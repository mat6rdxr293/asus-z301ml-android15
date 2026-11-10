#!/usr/bin/env python3
"""mt6735-mt6328.c: the Z301ML external speaker amp (enable = GPIO9) takes its input from the MT6328
headphone output (verified 2026-11-11: a tone on the HP path is heard from the speaker, a tone on the
IV-buffer "SPK" path is not). Feed "Ext Spk" from HPL only.
Usage: snd_machine_spk_from_hp.py path/to/mt6735-mt6328.c"""
import sys

p = sys.argv[1]
s = open(p).read()
old = """	/* external amp input is not known yet: feed it from either codec output */
	{"Ext Spk", NULL, "HPL"},
	{"Ext Spk", NULL, "SPK"},"""
new = """	/* the external speaker amp (GPIO9) is fed by the codec headphone output */
	{"Ext Spk", NULL, "HPL"},"""
if new in s:
    sys.exit("already patched")
assert s.count(old) == 1, "routes not found"
open(p, "w").write(s.replace(old, new))
print("patched", p)
