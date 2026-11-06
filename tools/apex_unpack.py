#!/usr/bin/env python3
"""Extract every APEX in a ROM into the filesystem tree, so the normal
analyzers (apk_inventory, native_deps, ...) see their contents too.

On Android 10+ many critical components (PermissionController, ExtServices,
media, conscrypt, tzdata, ART ...) ship inside .apex / .capex files, which
are ZIPs holding an ext4 'apex_payload.img'. Without extracting them the
coverage is incomplete and boot-role detection gives false "missing".

For each <name>.apex found under ROM_FS_DIR this writes its payload files to
  ROM_FS_DIR/apex_extracted/<name>/
so a second analysis pass can include them.

Usage: apex_unpack.py ROM_FS_DIR
Needs: unzip, debugfs (e2fsprogs), simg2img for sparse payloads.
"""
import json
import os
import subprocess
import sys
import tempfile
import zipfile


def extract_payload(payload, dest):
    os.makedirs(dest, exist_ok=True)
    # payload may be sparse; convert if so
    with open(payload, "rb") as f:
        magic = f.read(4)
    img = payload
    if magic == b"\x3a\xff\x26\xed":  # android sparse
        img = payload + ".raw"
        subprocess.run(["simg2img", payload, img], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run(["debugfs", "-R", f"rdump / {dest}", img],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def main():
    root = sys.argv[1]
    out_root = os.path.join(root, "apex_extracted")
    os.makedirs(out_root, exist_ok=True)
    done = []
    for part in sorted(os.listdir(root)):
        pdir = os.path.join(root, part)
        if not os.path.isdir(pdir) or pdir == out_root:
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                if not fn.endswith((".apex", ".capex")):
                    continue
                fp = os.path.join(dp, fn)
                name = fn.rsplit(".", 1)[0]
                dest = os.path.join(out_root, name)
                if os.path.isdir(dest) and os.listdir(dest):
                    continue
                try:
                    with tempfile.TemporaryDirectory() as td:
                        with zipfile.ZipFile(fp) as z:
                            payload = None
                            for nm in z.namelist():
                                if nm in ("apex_payload.img", "original_apex") or nm.endswith(".img"):
                                    z.extract(nm, td)
                                    if nm.endswith(".img"):
                                        payload = os.path.join(td, nm)
                        if payload and extract_payload(payload, dest):
                            cnt = sum(len(f) for _d, _n, f in os.walk(dest))
                            done.append({"apex": f"{part}:/{os.path.relpath(fp, pdir)}",
                                         "extracted_to": dest, "files": cnt})
                except (zipfile.BadZipFile, OSError) as ex:
                    done.append({"apex": fp, "error": str(ex)})
    print(json.dumps({"apex_count": len(done), "apexes": done}, indent=1, ensure_ascii=False))
    ok = [d for d in done if "files" in d]
    print(f"\nextracted {len(ok)} APEX payloads, "
          f"{sum(d['files'] for d in ok)} files total", file=sys.stderr)


if __name__ == "__main__":
    main()
