#!/usr/bin/env python3
"""Debug: print the components bound to every ASoC runtime of the z301ml-mt6328 card (late_probe).
Usage: snd_machine_debug.py path/to/mt6735-mt6328.c"""
import sys

p = sys.argv[1]
s = open(p).read()
if "mt6735_mt6328_late_probe" in s:
    sys.exit("already patched")
old = "static struct snd_soc_card mt6735_mt6328_card = {"
assert s.count(old) == 1
s = s.replace(old, r'''static int mt6735_mt6328_late_probe(struct snd_soc_card *card)
{
	struct snd_soc_pcm_runtime *rtd;
	struct snd_soc_component *c;
	int i;

	for_each_card_rtds(card, rtd)
		for_each_rtd_components(rtd, i, c)
			dev_info(card->dev, "rtd %s comp %d: %s (drv %s)\n", rtd->dai_link->name, i,
				 c->name, c->driver->name);
	return 0;
}

static struct snd_soc_card mt6735_mt6328_card = {
	.late_probe = mt6735_mt6328_late_probe,''')
open(p, "w").write(s)
print("patched", p)
