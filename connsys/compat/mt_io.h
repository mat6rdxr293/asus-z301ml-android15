#ifndef Z301_MT_IO_H
#define Z301_MT_IO_H
#include <linux/io.h>
#define mt_reg_sync_writel(v, a) do { writel((v), (void __iomem *)(a)); mb(); } while (0)
#define mt_reg_sync_writew(v, a) do { writew((v), (void __iomem *)(a)); mb(); } while (0)
#define mt_reg_sync_writeb(v, a) do { writeb((v), (void __iomem *)(a)); mb(); } while (0)
#endif
