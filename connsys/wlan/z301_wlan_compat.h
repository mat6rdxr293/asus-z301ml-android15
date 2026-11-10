/* Z301ML: kernel 3.18 -> 7.0 API shims for the MTK wlan gen2 driver */
#pragma once
#include <linux/version.h>
#include <linux/string.h>
#include <net/cfg80211.h>
#define IEEE80211_BAND_2GHZ	NL80211_BAND_2GHZ
#define IEEE80211_BAND_5GHZ	NL80211_BAND_5GHZ
#define IEEE80211_NUM_BANDS	NUM_NL80211_BANDS
#define strnicmp		strncasecmp
#define IEEE80211_BAND_60GHZ	NL80211_BAND_60GHZ
#define STATION_INFO_TX_BITRATE		BIT_ULL(NL80211_STA_INFO_TX_BITRATE)
#define STATION_INFO_RX_BITRATE		BIT_ULL(NL80211_STA_INFO_RX_BITRATE)
#define STATION_INFO_SIGNAL		BIT_ULL(NL80211_STA_INFO_SIGNAL)
#define STATION_INFO_TX_PACKETS		BIT_ULL(NL80211_STA_INFO_TX_PACKETS)
#define STATION_INFO_RX_PACKETS		BIT_ULL(NL80211_STA_INFO_RX_PACKETS)
#define STATION_INFO_TX_FAILED		BIT_ULL(NL80211_STA_INFO_TX_FAILED)
#define STATION_INFO_TX_RETRIES		BIT_ULL(NL80211_STA_INFO_TX_RETRIES)
#define STATION_INFO_RX_BYTES		BIT_ULL(NL80211_STA_INFO_RX_BYTES)
#define STATION_INFO_TX_BYTES		BIT_ULL(NL80211_STA_INFO_TX_BYTES)
#define STATION_INFO_INACTIVE_TIME	BIT_ULL(NL80211_STA_INFO_INACTIVE_TIME)
#define STATION_INFO_ASSOC_REQ_IES	0 /* assoc_req_ies is just set now, no flag */
#define netif_rx_ni			netif_rx
#define del_timer_sync			timer_delete_sync
#define del_timer			timer_delete
#define VERIFY_READ			0
#define VERIFY_WRITE			1
/* access_ok() lost its type argument */
#define z301_access_ok(type, addr, size)	access_ok(addr, size)
/* set_fs() is gone: kernel buffers go through kernel_read()/kernel_write() (patched call sites) */
typedef int mm_segment_t;
#define get_fs()		0
#define get_ds()		0
#define KERNEL_DS		0
#define set_fs(x)		do { (void)(x); } while (0)
#ifndef MODULE_SUPPORTED_DEVICE
#define MODULE_SUPPORTED_DEVICE(x)
#endif
