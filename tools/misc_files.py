#!/usr/bin/env python3
"""Cover the small long-tail file kinds of a ROM: shell scripts, APEX
manifests (protobuf), and other short text/config blobs.

  *.sh              -> shebang, purpose comment, referenced commands
  apex_manifest.pb  -> APEX name + version (generic protobuf wire decode)
  text config       -> first lines indexed

Usage: misc_files.py ROM_FS_DIR OUT.json [path ...]
Without explicit paths it walks ROM_FS_DIR for *.sh and apex_manifest.pb.
"""
import json
import os
import sys


def read_varint(buf, i):
    shift = result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def decode_protobuf(buf):
    """Minimal protobuf wire decode -> {field_number: [values]}."""
    out, i = {}, 0
    n = len(buf)
    while i < n:
        try:
            key, i = read_varint(buf, i)
        except IndexError:
            break
        field, wt = key >> 3, key & 7
        if wt == 0:
            val, i = read_varint(buf, i)
        elif wt == 2:
            ln, i = read_varint(buf, i)
            raw = buf[i:i + ln]
            i += ln
            try:
                val = raw.decode("utf-8")
                if any(ord(c) < 9 for c in val):
                    val = raw.hex()
            except UnicodeDecodeError:
                val = raw.hex()
        elif wt == 5:
            val, i = int.from_bytes(buf[i:i + 4], "little"), i + 4
        elif wt == 1:
            val, i = int.from_bytes(buf[i:i + 8], "little"), i + 8
        else:
            break
        out.setdefault(field, []).append(val)
    return out


def parse_sh(fp):
    shebang, purpose, cmds = None, None, set()
    COMMON = {"if", "then", "fi", "for", "do", "done", "else", "elif", "case",
              "esac", "echo", "exit", "set", "local", "return", "true", "false"}
    for idx, line in enumerate(open(fp, errors="replace")):
        s = line.rstrip("\n")
        if idx == 0 and s.startswith("#!"):
            shebang = s[2:].strip()
        elif purpose is None and s.strip().startswith("#") and len(s.strip()) > 3:
            purpose = s.strip("# ").strip()
        tok = s.strip().split()
        if tok and not tok[0].startswith("#"):
            w = tok[0]
            if w.isalpha() and w not in COMMON and len(w) > 1:
                cmds.add(w)
    return {"shebang": shebang, "purpose": purpose, "commands": sorted(cmds)[:25]}


def main():
    root, out = sys.argv[1], sys.argv[2]
    entries = []
    for part in sorted(os.listdir(root)):
        pdir = os.path.join(root, part)
        if not os.path.isdir(pdir):
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                fp = os.path.join(dp, fn)
                if os.path.islink(fp):
                    continue
                rel = "/" + os.path.relpath(fp, pdir)
                is_sh = fn.endswith(".sh")
                if not is_sh:
                    try:
                        with open(fp, "rb") as fh:
                            is_sh = fh.read(2) == b"#!"
                    except OSError:
                        is_sh = False
                if is_sh:
                    e = {"partition": part, "path": rel, "kind": "shell_script"}
                    e.update(parse_sh(fp))
                    entries.append(e)
                elif fn == "modules.dep":
                    graph = {}
                    for line in open(fp, errors="replace"):
                        if ":" in line:
                            mod, deps = line.split(":", 1)
                            graph[os.path.basename(mod.strip())] = [
                                os.path.basename(d) for d in deps.split()]
                        entries_mod = graph
                    entries.append({"partition": part, "path": rel, "kind": "kernel_modules_dep",
                                    "module_count": len(graph), "graph": graph})
                elif fn == "apex_manifest.pb":
                    raw = open(fp, "rb").read()
                    d = decode_protobuf(raw)
                    entries.append({"partition": part, "path": rel, "kind": "apex_manifest",
                                    "apex_name": (d.get(1) or [None])[0],
                                    "version": (d.get(2) or [None])[0],
                                    "raw_fields": {str(k): v for k, v in d.items()}})
    report = {"root": root, "count": len(entries),
              "scripts": [e for e in entries if e["kind"] == "shell_script"],
              "apex_manifests": [e for e in entries if e["kind"] == "apex_manifest"],
              "kernel_modules": [e for e in entries if e["kind"] == "kernel_modules_dep"]}
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(report['scripts'])} shell scripts, {len(report['apex_manifests'])} apex manifests")
    for a in report["apex_manifests"][:6]:
        print(f"  APEX {a['apex_name']} v{a['version']}")


if __name__ == "__main__":
    main()
