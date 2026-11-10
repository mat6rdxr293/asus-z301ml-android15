#!/usr/bin/env python3
"""Second btmtkstp.c patch (on top of btmtkstp_vendor_evt.py): track ALL outstanding HCI commands,
not just vendor ones. CONNSYS also sends duplicate Command Complete events for standard commands
(seen: extra CC for LE_SET_SCAN_ENABLE 0x200c while the stack waits for LE_SET_SCAN_PARAMETERS
0x200b -> GD hci_layer LOG_FATAL). Any CC/CS whose opcode the host is not waiting for is dropped
(opcode 0x0000 = credit-only NOP is passed through).
Usage: btmtkstp_all_cmd_evt.py path/to/btmtkstp.c
"""
import sys

p = sys.argv[1]
s = open(p).read()
if "cmd_pending" in s:
    sys.exit("already patched")
assert "vendor_pending" in s, "apply btmtkstp_vendor_evt.py first"

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

sub("""/* Vendor (OGF 0x3f) commands the host really sent and still waits for. CONNSYS emits
 * Command Complete for vendor opcodes nobody sent (e.g. 0xfcbd right after SSP pairing);
 * Android's GD HCI layer aborts the whole Bluetooth stack on such an event, so drop them. */
static DECLARE_BITMAP(vendor_pending, 1024);
""", """/* HCI commands the host really sent and still waits for. CONNSYS emits Command Complete for
 * opcodes nobody sent (vendor 0xfcbd right after SSP pairing) and duplicate CCs for standard ones
 * (LE_SET_SCAN_ENABLE); Android's GD HCI layer aborts the whole Bluetooth stack on any such
 * event, so drop them. */
static DECLARE_BITMAP(cmd_pending, 65536);
""")

sub("""			if ((op >> 10) == 0x3f && !test_and_clear_bit(op & 0x3ff, vendor_pending)) {
				bt_dev_warn_ratelimited(g_hdev,
					"dropping unsolicited event 0x%02x for vendor opcode 0x%04x",""",
"""			if (op && !test_and_clear_bit(op, cmd_pending)) {
				bt_dev_warn_ratelimited(g_hdev,
					"dropping unsolicited event 0x%02x for opcode 0x%04x",""")

sub("""		if ((op >> 10) == 0x3f)
			set_bit(op & 0x3ff, vendor_pending);""",
"""		if (op)
			set_bit(op, cmd_pending);""")

# a fresh open starts with nothing outstanding
sub("""static int btmtkstp_open(struct hci_dev *hdev)
{""", """static int btmtkstp_open(struct hci_dev *hdev)
{
	bitmap_zero(cmd_pending, 65536);""")

open(p, "w").write(s)
print("patched", p)
