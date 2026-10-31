#!/usr/bin/env python3
"""Minimal reader for Android dynamic-partition (liblp) super images.

Usage: lp_unpack.py super.raw OUT_DIR [--list]
Reads the primary metadata of slot 0 and writes each logical partition
as a raw image. Only 'linear' and 'zero' extents exist in liblp.
"""
import json
import os
import struct
import sys

SECTOR = 512
GEOMETRY_OFFSET = 4096
GEOMETRY_MAGIC = 0x616C4467
HEADER_MAGIC = 0x414C5030


def read_metadata(f):
    f.seek(GEOMETRY_OFFSET)
    g = f.read(52)
    magic, _size = struct.unpack_from("<II", g, 0)
    if magic != GEOMETRY_MAGIC:
        raise SystemExit("not a super image (bad geometry magic)")
    max_size, slot_count, block_size = struct.unpack_from("<III", g, 40)

    # geometry + backup geometry, then primary metadata slot 0
    meta_off = GEOMETRY_OFFSET * 3
    f.seek(meta_off)
    h = f.read(256)
    magic, major, minor, header_size = struct.unpack_from("<IHHI", h, 0)
    if magic != HEADER_MAGIC:
        raise SystemExit("bad metadata header magic")
    tables_size = struct.unpack_from("<I", h, 44)[0]
    desc = struct.unpack_from("<12I", h, 80)
    f.seek(meta_off + header_size)
    tables = f.read(tables_size)

    def table(i):
        off, num, size = desc[i * 3: i * 3 + 3]
        return [tables[off + k * size: off + (k + 1) * size] for k in range(num)]

    groups = []
    for e in table(2):
        name = e[:36].split(b"\0")[0].decode()
        flags, max_sz = struct.unpack_from("<IQ", e, 36)
        groups.append({"name": name, "flags": flags, "maximum_size": max_sz})

    extents = []
    for e in table(1):
        n, ttype, tdata, tsrc = struct.unpack_from("<QIQI", e, 0)
        extents.append({"sectors": n, "type": "linear" if ttype == 0 else "zero",
                        "target_sector": tdata, "source": tsrc})

    devices = []
    for e in table(3):
        first, align, align_off, size = struct.unpack_from("<QIIQ", e, 0)
        name = e[24:60].split(b"\0")[0].decode()
        devices.append({"name": name, "first_logical_sector": first, "size": size})

    parts = []
    for e in table(0):
        name = e[:36].split(b"\0")[0].decode()
        attrs, first, num, gidx = struct.unpack_from("<IIII", e, 36)
        ex = extents[first:first + num]
        parts.append({
            "name": name,
            "attributes": attrs,
            "readonly": bool(attrs & 1),
            "group": groups[gidx]["name"] if gidx < len(groups) else gidx,
            "size": sum(x["sectors"] for x in ex) * SECTOR,
            "extents": ex,
        })

    return {
        "metadata_version": f"{major}.{minor}",
        "metadata_max_size": max_size,
        "metadata_slot_count": slot_count,
        "logical_block_size": block_size,
        "block_devices": devices,
        "groups": groups,
        "partitions": parts,
    }


def extract(f, part, out_path):
    with open(out_path, "wb") as o:
        for ex in part["extents"]:
            length = ex["sectors"] * SECTOR
            if ex["type"] == "zero":
                o.seek(length, 1)
                continue
            f.seek(ex["target_sector"] * SECTOR)
            left = length
            while left:
                chunk = f.read(min(left, 16 << 20))
                if not chunk:
                    raise SystemExit("unexpected end of image")
                o.write(chunk)
                left -= len(chunk)
        o.truncate()


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    with open(src, "rb") as f:
        meta = read_metadata(f)
        with open(os.path.join(out, "lp_metadata.json"), "w") as j:
            json.dump(meta, j, indent=2)
        for p in meta["partitions"]:
            print(f'{p["name"]:24} {p["size"]:>12}  group={p["group"]}')
            if "--list" not in sys.argv and p["size"]:
                extract(f, p, os.path.join(out, p["name"] + ".img"))


if __name__ == "__main__":
    main()
