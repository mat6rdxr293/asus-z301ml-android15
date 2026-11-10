// SPDX-License-Identifier: GPL-2.0
/* Z301ML: stubs for vendor symbols not used on MT6735 SOC connsys (no SDIO combo chip, no AEE) */
#include <linux/kernel.h>
#include "osal_typedef.h"
#include "wmt_core.h"
#include "stp_sdio.h"
#include "stp_dbg_combo.h"
#include <aee.h>
WMT_IC_OPS wmt_ic_ops_mt6628;
WMT_IC_OPS wmt_ic_ops_mt6632;
MTK_WCN_STP_SDIO_HIF_INFO g_stp_sdio_host_info;
int sdio_detect_exit(void) { return 0; }
INT32 stp_dbg_combo_core_dump(INT32 dump_sink) { return 0; }
PUINT8 stp_dbg_combo_id_to_task(UINT32 id) { return (PUINT8)"combo"; }
void aee_kernel_warning_api(const char *file, const int line, const int db_opt, const char *module, const char *msg, ...)
{ pr_warn("z301 aee warning %s:%d %s\n", file, line, module); }
void aed_combo_exception_api(const int *log, int log_size, const int *phy, int phy_size, const char *detail, const int db_opt)
{ pr_err("z301 aed combo exception: %s\n", detail); }
#include "hif_sdio.h"
#include "sdio_detect.h"
WMT_IC_OPS wmt_ic_ops_mt6620;
WMT_IC_OPS wmt_ic_ops_mt6630;
void aee_kernel_dal_api(const char *file, const int line, const char *msg) { pr_err("z301 aee dal %s\n", msg); }
int sdio_detect_init(void) { return 0; }
int sdio_detect_query_chipid(int waitFlag) { return -1; }
int hif_sdio_is_chipid_valid(int chipId) { return 0; }
INT32 stp_sdio_rw_retry(ENUM_STP_SDIO_HIF_TYPE_T type, UINT32 retry_limit, MTK_WCN_HIF_SDIO_CLTCTX clt_ctx, UINT32 offset, PUINT32 pData, UINT32 len) { return -1; }
INT32 mtk_wcn_hif_sdio_wmt_control(WMT_SDIO_FUNC_TYPE func_type, MTK_WCN_BOOL is_on) { return 0; }
INT32 mtk_wcn_hif_sdio_update_cb_reg(INT32(*ts_update)(VOID)) { return 0; }
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/mfd/mt6397/core.h>
#include <upmu_common.h>
#include <mach/upmu_hw.h>
int sdio_detect_do_autok(int chipId) { return 0; }
/* Z301ML: only the LDO ON_CTRL (SW/HW control mode) fields used by consys are implemented, via the MT6328 regmap */
unsigned short pmic_set_register_value(PMU_FLAGS_LIST_ENUM flagname, unsigned int val)
{
	static struct regmap *rm;
	struct device_node *np;
	struct platform_device *pd;
	struct mt6397_chip *chip;

	if (!rm) {
		np = of_find_compatible_node(NULL, NULL, "mediatek,mt6328");
		pd = np ? of_find_device_by_node(np) : NULL;
		of_node_put(np);
		chip = pd ? platform_get_drvdata(pd) : NULL;
		if (!chip || !chip->regmap) { pr_err("z301 pmic: no mt6328 regmap\n"); return 1; }
		rm = chip->regmap;
	}
	switch (flagname) {
	case PMIC_RG_VCN18_ON_CTRL:
		return regmap_update_bits(rm, MT6328_PMIC_RG_VCN18_ON_CTRL_ADDR, 1 << MT6328_PMIC_RG_VCN18_ON_CTRL_SHIFT, (val & 1) << MT6328_PMIC_RG_VCN18_ON_CTRL_SHIFT);
	case PMIC_RG_VCN28_ON_CTRL:
		return regmap_update_bits(rm, MT6328_PMIC_RG_VCN28_ON_CTRL_ADDR, 1 << MT6328_PMIC_RG_VCN28_ON_CTRL_SHIFT, (val & 1) << MT6328_PMIC_RG_VCN28_ON_CTRL_SHIFT);
	case PMIC_RG_VCN33_ON_CTRL_BT:
		return regmap_update_bits(rm, MT6328_PMIC_RG_VCN33_ON_CTRL_BT_ADDR, 1 << MT6328_PMIC_RG_VCN33_ON_CTRL_BT_SHIFT, (val & 1) << MT6328_PMIC_RG_VCN33_ON_CTRL_BT_SHIFT);
	case PMIC_RG_VCN33_ON_CTRL_WIFI:
		return regmap_update_bits(rm, MT6328_PMIC_RG_VCN33_ON_CTRL_WIFI_ADDR, 1 << MT6328_PMIC_RG_VCN33_ON_CTRL_WIFI_SHIFT, (val & 1) << MT6328_PMIC_RG_VCN33_ON_CTRL_WIFI_SHIFT);
	default:
		pr_warn("z301 pmic_set_register_value(%d) not implemented\n", flagname);
		return 1;
	}
}

/* Z301ML: symbols the MTK wlan gen2 driver / wmt_chrdev_wifi expect from the WMT module */
#include <linux/export.h>
extern phys_addr_t gConEmiPhyBase;
EXPORT_SYMBOL(gConEmiPhyBase);
extern INT32 mtk_wcn_consys_hw_wifi_paldo_ctrl(UINT32 enable);
EXPORT_SYMBOL(mtk_wcn_consys_hw_wifi_paldo_ctrl);
UINT32 g_IsNeedDoChipReset;
EXPORT_SYMBOL(g_IsNeedDoChipReset);
