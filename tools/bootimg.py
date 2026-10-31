#!/usr/bin/env python3
"""Unpack Android boot images (header v0-v2) without external tools.

Usage: bootimg.py boot.img OUT_DIR
Writes kernel, ramdisk (raw), second, recovery_dtbo, dtb and header.json.
"""
import json
import os
import struct
import sys


def pages(size, page):
    return (size + page - 1) // page


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    data = open(src, "rb").read()
    if data[:8] != b"ANDROID!":
        raise SystemExit("not an Android boot image")
    (k_size, k_addr, r_size, r_addr, s_size, s_addr, tags, page,
     hver, osv) = struct.unpack_from("<10I", data, 8)
    name = data[48:64].split(b"\0")[0].decode()
    cmdline = data[64:576].split(b"\0")[0].decode()
    extra = data[608:1632].split(b"\0")[0].decode()
    hdr = {
        "header_version": hver, "page_size": page,
        "kernel_size": k_size, "kernel_addr": hex(k_addr),
        "ramdisk_size": r_size, "ramdisk_addr": hex(r_addr),
        "second_size": s_size, "tags_addr": hex(tags),
        "os_version": f"{(osv >> 25) & 0x7f}.{(osv >> 18) & 0x7f}.{(osv >> 11) & 0x7f}",
        "os_patch_level": f"{((osv >> 4) & 0x7f) + 2000}-{osv & 0xf:02d}",
        "name": name, "cmdline": (cmdline + extra).strip(),
    }
    off = page  # header occupies one page
    blobs = [("kernel", k_size), ("ramdisk", r_size), ("second", s_size)]
    if hver >= 1:
        rd_size, rd_off, hsize = struct.unpack_from("<IQI", data, 1632)
        hdr["recovery_dtbo_size"] = rd_size
        blobs.append(("recovery_dtbo", rd_size))
    if hver >= 2:
        dtb_size, dtb_addr = struct.unpack_from("<IQ", data, 1648)
        hdr["dtb_size"] = dtb_size
        hdr["dtb_addr"] = hex(dtb_addr)
        blobs.append(("dtb", dtb_size))
    for bname, size in blobs:
        if size:
            open(os.path.join(out, bname), "wb").write(data[off:off + size])
        off += pages(size, page) * page
    # identify ramdisk compression
    rd = data[page + pages(k_size, page) * page:][:4]
    hdr["ramdisk_format"] = ("gzip" if rd[:2] == b"\x1f\x8b" else
                             "lz4_legacy" if rd == b"\x02\x21\x4c\x18" else
                             "lz4_frame" if rd == b"\x04\x22\x4d\x18" else rd.hex())
    json.dump(hdr, open(os.path.join(out, "header.json"), "w"), indent=2)
    print(json.dumps(hdr, indent=2))


if __name__ == "__main__":
    main()
