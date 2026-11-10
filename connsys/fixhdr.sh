#!/bin/bash
# fixhdr.sh ERRFILE : for each missing header, copy from vendor 3.18 tree (mt-plat include dirs) or create a stub
C=~/z301ml-port/connsys/compat; K=~/z301ml-port/kernel-3.18
for h in $(grep -oE "fatal error: [^:]+: No such file" "$1" | sed -E "s/fatal error: (.*): No such file/\1/" | sort -u); do
  [ -e "$C/$h" ] && continue
  src=$(find $K/drivers/misc/mediatek/include $K/include -path "*$h" 2>/dev/null | grep -E "mt6735|mt-plat/[a-z_]*\.h$|/include/$h$|mt-plat/$h$" | head -1)
  [ -z "$src" ] && src=$(find $K/drivers/misc/mediatek/include $K/include -path "*/$h" 2>/dev/null | head -1)
  mkdir -p "$C/$(dirname $h)"
  if [ -n "$src" ]; then cp "$src" "$C/$h"; echo "COPIED $h <- ${src#$K/}"; else printf "/* z301 compat stub for %s */\n#pragma once\n" "$h" > "$C/$h"; echo "STUB $h"; fi
done
