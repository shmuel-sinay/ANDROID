#!/usr/bin/env python3
"""Parse the SELinux policy files of an extracted ROM into structured data.

Covers the text policy files shipped on device:
  *_file_contexts      path regex  -> security context
  *_property_contexts  property    -> context
  *_service_contexts   service     -> context (binder)
  *_hwservice_contexts hidl service-> context
  *_seapp_contexts     app rules   -> domain/type (how apps get a domain)
  *.cil                CIL policy statements (counts by kind)
  mac_permissions.xml  signer      -> seinfo

The point is coverage and the app->domain mapping (seapp_contexts), which
is the SELinux side of "what runs as what". Full allow-rule reasoning needs
the compiled sepolicy binary and is out of scope here.

Usage: selinux.py ROM_FS_DIR OUT.json
"""
import json
import os
import re
import sys


def parse_contexts(path):
    rows = []
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append({"key": parts[0], "context": parts[-1]})
    return rows


def parse_seapp(path):
    rows = []
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = dict(tok.split("=", 1) for tok in line.split() if "=" in tok)
        if d:
            rows.append(d)
    return rows


def parse_cil(path):
    kinds = {}
    for line in open(path, errors="replace"):
        s = line.strip()
        if s.startswith("("):
            kw = s[1:].split(None, 1)[0] if len(s) > 1 else ""
            kinds[kw] = kinds.get(kw, 0) + 1
    return kinds


def main():
    root_dir, out = sys.argv[1], sys.argv[2]
    files = []
    totals = {"file_contexts": 0, "property_contexts": 0, "service_contexts": 0,
              "hwservice_contexts": 0, "seapp_rules": 0, "cil_statements": 0}
    seapp_all = []
    for part in sorted(os.listdir(root_dir)):
        pdir = os.path.join(root_dir, part)
        if not os.path.isdir(pdir):
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                fp = os.path.join(dp, fn)
                if os.path.islink(fp):
                    continue
                rel = "/" + os.path.relpath(fp, pdir)
                entry = {"partition": part, "path": rel, "size": os.path.getsize(fp)}
                try:
                    if fn.endswith("_seapp_contexts") or fn == "seapp_contexts":
                        rows = parse_seapp(fp)
                        entry["kind"] = "seapp_contexts"
                        entry["rules"] = len(rows)
                        totals["seapp_rules"] += len(rows)
                        for r in rows:
                            seapp_all.append({**r, "from": f"{part}:{rel}"})
                    elif fn.endswith("_file_contexts") or fn == "file_contexts":
                        entry["kind"] = "file_contexts"
                        entry["entries"] = len(parse_contexts(fp))
                        totals["file_contexts"] += entry["entries"]
                    elif fn.endswith("_property_contexts"):
                        entry["kind"] = "property_contexts"
                        entry["entries"] = len(parse_contexts(fp))
                        totals["property_contexts"] += entry["entries"]
                    elif fn.endswith("_hwservice_contexts"):
                        entry["kind"] = "hwservice_contexts"
                        entry["entries"] = len(parse_contexts(fp))
                        totals["hwservice_contexts"] += entry["entries"]
                    elif fn.endswith("_service_contexts") or fn == "service_contexts":
                        entry["kind"] = "service_contexts"
                        entry["entries"] = len(parse_contexts(fp))
                        totals["service_contexts"] += entry["entries"]
                    elif fn.endswith(".cil"):
                        kinds = parse_cil(fp)
                        entry["kind"] = "cil"
                        entry["statements"] = kinds
                        totals["cil_statements"] += sum(kinds.values())
                    elif fn.endswith(".policy"):
                        # seccomp syscall filter: one syscall name per line
                        sy: list = []
                        for line in open(fp, errors="replace"):
                            s = line.split("#", 1)[0].split(":", 1)[0].strip()
                            if s and s.replace("_", "").isalnum():
                                sy.append(s)
                        entry["kind"] = "seccomp_policy"
                        entry["allowed_syscalls"] = len(set(sy))
                        totals.setdefault("seccomp_syscalls", 0)
                        totals["seccomp_syscalls"] += len(set(sy))
                    else:
                        continue
                except OSError:
                    continue
                files.append(entry)

    report = {"root_dir": root_dir, "totals": totals, "file_count": len(files),
              "seapp_rules": seapp_all, "files": files}
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(files)} SELinux policy files")
    print("totals:", totals)


if __name__ == "__main__":
    main()
