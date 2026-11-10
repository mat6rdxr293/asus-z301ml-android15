/* z301-hciraw: open hci0 via HCI_CHANNEL_USER (device must be down), send hex commands, dump raw replies.
 * usage: z301-hciraw "01 03 0c 00" "01 04 10 00" ... */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <sys/socket.h>
#include <fcntl.h>

struct sockaddr_hci { unsigned short family, dev, channel; };

int main(int argc, char **argv)
{
	int s = socket(31, SOCK_RAW | SOCK_CLOEXEC, 1), i, j, r;
	struct sockaddr_hci a = { 31, 0, 1 };
	unsigned char b[1100];

	if (getenv("DEV")) { close(s); s = open(getenv("DEV"), O_RDWR | O_NOCTTY); if (s < 0) { perror("open"); return 1; } }
	else if (s < 0 || bind(s, (void *)&a, sizeof(a)) < 0) { perror("user channel"); return 1; }
	for (i = 1; i < argc; i++) {
		char *p = argv[i];
		int n = 0;
		struct pollfd pf = { s, POLLIN, 0 };

		if (!strcmp(p, "wait")) {
			while (poll(&pf, 1, 8000) > 0 && (r = read(s, b, sizeof(b))) > 0) {
				printf("< (%d)", r);
				for (j = 0; j < r && j < 40; j++) printf(" %02x", b[j]);
				printf("\n");
			}
			continue;
		}
		while (*p) { b[n++] = strtoul(p, &p, 16); while (*p == ' ') p++; }
		if (write(s, b, n) != n) perror("write");
		while (poll(&pf, 1, 1500) > 0) {
			r = read(s, b, sizeof(b));
			if (r <= 0) break;
			printf("< (%d)", r);
			for (j = 0; j < r; j++) printf(" %02x", b[j]);
			printf("\n");
			if (b[0] == 4 && (b[1] == 0x0e || b[1] == 0x0f)) break;
		}
	}
	close(s);
	return 0;
}
