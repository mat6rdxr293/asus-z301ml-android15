#!/bin/bash
# build_vendor.sh -> android/work/vendor.img (ext4 192M, root-owned; cache partition is 400M)
set -e; cd /Users/matveysazhnov/ASUS-Z301ML-port/android/work
find vendor -name '._*' -delete; COPYFILE_DISABLE=1 tar czf vendor.tgz --no-xattrs -C vendor .
limactl copy vendor.tgz z301ml-kernel:/tmp/vendor.tgz
limactl shell z301ml-kernel -- bash -c 'set -e; sudo rm -rf /tmp/vroot && sudo mkdir /tmp/vroot && sudo tar xzf /tmp/vendor.tgz -C /tmp/vroot 2>/dev/null; sudo chown -R root:root /tmp/vroot && sudo find /tmp/vroot -type d -exec chmod 755 {} + && sudo find /tmp/vroot -type f -exec chmod 644 {} + && sudo chmod 755 /tmp/vroot/bin/*; [ -d /tmp/vroot/bin/hw ] && sudo chmod 755 /tmp/vroot/bin/hw/*; rm -f /tmp/vendor.img; sudo mkfs.ext4 -q -L vendor -O ^metadata_csum,^64bit -b 4096 -d /tmp/vroot /tmp/vendor.img 192M; sudo chown $(id -u) /tmp/vendor.img'
limactl copy z301ml-kernel:/tmp/vendor.img vendor.img; shasum -a 256 vendor.img
