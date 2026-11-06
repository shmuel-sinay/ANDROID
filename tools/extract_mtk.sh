#!/usr/bin/env bash
# Prepare a MediaTek SP-Flash-Tool ROM folder for analysis.
# Converts super -> logical partitions, extracts each filesystem, and
# unpacks the boot ramdisk, leaving the layout analyze_rom.sh expects.
#
# Usage: extract_mtk.sh <DIR_WITH_IMAGES>
#   DIR must contain super.img (or super.img.* sparse chunks) and boot.img.
# Result: <DIR>/fs/{system,vendor,product}, <DIR>/super/, <DIR>/boot/rd
set -uo pipefail
T=/home/user/android/tools
D="$1"; cd "$D" || exit 1
mkdir -p super fs/system fs/vendor fs/product

if [ -f super.img ]; then
  echo "[*] super -> raw"
  if file super.img | grep -qi sparse; then simg2img super.img super.raw && rm super.img; else mv super.img super.raw; fi
  echo "[*] unpack logical partitions"
  python3 "$T/lp_unpack.py" super.raw super >/dev/null && rm super.raw
fi
for p in system vendor product; do
  img="super/${p}_a.img"
  [ -f "$img" ] || img="super/${p}.img"
  if [ -f "$img" ]; then
    debugfs -R "rdump / fs/$p" "$img" >/dev/null 2>&1
    echo "    $p: $(find fs/$p -type f 2>/dev/null | wc -l) files"
  fi
done
if [ -f boot.img ]; then
  echo "[*] boot ramdisk"
  python3 "$T/bootimg.py" boot.img boot >/dev/null 2>&1
  ( cd boot && fmt=$(python3 -c "import json;print(json.load(open('header.json'))['ramdisk_format'])" 2>/dev/null)
    case "$fmt" in gzip) zcat ramdisk > ramdisk.cpio 2>/dev/null;; lz4*) lz4 -dc ramdisk > ramdisk.cpio 2>/dev/null;; esac
    mkdir -p rd && cd rd && cpio -idm --quiet < ../ramdisk.cpio 2>/dev/null )
fi
echo "[*] ready: $D"
