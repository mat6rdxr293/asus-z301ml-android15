#!/usr/bin/env python3
"""mt6735-dai-adda.c: use the MT6735 interconnection layout for O03/O04 (ADDA DL ch1/ch2).
The driver was adapted from mt6797, where O03/O04 live in AFE_CONN3/AFE_CONN4 (bit = input).
On MT6735 (vendor mt_soc_afe_connection.c mConnectionReg/mConnectionbits):
  O03 (ADDA DL ch1): AFE_CONN1 (0x24), bit 16 + Ixx
  O04 (ADDA DL ch2): AFE_CONN2 (0x28), bit Ixx
DL3 (I23/I24) and PCM capture inputs cannot reach O03/O04 on MT6735 -> virtual (NOPM) switches,
kept only so the existing DAPM routes still resolve.
With the mt6797 layout DL1 never reached the DAC: the speaker amp only hissed.
Usage: snd_afe_conn_mt6735.py path/to/mt6735-dai-adda.c"""
import re, sys

p = sys.argv[1]
s = open(p).read()
if "MT6735 interconnection layout" in s:
    sys.exit("already patched")

new_mix = r'''/* MT6735 interconnection layout (vendor mt_soc_afe_connection.c):
 * O03 = AFE_CONN1 bit (16 + Ixx), O04 = AFE_CONN2 bit Ixx; DL3/PCM cannot reach O03/O04.
 */
#define O03_BIT(i)	(16 + (i))
#define O04_BIT(i)	(i)
static const struct snd_kcontrol_new mtk_adda_dl_ch1_mix[] = {
	SOC_DAPM_SINGLE_AUTODISABLE("DL1_CH1", AFE_CONN1, O03_BIT(I_DL1_CH1), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("DL2_CH1", AFE_CONN1, O03_BIT(I_DL2_CH1), 1, 0),
	SOC_DAPM_SINGLE("DL3_CH1", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("ADDA_UL_CH2", AFE_CONN1, O03_BIT(I_ADDA_UL_CH2), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("ADDA_UL_CH1", AFE_CONN1, O03_BIT(I_ADDA_UL_CH1), 1, 0),
	SOC_DAPM_SINGLE("PCM_1_CAP_CH1", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE("PCM_2_CAP_CH1", SND_SOC_NOPM, 0, 1, 0),
};

static const struct snd_kcontrol_new mtk_adda_dl_ch2_mix[] = {
	SOC_DAPM_SINGLE_AUTODISABLE("DL1_CH1", AFE_CONN2, O04_BIT(I_DL1_CH1), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("DL1_CH2", AFE_CONN2, O04_BIT(I_DL1_CH2), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("DL2_CH1", AFE_CONN2, O04_BIT(I_DL2_CH1), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("DL2_CH2", AFE_CONN2, O04_BIT(I_DL2_CH2), 1, 0),
	SOC_DAPM_SINGLE("DL3_CH1", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE("DL3_CH2", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("ADDA_UL_CH2", AFE_CONN2, O04_BIT(I_ADDA_UL_CH2), 1, 0),
	SOC_DAPM_SINGLE_AUTODISABLE("ADDA_UL_CH1", AFE_CONN2, O04_BIT(I_ADDA_UL_CH1), 1, 0),
	SOC_DAPM_SINGLE("PCM_1_CAP_CH1", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE("PCM_2_CAP_CH1", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE("PCM_1_CAP_CH2", SND_SOC_NOPM, 0, 1, 0),
	SOC_DAPM_SINGLE("PCM_2_CAP_CH2", SND_SOC_NOPM, 0, 1, 0),
};
'''

pat = re.compile(r"static const struct snd_kcontrol_new mtk_adda_dl_ch1_mix\[\] = \{.*?\n\};\n\s*\nstatic const struct snd_kcontrol_new mtk_adda_dl_ch2_mix\[\] = \{.*?\n\};\n", re.S)
s, n = pat.subn(new_mix, s, count=1)
assert n == 1, "mixer arrays not found"
open(p, "w").write(s)
print("patched", p)
