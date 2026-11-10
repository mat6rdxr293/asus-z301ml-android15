#!/usr/bin/env python3
"""MT6328 codec: one-time init from vendor mt6331_codec_init_reg() that our driver lacked.
AFE_PMIC_NEWIF_CFG2 (0x203c) bit15 = "Reverse the PMIC clock": the PMIC must latch the SoC's
AUD_DAT_MOSI on the inverted AUD_CLK_MOSI edge, otherwise the DL data is garbage (speaker: white
noise instead of audio). Also disable HP/voice short-circuit protection (AUDDEC_ANA_CON0 0xe000).
Usage: snd_codec_newif_clk.py path/to/mt6328.c"""
import sys

p = sys.argv[1]
s = open(p).read()
if "Reverse the PMIC clock" in s:
    sys.exit("already patched")
old = """	snd_soc_component_init_regmap(c, p->regmap);"""
assert s.count(old) == 1
s = s.replace(old, old + """
	/* vendor mt6331_codec_init_reg(): "Reverse the PMIC clock" - latch DL data on the other edge */
	regmap_update_bits(p->regmap, 0x203c /* AFE_PMIC_NEWIF_CFG2 */, 0x8000, 0x8000);
	/* disable HPL/HPR/voice short-circuit protection */
	regmap_update_bits(p->regmap, 0x0cdc /* AUDDEC_ANA_CON0 */, 0xe000, 0xe000);""")
open(p, "w").write(s)
print("patched", p)
