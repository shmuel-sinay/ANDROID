#!/usr/bin/env python3
"""Catalogue the RRO overlays already present in a ROM.

Each overlay APK declares a <overlay targetPackage="..."> and carries
resources that replace the target's. This tool lists, per overlay, what it
targets and which resource values it overrides (with the new value) — real,
working examples of the override method the user can copy.

Usage: overlays.py OUT.json ROM_FS_DIR
Needs: aapt
"""
import json
import os
import re
import subprocess
import sys

OVERLAY_RE = re.compile(r"E: overlay")
TARGET_RE = re.compile(r'targetPackage[^=]*="([^"]+)"')
RES_RE = re.compile(r"resource 0x[0-9a-f]+ [^:]+:(\w+)/(\S+?): ")
VAL_RE = re.compile(r"\((boolean|string8|integer|dimension|color|reference)\)\s*(.*)")


def target_of(apk):
    txt = subprocess.run(["aapt", "dump", "xmltree", apk, "AndroidManifest.xml"],
                         capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    in_overlay = False
    for line in txt.splitlines():
        s = line.strip()
        if OVERLAY_RE.match(s):
            in_overlay = True
        elif in_overlay:
            m = TARGET_RE.search(s)
            if m:
                return m.group(1)
    return None


def overrides(apk):
    txt = subprocess.run(["aapt", "dump", "--values", "resources", apk],
                         capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    out, pend = {}, None
    types = {}
    for line in txt.splitlines():
        s = line.strip()
        m = RES_RE.match(s)
        if m:
            typ, name = m.groups()
            types[typ] = types.get(typ, 0) + 1
            pend = (typ, name) if typ in ("bool", "integer", "string", "color", "dimen", "array") else None
            continue
        m2 = VAL_RE.match(s)
        if m2 and pend:
            out[pend[1]] = {"type": pend[0], "value": m2.group(2).strip().strip('"')}
            pend = None
    return types, out


def main():
    out, root = sys.argv[1], sys.argv[2]
    apks = []
    for dp, _dn, fns in os.walk(root):
        if "/overlay/" in dp + "/":
            for f in fns:
                if f.endswith(".apk"):
                    apks.append(os.path.join(dp, f))
    result = []
    for apk in sorted(apks):
        try:
            tgt = target_of(apk)
            types, ov = overrides(apk)
        except (subprocess.TimeoutExpired, OSError):
            continue
        result.append({
            "overlay": "/" + os.path.relpath(apk, root),
            "target": tgt,
            "resource_types": types,
            "override_count": len(ov),
            "overrides": ov,
        })
    json.dump({"overlay_count": len(result), "overlays": result},
              open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(result)} overlays")
    for r in result[:8]:
        print(f"  {os.path.basename(r['overlay']):50} -> {r['target']} ({r['override_count']} values)")


if __name__ == "__main__":
    main()
