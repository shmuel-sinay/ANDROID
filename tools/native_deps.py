#!/usr/bin/env python3
"""Map the native (.so) dependency graph of an extracted ROM.

For every ELF shared object it records: its SONAME, the libraries it needs
(DT_NEEDED), the init HAL/service interfaces it may implement (by name),
and a count of exported vs imported symbols. From that it builds the
"what builds on what" graph for native code, and flags libraries whose
dependencies are missing from the ROM.

Usage: native_deps.py ROM_FS_DIR OUT.json
Needs: pip install pyelftools
"""
import json
import os
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.elf.sections import SymbolTableSection


def analyze(path):
    with open(path, "rb") as f:
        try:
            elf = ELFFile(f)
        except Exception:
            return None
        info = {"soname": None, "needed": [], "machine": elf["e_machine"],
                "type": elf["e_type"], "exports": 0, "imports": 0, "rpath": []}
        for sec in elf.iter_sections():
            if isinstance(sec, DynamicSection):
                for t in sec.iter_tags():
                    if t.entry.d_tag == "DT_NEEDED":
                        info["needed"].append(t.needed)
                    elif t.entry.d_tag == "DT_SONAME":
                        info["soname"] = t.soname
                    elif t.entry.d_tag in ("DT_RPATH", "DT_RUNPATH"):
                        info["rpath"].append(t.runpath if t.entry.d_tag == "DT_RUNPATH" else t.rpath)
            elif isinstance(sec, SymbolTableSection) and sec.name == ".dynsym":
                for sym in sec.iter_symbols():
                    shndx = sym["st_shndx"]
                    bind = sym["st_info"]["bind"]
                    if bind in ("STB_GLOBAL", "STB_WEAK"):
                        if shndx == "SHN_UNDEF":
                            info["imports"] += 1
                        else:
                            info["exports"] += 1
        return info


def main():
    root, out = sys.argv[1], sys.argv[2]
    libs = {}          # soname/basename -> record
    provided = set()   # every soname + basename present in the ROM
    for part in sorted(os.listdir(root)):
        pdir = os.path.join(root, part)
        if not os.path.isdir(pdir):
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                if not fn.endswith(".so"):
                    continue
                fp = os.path.join(dp, fn)
                if os.path.islink(fp):
                    continue
                info = analyze(fp)
                if info is None:
                    continue
                rel = "/" + os.path.relpath(fp, pdir)
                key = f"{part}:{rel}"
                info["partition"] = part
                info["path"] = rel
                info["name"] = fn
                libs[key] = info
                provided.add(fn)
                if info["soname"]:
                    provided.add(info["soname"])

    # resolve: which NEEDED entries are not present anywhere in the ROM
    for info in libs.values():
        info["needed_missing"] = sorted(set(info["needed"]) - provided)

    # reverse graph: for each provided lib, who needs it
    needed_by = {}
    for key, info in libs.items():
        for dep in info["needed"]:
            needed_by.setdefault(dep, []).append(info["name"])

    # most-depended-on libraries (the native "load-bearing" ones)
    top = sorted(((d, len(set(v))) for d, v in needed_by.items()), key=lambda x: -x[1])[:40]

    missing_all = {}
    for info in libs.values():
        for m in info["needed_missing"]:
            missing_all.setdefault(m, 0)
            missing_all[m] += 1

    report = {
        "root": root,
        "total_libs": len(libs),
        "machines": _count(i["machine"] for i in libs.values()),
        "top_depended_on": [{"lib": d, "needed_by_count": n} for d, n in top],
        "missing_dependencies": dict(sorted(missing_all.items(), key=lambda x: -x[1])),
        "libs": libs,
        "needed_by": {k: sorted(set(v)) for k, v in needed_by.items()},
    }
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(libs)} ELF libraries")
    print("architectures:", report["machines"])
    print(f"distinct missing NEEDED deps: {len(missing_all)}")
    print("top missing:", dict(list(report["missing_dependencies"].items())[:6]))


def _count(it):
    d = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return d


if __name__ == "__main__":
    main()
