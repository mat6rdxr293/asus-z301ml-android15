/* z301 compat: MT6735 clock buffer control (TODO: real CLK_BUF_CONN via MT6328) */
#pragma once
#include <linux/types.h>
enum clk_buf_id { CLK_BUF_BB_MD, CLK_BUF_CONN, CLK_BUF_NFC, CLK_BUF_AUDIO };
bool z301_clk_buf_ctrl(enum clk_buf_id id, bool onoff);
#define clk_buf_ctrl(id, on) z301_clk_buf_ctrl((id), (on))
