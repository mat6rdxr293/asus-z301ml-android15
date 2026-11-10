/* z301-btscan: bring hci0 up and run a 5 s LE scan through a raw HCI socket (no bluez needed) */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>

#define AF_BLUETOOTH 31
#define BTPROTO_HCI 1
#define SOL_HCI 0
#define HCI_FILTER 2
#define HCIDEVUP _IOW('H', 201, int)
struct sockaddr_hci { unsigned short family, dev, channel; };
struct hci_filter { unsigned int type_mask; unsigned int event_mask[2]; unsigned short opcode; };

static int cmd(int s, unsigned short op, const void *p, int n)
{
	unsigned char b[260] = { 1, op & 0xff, op >> 8, n };

	memcpy(b + 4, p, n);
	return write(s, b, n + 4);
}

int main(void)
{
	int s = socket(AF_BLUETOOTH, SOCK_RAW, BTPROTO_HCI), r, i, seen = 0;
	struct sockaddr_hci a = { AF_BLUETOOTH, 0, 0 };
	struct hci_filter f = { 1 << 4, { 0xffffffff, 0xffffffff }, 0 };
	unsigned char b[300];
	static const unsigned char sp[] = { 1, 0x10, 0, 0x10, 0, 0, 0 }, en[] = { 1, 0 }, dis[] = { 0, 0 };
	time_t t0;

	if (s < 0) { perror("socket"); return 1; }
	if (ioctl(s, HCIDEVUP, 0) < 0) perror("HCIDEVUP (EALREADY is fine)");
	if (bind(s, (void *)&a, sizeof(a)) < 0) { perror("bind"); return 1; }
	setsockopt(s, SOL_HCI, HCI_FILTER, &f, sizeof(f));
	cmd(s, 0x1009, "", 0);			/* Read BD_ADDR */
	cmd(s, 0x200b, sp, sizeof(sp));		/* LE set scan params: active */
	cmd(s, 0x200c, en, sizeof(en));		/* LE scan enable */
	t0 = time(0);
	while (time(0) - t0 < 6) {
		struct pollfd p = { s, POLLIN, 0 };

		if (poll(&p, 1, 500) <= 0) continue;
		r = read(s, b, sizeof(b));
		if (r < 4) continue;
		if (b[1] == 0x0e && b[4] == 0x09 && b[5] == 0x10)
			printf("bdaddr %02x:%02x:%02x:%02x:%02x:%02x status %d\n", b[12], b[11], b[10], b[9], b[8], b[7], b[6]);
		else if (b[1] == 0x0e)
			printf("cmd %02x%02x status %d\n", b[5], b[4], b[6]);
		else if (b[1] == 0x3e && b[3] == 0x02) {
			seen++;
			printf("adv %02x:%02x:%02x:%02x:%02x:%02x rssi %d\n", b[11], b[10], b[9], b[8], b[7], b[6], (signed char)b[r - 1]);
		}
	}
	cmd(s, 0x200c, dis, sizeof(dis));
	printf("LE adv reports: %d\n", seen);
	close(s);
	return 0;
}
