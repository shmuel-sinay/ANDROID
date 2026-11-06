#!/usr/bin/env python3
"""Find every 'boot guard' in system_server code.

A boot guard is a method that throws when something it requires is
missing (a package, a library, a config value, a file, a service...).
If such a method runs while the system boots, the missing piece turns
into a crash loop.

Usage: boot_guards.py OUT.json JAR_OR_DEX [JAR_OR_DEX ...]
  e.g. boot_guards.py guards.json services.jar framework.jar

For each guard:
  method       - class.method(descriptor)
  messages     - the strings it builds its exception from
  throws       - number of throw instructions
  boot_path    - shortest call chain from a boot entry point, or null
  source       - decompiled Java (only for guards on the boot path)
Needs: pip install androguard
"""
import json
import re
import sys
import zipfile
from collections import deque

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ag_compat  # noqa: E402,F401
from androguard.core.analysis.analysis import Analysis  # noqa: E402
from androguard.core.dex import DEX  # noqa: E402
from androguard.decompiler.decompile import DvMethod  # noqa: E402

GUARD_TEXT = re.compile(
    r"must (be|have|exist)|exactly one|missing|required|not found|no such|"
    r"unable to (find|locate|load)|failed to (find|load|locate)|"
    r"does not exist|cannot find|could not find|expected a package|"
    r"not (installed|available|present)", re.I)

# where the boot starts: everything reachable from these runs while booting
BOOT_ENTRIES = [
    ("Lcom/android/server/SystemServer;", "run"),
    ("Lcom/android/server/SystemServer;", "startBootstrapServices"),
    ("Lcom/android/server/SystemServer;", "startCoreServices"),
    ("Lcom/android/server/SystemServer;", "startOtherServices"),
    ("Lcom/android/server/pm/PackageManagerService;", "<init>"),
    ("Lcom/android/server/pm/PackageManagerService;", "main"),
    ("Lcom/android/server/pm/PackageManagerService;", "systemReady"),
    ("Lcom/android/server/am/ActivityManagerService;", "systemReady"),
    ("Lcom/android/server/am/ActivityManagerService;", "installSystemProviders"),
]
MAX_DEPTH = 12


def load(dx, path):
    if path.endswith(".dex"):
        dx.add(DEX(open(path, "rb").read()))
        return
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if re.fullmatch(r"classes\d*\.dex", n):
                dx.add(DEX(z.read(n)))


def name_of(m):
    return f"{m.get_class_name()[1:-1].replace('/', '.')}.{m.get_name()}{m.get_descriptor()}"


def main():
    out_path, inputs = sys.argv[1], sys.argv[2:]
    dx = Analysis()
    loaded = []
    for p in inputs:
        if os.path.exists(p):
            load(dx, p)
            loaded.append(p)
    dx.create_xref()

    # 1. candidate guards: methods that throw and carry a "required" message
    guards = {}
    for ma in dx.get_methods():
        if ma.is_external():
            continue
        m = ma.get_method()
        # A message counts only when it sits between "new-instance X(Exception|Error)"
        # and the next "throw" - the usual javac shape of `throw new X("..." + y)`.
        msgs, throws, exc = [], 0, set()
        pending = None  # exception type currently being built
        window = []
        for ins in m.get_instructions():
            op = ins.get_name()
            if op == "new-instance":
                t = ins.get_output().split(", ")[-1]
                if t.endswith(("Exception;", "Error;")):
                    pending, window = t[1:-1].split("/")[-1], []
            elif op.startswith("const-string") and pending:
                window.append(ins.get_output().split(", ", 1)[-1].strip("'\""))
            elif op == "throw":
                throws += 1
                if pending:
                    hit = [s for s in window if GUARD_TEXT.search(s)]
                    if hit:
                        msgs += hit
                        exc.add(pending)
                pending, window = None, []
            elif op.startswith("return"):
                pending, window = None, []
        if msgs:
            guards[name_of(m)] = {"ma": ma, "messages": msgs, "throws": throws,
                                  "exceptions": sorted(exc)}

    # 2. forward BFS from the boot entry points over "calls" edges
    parent = {}
    queue = deque()
    for cls, meth in BOOT_ENTRIES:
        for ma in dx.find_methods(classname=re.escape(cls), methodname="^" + re.escape(meth) + "$"):
            if not ma.is_external():
                k = name_of(ma.get_method())
                parent[k] = None
                queue.append((ma, 0))
    while queue:
        ma, depth = queue.popleft()
        if depth >= MAX_DEPTH:
            continue
        here = name_of(ma.get_method())
        for _c, callee, _o in ma.get_xref_to():
            if callee.is_external():
                continue
            k = name_of(callee.get_method())
            if k not in parent:
                parent[k] = here
                queue.append((callee, depth + 1))

    def chain(k):
        path = []
        while k is not None:
            path.append(k)
            k = parent.get(k)
        return list(reversed(path))

    # 3. report
    result = []
    for k, g in sorted(guards.items()):
        on_boot = k in parent
        entry = {"method": k, "messages": g["messages"], "throws": g["throws"],
                 "exceptions": g["exceptions"],
                 "callers": sorted({name_of(c.get_method()) for _x, c, _o in g["ma"].get_xref_from()
                                    if not c.is_external()})[:20],
                 "boot_path": chain(k) if on_boot else None}
        if on_boot:
            try:
                dv = DvMethod(g["ma"])
                dv.process()
                entry["source"] = dv.get_source()
            except Exception as e:  # decompiler limits; keep the guard anyway
                entry["source"] = f"(decompile failed: {e})"
        result.append(entry)
    result.sort(key=lambda e: (e["boot_path"] is None, len(e["boot_path"] or []), e["method"]))
    json.dump({"inputs": inputs, "boot_entries": BOOT_ENTRIES, "max_depth": MAX_DEPTH,
               "guards_total": len(result),
               "guards_on_boot_path": sum(1 for e in result if e["boot_path"]),
               "guards": result}, open(out_path, "w"), indent=1, ensure_ascii=False)
    print(f"{len(result)} guards, {sum(1 for e in result if e['boot_path'])} on boot path")


if __name__ == "__main__":
    main()
