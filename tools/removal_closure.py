#!/usr/bin/env python3
"""Recursive removal closure: "what depends on this, and what depends on
THAT" — walked all the way out, not just one hop.

removal_recipe.py already answers, for a single package, what breaks
*directly* (its own boot roles/guards, its own sharedUserId siblings). It
does not then ask: do THOSE siblings have dependents of their own? This
tool does — it keeps expanding generation by generation until nothing new
is found, over two real, data-backed edge types:

  1. sharedUserId siblings (apks.json): removing a package can strip a
     signature/uid identity that other packages rely on.
  2. Java shared-library provider -> consumer (apks.json
     libraries_declared / uses_library): removing a library-providing
     package breaks every app that declares it required, and if one of
     THOSE apps is itself a provider, its own consumers are next.

A separate mode walks the *native* (.so) dependency graph from
native_deps.json the same way, for when the question is about a library
file rather than an APK package (relevant to the video-codec work).

Usage:
  removal_closure.py ROM_DIR pkg PACKAGE_NAME [OUT.json]
  removal_closure.py ROM_DIR lib SONAME [OUT.json]
"""
import json
import os
import sys


def load(d, name, default=None):
    p = os.path.join(d, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def build_pkg_graph(rom):
    apks = load(rom, "apks.json", {"apks": []})["apks"]
    recipes = load(rom, "removal_recipes.json", {"recipes": {}})["recipes"]

    uid_of, pkgs_of_uid = {}, {}
    provides, requires = {}, {}  # lib -> [pkg], pkg -> [(lib, required)]
    for a in apks:
        pkg = a.get("package")
        if not pkg:
            continue
        if a.get("sharedUserId"):
            uid_of[pkg] = a["sharedUserId"]
            pkgs_of_uid.setdefault(a["sharedUserId"], set()).add(pkg)
        for lib in a.get("libraries_declared", []):
            provides.setdefault(lib, set()).add(pkg)
        requires[pkg] = a.get("uses_library", [])

    def edges_from(pkg):
        """-> list of (dependent_pkg, reason), i.e. who breaks if pkg is removed."""
        out = []
        uid = uid_of.get(pkg)
        if uid:
            for sib in pkgs_of_uid.get(uid, ()):
                if sib != pkg:
                    out.append((sib, f'שותף sharedUserId="{uid}"'))
        for consumer, libs in requires.items():
            if consumer == pkg:
                continue
            for entry in libs:
                lib, required = (entry if isinstance(entry, list) else (entry, False))
                if pkg in provides.get(lib, ()) and required:
                    out.append((consumer, f'uses-library חובה "{lib}"'))
        return out

    return edges_from, recipes


def build_lib_graph(rom):
    nat = load(rom, "native_deps.json", {"needed_by": {}, "libs": {}})
    needed_by = nat.get("needed_by", {})

    def edges_from(so_name):
        return [(dep, f"DT_NEEDED -> {so_name}") for dep in needed_by.get(so_name, ())]

    return edges_from, nat.get("libs", {})


def closure(start, edges_from, max_gen=12):
    generations = []
    visited = {start}
    frontier = [start]
    gen = 0
    reasons = {}  # node -> (parent, reason) for the first time it was reached
    while frontier and gen < max_gen:
        gen += 1
        nxt = []
        for node in frontier:
            for dep, reason in edges_from(node):
                if dep not in visited:
                    visited.add(dep)
                    reasons[dep] = (node, reason)
                    nxt.append(dep)
        if not nxt:
            break
        generations.append(sorted(set(nxt)))
        frontier = nxt
    return generations, reasons


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    rom, mode, target = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else None

    if mode == "pkg":
        edges_from, recipes = build_pkg_graph(rom)
        annotate = lambda n: {
            "risk": recipes.get(n, {}).get("risk", "unknown"),
            "verdict": recipes.get(n, {}).get("verdict", "(לא נבדק ב-removal_recipes.json)"),
        }
    elif mode == "lib":
        edges_from, libs = build_lib_graph(rom)
        annotate = lambda n: {"kind": "native .so"}
    else:
        print("mode must be 'pkg' or 'lib'")
        sys.exit(1)

    generations, reasons = closure(target, edges_from)

    report = {"target": target, "mode": mode, "generations": []}
    print(f"סגירה רקורסיבית מ-{target} ({mode}):")
    print(f"  דור 0 (המטרה): {target}  {annotate(target)}")
    for i, g in enumerate(generations, 1):
        gen_entries = []
        for node in g:
            parent, reason = reasons[node]
            info = annotate(node)
            gen_entries.append({"node": node, "via": parent, "reason": reason, **info})
            print(f"  דור {i}: {node}  <- ({reason}, מ-{parent})  {info}")
        report["generations"].append(gen_entries)

    if not generations:
        print("  (אין דור נוסף — שום דבר אחר לא תלוי בזה בדרכים שמופו)")

    if out:
        json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
        print(f"\nנשמר ל-{out}")


if __name__ == "__main__":
    main()
