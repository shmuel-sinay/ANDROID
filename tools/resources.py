#!/usr/bin/env python3
"""Deep resource scan of every APK in a ROM.

For each APK it records, via aapt:
  - resource type counts (how many drawables, strings, layouts ...)
  - every primitive "knob" resource (bool / integer / string / dimen /
    color) whose name looks like a configuration switch
    (config_*, def_*, status_bar*, show*, enable*, default_*),
    with its resolved value -> these are the add/remove-feature switches
  - the list of named arrays (with element counts)
  - drawable names that match a query (so an icon can be located)

The knobs are what you override with an RRO overlay to add or remove a
feature (e.g. a status-bar icon, the battery percentage, a default app).

Usage: resources.py OUT.json APK [APK ...]
       resources.py OUT.json --walk ROM_FS_DIR   (all APKs)
Needs: aapt
"""
import json
import os
import re
import subprocess
import sys

KNOB_RE = re.compile(r"(config_|def_|default_|status_bar|statusbar|show|enable|"
                     r"allow|is_|has_|max_|min_|feature_)", re.I)
SPEC_RE = re.compile(r"spec resource 0x[0-9a-f]+ ([^:]+):([a-z]+)/(\S+?):")
RES_RE = re.compile(r"resource 0x[0-9a-f]+ ([^:]+):([a-z]+)/(\S+?): ")
TYPEVAL_RE = re.compile(r"\((boolean|string8|dimension|color|integer|float|reference)\)\s*(.*)")


def scan(apk):
    try:
        out = subprocess.run(["aapt", "dump", "--values", "resources", apk],
                             capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
    except (subprocess.TimeoutExpired, OSError):
        return None
    type_counts, knobs, arrays, drawables = {}, {}, {}, []
    pkg = None
    cur_array = None        # array name currently collecting entries
    pending = None          # (type, name) awaiting its value on the next line
    for line in out.splitlines():
        s = line.strip()
        m = SPEC_RE.match(s)
        if m:
            pkg, typ, name = m.group(1), m.group(2), m.group(3)
            type_counts[typ] = type_counts.get(typ, 0) + 1
            if typ == "drawable":
                drawables.append(name)
            continue
        m = RES_RE.match(s)
        if m:
            _pkg, typ, name = m.groups()
            pending = (typ, name) if typ in ("bool", "integer", "string", "dimen", "color") else None
            cur_array = name if typ == "array" else None
            if typ == "array":
                arrays.setdefault(name, 0)
            continue
        m = TYPEVAL_RE.match(s)
        if m and pending:
            typ, name = pending
            if KNOB_RE.search(name):
                knobs[name] = {"type": typ, "value": m.group(2).strip().strip('"')}
            pending = None
            continue
        if cur_array and ("Key=" in s or "(string8)" in s or "(reference)" in s):
            arrays[cur_array] = arrays.get(cur_array, 0) + 1
    return {"package": pkg, "type_counts": type_counts, "knob_count": len(knobs),
            "knobs": knobs, "arrays": arrays, "drawable_count": len(drawables),
            "drawables": drawables}


def main():
    out = sys.argv[1]
    if sys.argv[2] == "--walk":
        apks = []
        for dp, _dn, fns in os.walk(sys.argv[3]):
            for f in fns:
                if f.endswith(".apk"):
                    apks.append(os.path.join(dp, f))
    else:
        apks = sys.argv[2:]
    result = {}
    for apk in sorted(apks):
        info = scan(apk)
        if info:
            result[apk] = info
    total_knobs = sum(v["knob_count"] for v in result.values())
    json.dump({"apk_count": len(result), "total_knobs": total_knobs, "apks": result},
              open(out, "w"), indent=1, ensure_ascii=False, default=str)
    print(f"{len(result)} APKs, {total_knobs} config knobs")


if __name__ == "__main__":
    main()
