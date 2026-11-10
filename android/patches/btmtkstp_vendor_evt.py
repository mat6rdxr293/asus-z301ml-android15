#!/usr/bin/env python3
"""Patch btmtkstp.c (VM ~/z301ml-port/connsys/wmt/linux) so Android's BT stack survives pairing:
 - drop Command Complete/Status for vendor opcodes (OGF 0x3f) the host never sent
   (CONNSYS emits CC for 0xfcbd after SSP; GD HCI layer aborts on it -> stack SIGABRT)
 - clamp max_page in Read Remote Extended Features Complete (stack walked pages 2..40)
Usage: btmtkstp_vendor_evt.py path/to/btmtkstp.c
"""
import sys

p = sys.argv[1]
s = open(p).read()
if "vendor_pending" in s:
    sys.exit("already patched")

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

sub("static bool bdaddr_ok, swallow_fc1a;\n",
"""static bool bdaddr_ok, swallow_fc1a;

/* Vendor (OGF 0x3f) commands the host really sent and still waits for. CONNSYS emits
 * Command Complete for vendor opcodes nobody sent (e.g. 0xfcbd right after SSP pairing);
 * Android's GD HCI layer aborts the whole Bluetooth stack on such an event, so drop them. */
static DECLARE_BITMAP(vendor_pending, 1024);
""")

sub("""		/* completion of our own set-BDADDR command: the host never sent it */""",
"""		/* Read Remote Extended Features Complete: CONNSYS reports a bogus max_page (the
		 * stack then walks pages 2..40); no spec page beyond 2 exists */
		if (rx_type == HCI_EVENT_PKT && rx_skb->len >= 7 &&
		    rx_skb->data[0] == HCI_EV_REMOTE_EXT_FEATURES && rx_skb->data[6] > 2)
			rx_skb->data[6] = max_t(u8, 2, rx_skb->data[5]);
		/* completion/status of a vendor command the host never sent: drop it */
		if (rx_type == HCI_EVENT_PKT && !(swallow_fc1a && rx_skb->len >= 5 &&
		      rx_skb->data[0] == HCI_EV_CMD_COMPLETE &&
		      get_unaligned_le16(rx_skb->data + 3) == 0xfc1a)) {
			u16 op = 0;

			if (rx_skb->len >= 5 && rx_skb->data[0] == HCI_EV_CMD_COMPLETE)
				op = get_unaligned_le16(rx_skb->data + 3);
			else if (rx_skb->len >= 6 && rx_skb->data[0] == HCI_EV_CMD_STATUS)
				op = get_unaligned_le16(rx_skb->data + 4);
			if ((op >> 10) == 0x3f && !test_and_clear_bit(op & 0x3ff, vendor_pending)) {
				bt_dev_warn_ratelimited(g_hdev,
					"dropping unsolicited event 0x%02x for vendor opcode 0x%04x",
					rx_skb->data[0], op);
				kfree_skb(rx_skb);
				rx_skb = NULL;
				rx_stage = 0;
				continue;
			}
		}
		/* completion of our own set-BDADDR command: the host never sent it */""")

sub("""	memcpy(skb_push(skb, 1), &hci_skb_pkt_type(skb), 1);""",
"""	if (hci_skb_pkt_type(skb) == HCI_COMMAND_PKT && skb->len >= 2) {
		u16 op = get_unaligned_le16(skb->data);

		if ((op >> 10) == 0x3f)
			set_bit(op & 0x3ff, vendor_pending);
	}
	memcpy(skb_push(skb, 1), &hci_skb_pkt_type(skb), 1);""")

open(p, "w").write(s)
print("patched", p)
