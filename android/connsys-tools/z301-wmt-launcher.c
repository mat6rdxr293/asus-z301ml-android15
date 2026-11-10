/* z301-wmt-launcher: minimal replacement for MediaTek wmt_loader + wmt_launcher (MT6735 SOC connsys, BTIF).
 * Protocol reverse-engineered from the stock Android 7 wmt_launcher + vendor WMT kernel driver. */
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define WMT_IOC_MAGIC 0xa0
#define WMT_IOCTL_SET_STP_MODE    _IOW(WMT_IOC_MAGIC, 5, int)
#define WMT_IOCTL_FUNC_ONOFF_CTRL _IOW(WMT_IOC_MAGIC, 6, int)
#define WMT_IOCTL_SET_LAUNCHER_KILL _IOW(WMT_IOC_MAGIC, 13, int)
#define WMT_IOCTL_SET_PATCH_NUM   _IOW(WMT_IOC_MAGIC, 14, int)
#define WMT_IOCTL_SET_PATCH_INFO  _IOW(WMT_IOC_MAGIC, 15, char *)
#define WMT_IOCTL_WMT_CFG_NAME    _IOWR(WMT_IOC_MAGIC, 21, char *)
#define WMT_IOCTL_WMT_TELL_CHIPID _IOW(WMT_IOC_MAGIC, 23, int)
#define WMT_DETECT_IOC_MAGIC 'w'
#define COMBO_IOCTL_SET_CHIP_ID   _IOW(WMT_DETECT_IOC_MAGIC, 1, int)

struct wmt_patch_info { uint32_t seq; uint8_t addr[4]; uint8_t name[256]; };

static const char *fwdir = "/vendor/firmware";
static const char *patches[] = { "ROMv2_lm_patch_1_0_hdr.bin", "ROMv2_lm_patch_1_1_hdr.bin" };

static int send_patches(int fd)
{
	int n = sizeof(patches) / sizeof(patches[0]), i, num = 0;

	for (i = 0; i < n; i++) {
		struct wmt_patch_info pi = { 0 };
		char path[300];
		uint8_t b[4];
		int pf;

		snprintf(path, sizeof(path), "%s/%s", fwdir, patches[i]);
		pf = open(path, O_RDONLY);
		if (pf < 0 || pread(pf, b, 4, 0x18) != 4) { fprintf(stderr, "patch %s unreadable\n", path); if (pf >= 0) close(pf); return -1; }
		close(pf);
		if (!num) {
			num = b[0] >> 4;
			printf("patch num = %d\n", num);
			if (ioctl(fd, WMT_IOCTL_SET_PATCH_NUM, num) < 0) perror("SET_PATCH_NUM");
		}
		pi.seq = b[0] & 0xf;
		memcpy(pi.addr, b, 4); pi.addr[0] = 0; /* stock launcher clears num/seq nibble byte */
		snprintf((char *)pi.name, sizeof(pi.name), "%s", path);
		printf("patch %s seq %u addr %02x %02x %02x %02x\n", path, pi.seq, b[0], b[1], b[2], b[3]);
		if (ioctl(fd, WMT_IOCTL_SET_PATCH_INFO, &pi) < 0) perror("SET_PATCH_INFO");
	}
	return 0;
}

int main(int argc, char **argv)
{
	char cfg[256] = "WMT_SOC.cfg", buf[256];
	int fd, dfd, wifi = argc > 1 && !strcmp(argv[1], "wifi");

	if (getenv("Z301_FWDIR")) fwdir = getenv("Z301_FWDIR");
	dfd = open("/dev/wmtdetect", O_RDWR);
	if (dfd >= 0) { if (ioctl(dfd, COMBO_IOCTL_SET_CHIP_ID, 0x6735) < 0) perror("SET_CHIP_ID"); close(dfd); }
	fd = open("/dev/stpwmt", O_RDWR | O_NOCTTY);
	if (fd < 0) { perror("/dev/stpwmt"); return 1; }
	if (ioctl(fd, WMT_IOCTL_WMT_TELL_CHIPID, 0x6735) < 0) perror("TELL_CHIPID");
	if (ioctl(fd, WMT_IOCTL_WMT_CFG_NAME, cfg) < 0) perror("CFG_NAME");
	/* STP over BTIF, FM via common interface (WMT_FM_COMM=2) */
	if (ioctl(fd, WMT_IOCTL_SET_STP_MODE, 0x03 | (2 << 4)) < 0) perror("SET_STP_MODE");
	printf("launcher ready, waiting for driver requests\n"); fflush(stdout);
	if (wifi) {
		/* turn on WIFI (WMTDRV_TYPE_WIFI = 3) from a child so we keep serving srh_patch */
		if (fork() == 0) { sleep(1); int r = ioctl(fd, WMT_IOCTL_FUNC_ONOFF_CTRL, 0x80000000 | 3); printf("FUNC_ON wifi -> %d\n", r); fflush(stdout); _exit(0); }
	}
	for (;;) {
		struct pollfd p = { .fd = fd, .events = POLLIN };
		int r = poll(&p, 1, -1), len;

		if (r <= 0) continue;
		len = read(fd, buf, sizeof(buf) - 1);
		if (len <= 0) continue;
		buf[len] = 0;
		printf("cmd: %s\n", buf); fflush(stdout);
		if (!strcmp(buf, "srh_patch")) {
			r = send_patches(fd);
			write(fd, r ? "fail" : "ok", r ? 4 : 2);
		} else {
			write(fd, "ok", 2);
		}
	}
}
