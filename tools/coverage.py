#!/usr/bin/env python3
"""Build a complete coverage ledger for an extracted ROM.

Goal: account for EVERY file in the ROM, so nothing is silently skipped.
Each file is listed with its size, sha256, partition, and a category.
Each category is marked with how deeply the project analyzes it today, so
"what has not been looked at yet" is a number you can read, not a guess.

Usage: coverage.py ROM_FS_DIR OUT.json [--hash]
  ROM_FS_DIR holds system/ vendor/ product/ (the extracted partitions).
  --hash computes sha256 for every file (slower). Without it, sizes only.
"""
import hashlib
import json
import os
import stat
import sys

# category -> (how it is analysed today, depth)
# depth: "parsed" = a tool reads its structure; "listed" = only indexed;
#        "pending" = recognised but no analyzer yet.
RULES = [
    # (test(path, name, ext) -> bool, category, how, depth)
    (lambda p, n, x: x == "apk", "apk", "apk_inventory.py: manifest, perms, priv-app, intents", "parsed"),
    (lambda p, n, x: x == "jar", "jar", "boot_guards.py: dex scanned for boot guards (framework/services)", "partial"),
    (lambda p, n, x: x == "so", "native_lib", "native_deps.py: SONAME, DT_NEEDED deps, export/import counts", "parsed"),
    (lambda p, n, x: x in ("odex", "vdex", "oat", "art"), "aot", "pre-compiled AOT image (mirrors its jar/apk dex)", "listed"),
    (lambda p, n, x: x == "rc", "init_rc", "init_rc.py: services, actions, triggers", "parsed"),
    (lambda p, n, x: n == "build.prop" or x == "prop", "prop", "build.prop parsed (key props surfaced)", "parsed"),
    (lambda p, n, x: x == "xml" and "permissions" in p, "privapp_xml", "apk_inventory.py: privapp-permissions allowlists", "parsed"),
    (lambda p, n, x: x == "xml" and ("sysconfig" in p or "sku" in p), "sysconfig_xml", "sysconfig/permissions xml — not yet parsed", "pending"),
    (lambda p, n, x: x == "xml", "xml_other", "config xml — not yet parsed", "pending"),
    (lambda p, n, x: n == "fstab" or n.startswith("fstab."), "fstab", "BOOT_CHAIN.md: mount + avb flags", "parsed"),
    (lambda p, n, x: x in ("te", "cil", "policy") or "sepolicy" in n, "selinux", "SELinux policy — not yet parsed", "pending"),
    (lambda p, n, x: x in ("kl", "kcm", "idc"), "input_map", "input key-layout — static data", "listed"),
    (lambda p, n, x: x in ("ttf", "otf", "hyb"), "font", "font asset", "listed"),
    (lambda p, n, x: x in ("ogg", "mp3", "wav", "qmg"), "audio", "sound/animation asset", "listed"),
    (lambda p, n, x: x in ("png", "jpg", "jpeg", "webp", "gif", "bmp"), "image", "image asset", "listed"),
    (lambda p, n, x: x in ("pb", "txtpb", "pbtxt"), "protobuf", "protobuf data — not yet parsed", "pending"),
    (lambda p, n, x: x in ("bin", "dat", "db", "bc", "ko", "img", "mdl", "map", "cfg", "conf", "ser", "dic"), "binary_data", "binary/config blob", "listed"),
    (lambda p, n, x: x in ("sh", "rc_sh"), "script", "shell script — not yet read line by line", "pending"),
    (lambda p, n, x: x in ("txt", "json", "conf", "ini", "cfg", "version", "md", "html", "css", "js", "xsd", "dtd", "proto"), "text", "text/config — indexed", "listed"),
]


def categorize(path, name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for test, cat, how, depth in RULES:
        if test(path.lower(), name.lower(), ext):
            return cat, how, depth
    return "other", "unclassified — needs a rule", "pending"


def main():
    root, out = sys.argv[1], sys.argv[2]
    do_hash = "--hash" in sys.argv
    files, cats = [], {}
    totals = {"files": 0, "bytes": 0, "symlinks": 0}
    for part in sorted(os.listdir(root)):
        pdir = os.path.join(root, part)
        if not os.path.isdir(pdir):
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                fp = os.path.join(dp, fn)
                rel = "/" + os.path.relpath(fp, pdir)
                try:
                    st = os.lstat(fp)
                except OSError:
                    continue
                if stat.S_ISLNK(st.st_mode):
                    totals["symlinks"] += 1
                    cat, how, depth = "symlink", "symbolic link", "listed"
                    size, digest = 0, None
                else:
                    cat, how, depth = categorize(rel, fn)
                    size = st.st_size
                    digest = None
                    if do_hash and size:
                        h = hashlib.sha256()
                        with open(fp, "rb") as f:
                            for chunk in iter(lambda: f.read(1 << 20), b""):
                                h.update(chunk)
                        digest = h.hexdigest()
                    totals["files"] += 1
                    totals["bytes"] += size
                files.append({"partition": part, "path": rel, "size": size,
                              "sha256": digest, "category": cat, "depth": depth})
                c = cats.setdefault(cat, {"how": how, "depth": depth, "count": 0, "bytes": 0})
                c["count"] += 1
                c["bytes"] += size

    by_depth = {}
    for c in cats.values():
        d = by_depth.setdefault(c["depth"], {"count": 0, "bytes": 0})
        d["count"] += c["count"]
        d["bytes"] += c["bytes"]

    report = {
        "root": root, "hashed": do_hash, "totals": totals,
        "by_depth": by_depth,
        "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1]["count"])),
        "files": files,
    }
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    analysed = sum(v["count"] for k, v in by_depth.items() if k in ("parsed", "partial"))
    print(f"{totals['files']} files, {totals['bytes']/1e9:.2f} GB")
    print("by depth:", {k: v["count"] for k, v in sorted(by_depth.items())})
    print(f"covered by an analyzer (parsed/partial): {analysed} files")


if __name__ == "__main__":
    main()
