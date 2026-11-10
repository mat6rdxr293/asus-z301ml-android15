#!/usr/bin/env python3
"""mt6735-dai-adda.c: program and enable the "I2S DAC out" (AFE_I2S_CON1) for ADDA playback, as the
MT6735 vendor driver does (SetI2SDacOut + SetI2SDacEnable): rate code << 8, I2S format (1 << 3),
16-bit word length, enable bit0 while ADDA playback is powered (DAPM supply).
Usage: snd_afe_i2s_dac.py path/to/mt6735-dai-adda.c"""
import sys

p = sys.argv[1]
s = open(p).read()
if "I2S DAC Enable" in s:
    sys.exit("already patched")

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

# DAPM supply on AFE_I2S_CON1 bit0
sub("""	SND_SOC_DAPM_SUPPLY_S("ADDA Playback Enable", SUPPLY_SEQ_ADDA_DL_ON,""",
"""	SND_SOC_DAPM_SUPPLY_S("I2S DAC Enable", SUPPLY_SEQ_ADDA_DL_ON,
			      AFE_I2S_CON1, 0, 0, NULL, 0),
	SND_SOC_DAPM_SUPPLY_S("ADDA Playback Enable", SUPPLY_SEQ_ADDA_DL_ON,""")
sub("""	{"ADDA Playback", NULL, "ADDA Playback Enable"},""",
"""	{"ADDA Playback", NULL, "ADDA Playback Enable"},
	{"ADDA Playback", NULL, "I2S DAC Enable"},""")

# rate code helper (vendor enum Soc_Aud_I2S_SAMPLERATE)
sub("""/* dai ops */
static int mtk_dai_adda_hw_params(""",
"""static unsigned int mt6735_i2s_rate(unsigned int rate)
{
	switch (rate) {
	case 8000: return 0;
	case 11025: return 1;
	case 12000: return 2;
	case 16000: return 4;
	case 22050: return 5;
	case 24000: return 6;
	case 32000: return 8;
	case 44100: return 9;
	case 88200: return 11;
	case 96000: return 12;
	case 192000: return 14;
	case 48000:
	default: return 10;
	}
}

/* dai ops */
static int mtk_dai_adda_hw_params(""")

sub("""		/* clean predistortion */
		regmap_write(afe->regmap, AFE_ADDA_PREDIS_CON0, 0);""",
"""		/* I2S DAC out (vendor SetI2SDacOut): rate, I2S format, 16-bit; bit0 = DAPM supply */
		regmap_update_bits(afe->regmap, AFE_I2S_CON1, ~0x1u,
				   mt6735_i2s_rate(rate) << 8 | 1 << 3);

		/* clean predistortion */
		regmap_write(afe->regmap, AFE_ADDA_PREDIS_CON0, 0);""")

open(p, "w").write(s)
print("patched", p)
