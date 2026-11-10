/* Z301ML: compat shims so MTK 3.18 vendor drivers build on Linux 7.0 */
#ifndef Z301_COMPAT_H
#define Z301_COMPAT_H
#include <linux/version.h>
#include <linux/kernel.h>
#include <linux/timer.h>
#include <linux/time.h>
#include <linux/timekeeping.h>
#include <linux/ktime.h>
#include <linux/device.h>
#include <linux/dma-mapping.h>
#include <linux/sched/clock.h>
struct timeval { long tv_sec; long tv_usec; };
static inline void do_gettimeofday(struct timeval *tv)
{ struct timespec64 ts; ktime_get_real_ts64(&ts); tv->tv_sec = ts.tv_sec; tv->tv_usec = ts.tv_nsec / 1000; }
struct timespec { long tv_sec; long tv_nsec; };
static inline void getnstimeofday(struct timespec *t)
{ struct timespec64 ts; ktime_get_real_ts64(&ts); t->tv_sec = ts.tv_sec; t->tv_nsec = ts.tv_nsec; }
#define dma_zalloc_coherent dma_alloc_coherent
#define class_create(owner, name) class_create(name)
#define DRIVER_ATTR(_name, _mode, _show, _store) \
	struct driver_attribute driver_attr_##_name = __ATTR(_name, _mode, _show, _store)
#ifndef S_IRUGO
#define S_IRUGO 0444
#include <linux/pinctrl/consumer.h>
#include <linux/proc_fs.h>
#include <linux/sched/debug.h>
#include <linux/io.h>
#define ioremap_nocache ioremap
#define z301_show_stack(t, sp) dump_stack()
extern int g_ASUS_hwID;
static inline int enable_4G(void) { return 0; }
#endif
#include <linux/pinctrl/consumer.h>
#include <linux/proc_fs.h>
#include <linux/sched/debug.h>
#include <linux/io.h>
#define ioremap_nocache ioremap
#define z301_show_stack(t, sp) dump_stack()
extern int g_ASUS_hwID;
static inline int enable_4G(void) { return 0; }
#endif
