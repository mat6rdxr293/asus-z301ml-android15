// SPDX-License-Identifier: GPL-2.0
/*
 * btmtkstp: Linux HCI driver for the MT6735 CONNSYS Bluetooth core (ASUS Z301ML).
 * The controller is reached via the vendor WMT/STP stack (mtk_wmt.ko) over BTIF;
 * STP carries plain H4 frames on BT_TASK_INDX.
 */
#include <linux/module.h>
#include <linux/skbuff.h>
#include <linux/workqueue.h>
#include <linux/unaligned.h>
#include <net/bluetooth/bluetooth.h>
#include <net/bluetooth/hci_core.h>
#include "osal_typedef.h"
#include "stp_exp.h"
#include "wmt_exp.h"

static struct hci_dev *g_hdev;
static struct work_struct rx_work;
static struct sk_buff *rx_skb;
static unsigned int rx_need;	/* bytes still needed for current header/payload */
static u8 rx_type;
static int rx_stage;		/* 0 = type, 1 = header, 2 = payload */
static DEFINE_MUTEX(tx_lock);

/* factory BD_ADDR ("XX:XX:XX:XX:XX:XX", from persist/bt/bd_addr.conf); written with the MTK
 * vendor command 0xfc1a at every open, since the controller boots with a placeholder address */
static char *bdaddr;
module_param(bdaddr, charp, 0444);
MODULE_PARM_DESC(bdaddr, "BD_ADDR to program at open, XX:XX:XX:XX:XX:XX");
static u8 bdaddr_le[6];
static bool bdaddr_ok, swallow_fc1a;

static unsigned int hdr_len(u8 t)
{
	switch (t) {
	case HCI_EVENT_PKT: return HCI_EVENT_HDR_SIZE;
	case HCI_ACLDATA_PKT: return HCI_ACL_HDR_SIZE;
	case HCI_SCODATA_PKT: return HCI_SCO_HDR_SIZE;
	case HCI_ISODATA_PKT: return HCI_ISO_HDR_SIZE;
	}
	return 0;
}

static unsigned int payload_len(struct sk_buff *skb, u8 t)
{
	switch (t) {
	case HCI_EVENT_PKT: return ((struct hci_event_hdr *)skb->data)->plen;
	case HCI_ACLDATA_PKT: return __le16_to_cpu(((struct hci_acl_hdr *)skb->data)->dlen);
	case HCI_SCODATA_PKT: return ((struct hci_sco_hdr *)skb->data)->dlen;
	case HCI_ISODATA_PKT: return hci_iso_data_len(__le16_to_cpu(((struct hci_iso_hdr *)skb->data)->dlen));
	}
	return 0;
}

static void rx_reset(void)
{
	kfree_skb(rx_skb);
	rx_skb = NULL;
	rx_stage = 0;
}

static void rx_feed(const u8 *p, int n)
{
	while (n > 0) {
		if (rx_stage == 0) {
			rx_type = *p++;
			n--;
			rx_need = hdr_len(rx_type);
			if (!rx_need) {
				bt_dev_err(g_hdev, "bad H4 type 0x%02x", rx_type);
				continue;
			}
			rx_skb = bt_skb_alloc(HCI_MAX_FRAME_SIZE, GFP_KERNEL);
			if (!rx_skb)
				return;
			hci_skb_pkt_type(rx_skb) = rx_type;
			rx_stage = 1;
			continue;
		}
		{
			unsigned int c = min_t(unsigned int, n, rx_need);

			if (rx_skb->len + c > HCI_MAX_FRAME_SIZE) {
				bt_dev_err(g_hdev, "rx frame too long");
				rx_reset();
				return;
			}
			skb_put_data(rx_skb, p, c);
			p += c;
			n -= c;
			rx_need -= c;
		}
		if (rx_need)
			continue;
		if (rx_stage == 1) {
			rx_need = payload_len(rx_skb, rx_type);
			rx_stage = 2;
			if (rx_need)
				continue;
		}
		/* CONNSYS reports max_page 2 for Read Local Extended Features but
		 * rejects page 2 with status 0x30, which aborts hci init: clamp it */
		if (rx_type == HCI_EVENT_PKT && rx_skb->len >= 8 && rx_skb->data[0] == HCI_EV_CMD_COMPLETE &&
		    get_unaligned_le16(rx_skb->data + 3) == HCI_OP_READ_LOCAL_EXT_FEATURES && rx_skb->data[7] > 1)
			rx_skb->data[7] = 1;
		/* completion of our own set-BDADDR command: the host never sent it */
		if (swallow_fc1a && rx_type == HCI_EVENT_PKT && rx_skb->len >= 5 &&
		    rx_skb->data[0] == HCI_EV_CMD_COMPLETE && get_unaligned_le16(rx_skb->data + 3) == 0xfc1a) {
			swallow_fc1a = false;
			if (rx_skb->len >= 6 && rx_skb->data[5])
				bt_dev_err(g_hdev, "set BD_ADDR failed, status 0x%02x", rx_skb->data[5]);
			kfree_skb(rx_skb);
		} else {
			hci_recv_frame(g_hdev, rx_skb);
		}
		rx_skb = NULL;
		rx_stage = 0;
	}
}

static void btmtkstp_rx_work(struct work_struct *w)
{
	static u8 buf[2048];
	int r;

	while ((r = mtk_wcn_stp_receive_data(buf, sizeof(buf), BT_TASK_INDX)) > 0)
		rx_feed(buf, r);
}

static void btmtkstp_event_cb(void)
{
	schedule_work(&rx_work);
}

static int btmtkstp_open(struct hci_dev *hdev)
{
	if (mtk_wcn_wmt_func_on(WMTDRV_TYPE_BT) == MTK_WCN_BOOL_FALSE) {
		bt_dev_err(hdev, "WMT func on BT failed (is the launcher running?)");
		return -EIO;
	}
	if (mtk_wcn_stp_is_ready() == MTK_WCN_BOOL_FALSE) {
		mtk_wcn_wmt_func_off(WMTDRV_TYPE_BT);
		return -EIO;
	}
	rx_reset();
	mtk_wcn_stp_register_event_cb(BT_TASK_INDX, btmtkstp_event_cb);
	schedule_work(&rx_work);
	if (bdaddr_ok) {
		u8 cmd[10] = { HCI_COMMAND_PKT, 0x1a, 0xfc, 6 };
		int r, tries = 0;

		memcpy(cmd + 4, bdaddr_le, 6);
		swallow_fc1a = true;
		mutex_lock(&tx_lock);
		while ((r = mtk_wcn_stp_send_data(cmd, sizeof(cmd), BT_TASK_INDX)) == 0 && tries++ < 50)
			usleep_range(1000, 2000);
		mutex_unlock(&tx_lock);
		if (r != sizeof(cmd)) {
			swallow_fc1a = false;
			bt_dev_err(hdev, "set BD_ADDR: STP tx %d", r);
		} else {
			bt_dev_info(hdev, "BD_ADDR set to %pMR", bdaddr_le);
		}
	}
	return 0;
}

static int btmtkstp_close(struct hci_dev *hdev)
{
	mtk_wcn_stp_register_event_cb(BT_TASK_INDX, NULL);
	cancel_work_sync(&rx_work);
	mtk_wcn_wmt_func_off(WMTDRV_TYPE_BT);
	rx_reset();
	return 0;
}

static int btmtkstp_flush(struct hci_dev *hdev)
{
	return 0;
}

static int btmtkstp_send(struct hci_dev *hdev, struct sk_buff *skb)
{
	int r, tries = 0;

	memcpy(skb_push(skb, 1), &hci_skb_pkt_type(skb), 1);
	mutex_lock(&tx_lock);
	while ((r = mtk_wcn_stp_send_data(skb->data, skb->len, BT_TASK_INDX)) == 0 && tries++ < 50)
		usleep_range(1000, 2000);
	mutex_unlock(&tx_lock);
	if (r != skb->len) {
		bt_dev_err(hdev, "STP tx %d/%u", r, skb->len);
		hdev->stat.err_tx++;
		kfree_skb(skb);
		return -EIO;
	}
	hdev->stat.byte_tx += skb->len;
	kfree_skb(skb);
	return 0;
}

/* MediaTek vendor command: write BD_ADDR (little endian) */
static int btmtkstp_set_bdaddr(struct hci_dev *hdev, const bdaddr_t *bdaddr)
{
	struct sk_buff *skb = __hci_cmd_sync(hdev, 0xfc1a, 6, bdaddr, HCI_INIT_TIMEOUT);

	if (IS_ERR(skb))
		return PTR_ERR(skb);
	kfree_skb(skb);
	return 0;
}

static int __init btmtkstp_init(void)
{
	struct hci_dev *hdev = hci_alloc_dev();
	int err;

	if (!hdev)
		return -ENOMEM;
	if (bdaddr) {
		unsigned int a[6];

		if (sscanf(bdaddr, "%x:%x:%x:%x:%x:%x", &a[0], &a[1], &a[2], &a[3], &a[4], &a[5]) == 6) {
			int i;

			for (i = 0; i < 6; i++)
				bdaddr_le[i] = a[5 - i];
			bdaddr_ok = true;
		} else {
			pr_err("btmtkstp: bad bdaddr '%s'\n", bdaddr);
		}
	}
	INIT_WORK(&rx_work, btmtkstp_rx_work);
	hdev->bus = HCI_SDIO;	/* closest match; CONNSYS is on-SoC */
	hdev->open = btmtkstp_open;
	hdev->close = btmtkstp_close;
	hdev->flush = btmtkstp_flush;
	hdev->send = btmtkstp_send;
	hdev->set_bdaddr = btmtkstp_set_bdaddr;
	g_hdev = hdev;
	err = hci_register_dev(hdev);
	if (err < 0) {
		hci_free_dev(hdev);
		return err;
	}
	pr_info("btmtkstp: registered %s\n", hdev->name);
	return 0;
}

static void __exit btmtkstp_exit(void)
{
	hci_unregister_dev(g_hdev);
	hci_free_dev(g_hdev);
}

module_init(btmtkstp_init);
module_exit(btmtkstp_exit);
MODULE_DESCRIPTION("MT6735 CONNSYS Bluetooth over WMT/STP");
MODULE_LICENSE("GPL");
