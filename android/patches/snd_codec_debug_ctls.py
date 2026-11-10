#!/usr/bin/env python3
"""Debug mixer controls for the MT6328 codec (sound/soc/codecs/mt6328.c):
  "DBG DL Sine Gen"  PMIC_AFE_TOP_CON0 bit0 (DL from the PMIC's internal sine table; AFE_SGEN_CFG0/1
                     are programmed at component probe) -> isolates analog/amp from the SoC->PMIC link
  "DBG DL PDN"       AFE_AUDIO_TOP_CON0 bit6 (PMIC downlink power-down)
  "DBG AFE TOP"      AFE_AUDIO_TOP_CON0 full 16-bit value
Usage: snd_codec_debug_ctls.py path/to/mt6328.c"""
import sys

p = sys.argv[1]
s = open(p).read()
if "DBG DL Sine Gen" in s:
    sys.exit("already patched")

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

sub("""	SOC_ENUM_EXT("Speaker Mode", spk_mode_enum, spk_mode_get, spk_mode_put),""",
"""	SOC_ENUM_EXT("Speaker Mode", spk_mode_enum, spk_mode_get, spk_mode_put),
	SOC_SINGLE("DBG DL Sine Gen", MT6328_PMIC_AFE_TOP_CON0, 0, 1, 0),
	SOC_SINGLE("DBG DL PDN", MT6328_AFE_AUDIO_TOP_CON0, 6, 1, 0),
	SOC_SINGLE("DBG AFE TOP", MT6328_AFE_AUDIO_TOP_CON0, 0, 0xffff, 0),""")

sub("""	snd_soc_component_init_regmap(c, p->regmap);
	return 0;""",
"""	snd_soc_component_init_regmap(c, p->regmap);
	/* PMIC sine generator (vendor SineTable test): 0x2040 = AFE_SGEN_CFG0, 0x2042 = AFE_SGEN_CFG1 */
	regmap_write(p->regmap, 0x2040, 0x0080);
	regmap_write(p->regmap, 0x2042, 0x0101);
	return 0;""")

open(p, "w").write(s)
print("patched", p)
