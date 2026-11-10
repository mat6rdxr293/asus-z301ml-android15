#!/bin/zsh
# passive: print a line whenever the set of MTK/ASUS/Google USB devices, adb or fastboot changes
prev=""
end=$((SECONDS+${1:-300}))
while (( SECONDS < end )); do
  u=$(ioreg -p IOUSB -l -w0 2>/dev/null | awk -F' = ' '/"idVendor"/{v=$2} /"idProduct"/{p=$2} (v!="" && p!=""){printf "%04x:%04x ", v, p; v=""; p=""}' | tr ' ' '\n' | grep -E '^(0e8d|0b05|18d1|0525|1d6b):' | sort | tr '\n' ' ')
  a=$(adb devices 2>/dev/null | sed 1d | grep -v '^$' | tr '\n' ' ')
  f=$(fastboot devices 2>/dev/null | tr '\n' ' ')
  cur="USB=[$u] ADB=[$a] FB=[$f]"
  [[ "$cur" != "$prev" ]] && echo "$(date +%T) $cur" && prev="$cur"
  sleep 1
done
echo "$(date +%T) WATCH END $prev"
