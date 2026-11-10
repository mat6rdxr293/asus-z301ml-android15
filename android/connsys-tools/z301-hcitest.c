/* z301-hcitest: send HCI Reset + Read BD_ADDR + Read Local Version over /dev/stpbt (H4 framing), dump replies */
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <unistd.h>

static void xfer(int fd, const unsigned char *c, int n)
{
	unsigned char b[512];
	int i, r;
	struct pollfd p = { fd, POLLIN, 0 };

	printf(">");
	for (i = 0; i < n; i++) printf(" %02x", c[i]);
	printf("\n");
	if (write(fd, c, n) != n) { perror("write"); return; }
	while (poll(&p, 1, 3000) > 0) {
		r = read(fd, b, sizeof(b));
		if (r <= 0) break;
		printf("<");
		for (i = 0; i < r; i++) printf(" %02x", b[i]);
		printf("\n");
		if (poll(&p, 1, 300) <= 0) break;
	}
}

int main(void)
{
	static const unsigned char rst[] = { 1, 0x03, 0x0c, 0 }, addr[] = { 1, 0x09, 0x10, 0 }, ver[] = { 1, 0x01, 0x10, 0 };
	int fd = open("/dev/stpbt", O_RDWR | O_NOCTTY);

	if (fd < 0) { perror("open /dev/stpbt"); return 1; }
	printf("opened\n");
	xfer(fd, rst, 4);
	xfer(fd, ver, 4);
	xfer(fd, addr, 4);
	close(fd);
	return 0;
}
