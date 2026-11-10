#!/usr/bin/env python3
"""Fix kernel panic on first playback (NULL deref in mtk_memif_set_rate_substream).
In Linux 7.0 COMP_DUMMY() is an empty array (snd_soc_fill_dummy_dai() fills it later), so for the
FE links dai_link->codecs aliases the next array (platforms). The probe loop
`if (!dai_link->codecs->name) dai_link->codecs->of_node = codec_node;` therefore overwrote the
Playback_1 platform with the codec node -> the AFE "mtk-afe-pcm" component was not bound to the FE
runtime -> snd_soc_rtdcom_lookup() returned NULL in hw_params -> Oops -> panic.
Usage: snd_machine_dummy_fix.py path/to/mt6735-mt6328.c"""
import sys

p = sys.argv[1]
s = open(p).read()
old = """		if (!dai_link->platforms->name)
			dai_link->platforms->of_node = platform_node;
		if (!dai_link->codecs->name)
			dai_link->codecs->of_node = codec_node;"""
new = """		/* COMP_DUMMY() is an empty array: only touch entries that exist */
		if (dai_link->num_platforms && !dai_link->platforms->name)
			dai_link->platforms->of_node = platform_node;
		if (dai_link->num_codecs && !dai_link->codecs->name)
			dai_link->codecs->of_node = codec_node;"""
assert s.count(old) == 1, "pattern not found"
s = s.replace(old, new)
open(p, "w").write(s)
print("patched", p)
