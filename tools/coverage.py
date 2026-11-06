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
    (lambda p, n, x: x in ("bak", "old", "orig") or n.endswith(".apk.a") or ".apk." in n, "backup", "leftover backup copy — original analysed separately", "listed"),
    (lambda p, n, x: x == "apk", "apk", "apk_inventory.py: manifest, perms, priv-app, intents", "parsed"),
    (lambda p, n, x: x == "jar", "jar", "boot_guards.py: dex scanned for boot guards (framework/services)", "partial"),
    (lambda p, n, x: x == "so", "native_lib", "native_deps.py: SONAME, DT_NEEDED deps, export/import counts", "parsed"),
    (lambda p, n, x: x in ("der", "crt", "cer", "pem", "pk8", "x509", "avbpubkey") or n == "apex_pubkey" or "cacerts" in p or "/security/" in p, "cert_key", "trust anchor / signing key — indexed", "listed"),
    (lambda p, n, x: n.endswith("_contexts") or "sepolicy" in n or n.endswith("mac_permissions.xml") or x in ("cil", "policy"), "selinux", "selinux.py: contexts / CIL policy parsed", "parsed"),
    (lambda p, n, x: x in ("prof", "bprof"), "art_profile", "ART dexlayout profile — build artifact", "listed"),
    (lambda p, n, x: n in ("passwd", "group", "fs_config_dirs", "fs_config_files", "ld.config.txt") or x in ("tz", "idc") or n in ("tzdata", "tz_version"), "system_config", "passwd/group/fs_config/tz — static system config", "listed"),
    (lambda p, n, x: x in ("odex", "vdex", "oat", "art"), "aot", "pre-compiled AOT image (mirrors its jar/apk dex)", "listed"),
    (lambda p, n, x: x == "rc", "init_rc", "init_rc.py: services, actions, triggers", "parsed"),
    (lambda p, n, x: n == "build.prop" or x == "prop", "prop", "build.prop parsed (key props surfaced)", "parsed"),
    (lambda p, n, x: x == "xml" and "permissions" in p, "privapp_xml", "apk_inventory.py: privapp-permissions allowlists", "parsed"),
    (lambda p, n, x: x == "xml" and ("sysconfig" in p or "sku" in p), "sysconfig_xml", "xml_config.py: VINTF HALs, features, libraries", "parsed"),
    (lambda p, n, x: x == "xml", "xml_other", "xml_config.py: root tag + declared content", "parsed"),
    (lambda p, n, x: n == "fstab" or n.startswith("fstab."), "fstab", "BOOT_CHAIN.md: mount + avb flags", "parsed"),
    (lambda p, n, x: x in ("te", "cil", "policy") or "sepolicy" in n, "selinux", "SELinux policy — not yet parsed", "pending"),
    (lambda p, n, x: x in ("kl", "kcm", "idc"), "input_map", "input key-layout — static data", "listed"),
    (lambda p, n, x: x in ("ttf", "otf", "ttc", "hyb"), "font", "font asset", "listed"),
    (lambda p, n, x: x in ("ogg", "mp3", "wav", "qmg"), "audio", "sound/animation asset", "listed"),
    (lambda p, n, x: x in ("png", "jpg", "jpeg", "webp", "gif", "bmp"), "image", "image asset", "listed"),
    (lambda p, n, x: x in ("gz", "zip", "tgz", "xz", "model", "bmd", "lock"), "asset_blob", "compressed/model/binary asset — indexed", "listed"),
    (lambda p, n, x: n in ("hosts", "mkshrc", "event-log-tags", "preloaded-classes", "dirty-image-objects", "prop.default", "compatibility_matrix.xml") or x == "default", "system_config", "static system config — indexed", "listed"),
    (lambda p, n, x: n == "apex_manifest.pb", "apex_manifest", "misc_files.py: APEX name + version", "parsed"),
    (lambda p, n, x: x in ("apex", "capex"), "apex_archive", "apex_unpack.py: payload extracted to apex_extracted/ and analysed", "parsed"),
    (lambda p, n, x: "seccomp" in n, "selinux", "selinux.py: seccomp syscall filter", "parsed"),
    (lambda p, n, x: x in ("bfbs", "fbs"), "flatbuffer", "flatbuffer schema/data — indexed", "listed"),
    (lambda p, n, x: x in ("mp4", "webm", "m4v", "qmg"), "video", "video/animation asset", "listed"),
    (lambda p, n, x: x == "csv", "text", "csv data — indexed", "listed"),
    (lambda p, n, x: x in ("ta", "fsm", "drbg", "ski") or n.startswith("aee-") or "/thh/" in p, "vendor_blob", "TEE app / firmware / AEE debug blob — indexed", "listed"),
    (lambda p, n, x: "/srec/" in p or "/tts/" in p or x in ("fst", "mfar", "mmap", "syms", "lstm", "far", "dnn", "klatt", "pumpkin"), "speech_model", "speech/TTS model data — indexed", "listed"),
    (lambda p, n, x: n in ("bug_map", "remoteproc_scp", "out-of-process") or "remoteproc" in n, "binary_data", "firmware/debug blob — indexed", "listed"),
    (lambda p, n, x: x in ("pb", "txtpb", "pbtxt", "binarypb"), "protobuf", "protobuf blob — indexed", "listed"),
    (lambda p, n, x: x in ("bin", "dat", "db", "bc", "ko", "img", "mdl", "map", "cfg", "conf", "ser", "dic"), "binary_data", "binary/config blob", "listed"),
    (lambda p, n, x: x in ("sh", "rc_sh"), "script", "misc_files.py: shebang, purpose, commands", "parsed"),
    (lambda p, n, x: x in ("txt", "json", "conf", "ini", "cfg", "version", "md", "html", "css", "js", "xsd", "dtd", "proto"), "text", "text/config — indexed", "listed"),
]


def is_elf(fp):
    try:
        with open(fp, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def categorize(path, name, fp=None):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for test, cat, how, depth in RULES:
        if test(path.lower(), name.lower(), ext):
            return cat, how, depth
    # kernel module metadata (dependency graph, load order)
    if name.startswith("modules."):
        return "kernel_modules", "misc_files.py: modules.dep graph / load order", "parsed"
    # MediaTek thermal / debug / supl config blobs under vendor
    if ("/.tp/" in path or "/apdb/" in path or name in ("slp_conf", "selinux_denial_metadata")
            or name.startswith("apdb")):
        return "vendor_blob", "vendor (MTK) config/debug blob — indexed", "listed"
    if ext in ("mk", "cnf", "conf", "config"):
        return "text", "text/config — indexed", "listed"
    # fall back to content sniffing for extension-less files
    if fp:
        if is_elf(fp):
            return "native_exec", "native_deps.py: ELF executable (HAL service / daemon), DT_NEEDED deps", "parsed"
        try:
            with open(fp, "rb") as f:
                head = f.read(2)
            # a /bin command is a text wrapper (shebang, or a leading comment)
            if head[:1] in (b"#", b"\n") or "/bin/" in path:
                return "script", "misc_files.py: shell command wrapper", "parsed"
        except OSError:
            pass
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
                    cat, how, depth = categorize(rel, fn, fp)
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
