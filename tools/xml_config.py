#!/usr/bin/env python3
"""Index and parse the XML configuration files of an extracted ROM.

Every XML is classified by its root tag. For the kinds that express a
dependency or a system contract, the real content is pulled out:

  manifest / compatibility-matrix (VINTF) -> HALs provided vs required
  permissions / sysconfig (framework)      -> features, libraries, privapp
  media_codecs                             -> declared codecs
  audio_policy_configuration               -> modules / devices

Everything else is indexed (root tag + size) so it is accounted for.

Usage: xml_config.py ROM_FS_DIR OUT.json
"""
import json
import os
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_vintf_manifest(root):
    hals = []
    for hal in root.findall("hal"):
        name = (hal.findtext("name") or "").strip()
        fmt = hal.get("format", "")
        optional = hal.get("optional", "false") == "true"
        _ = optional  # recorded per-entry below
        for intf in hal.findall("interface"):
            iname = (intf.findtext("name") or "").strip()
            insts = [i.text.strip() for i in intf.findall("instance") if i.text]
            for ver in hal.findall("version"):
                hals.append({"name": name, "format": fmt, "interface": iname,
                             "version": (ver.text or "").strip(), "instances": insts, "optional": optional})
        if not hal.findall("interface"):
            for ver in hal.findall("version"):
                hals.append({"name": name, "format": fmt, "version": (ver.text or "").strip(), "optional": optional})
        for fqn in hal.findall("fqname"):
            hals.append({"name": name, "format": fmt, "fqname": (fqn.text or "").strip(), "optional": optional})
    return hals


def parse_permissions(root):
    out = {"features": [], "libraries": [], "privapp": [], "allow": []}
    for el in root:
        t = local(el.tag)
        if t == "feature":
            out["features"].append(el.get("name"))
        elif t == "library":
            out["libraries"].append({"name": el.get("name"), "file": el.get("file")})
        elif t == "privapp-permissions":
            out["privapp"].append(el.get("package"))
        elif t.startswith("allow"):
            out["allow"].append({t: el.get("package") or el.get("name")})
    return out


def main():
    root_dir, out = sys.argv[1], sys.argv[2]
    index, roots = [], {}
    provided_hals, required_hals = [], []
    for part in sorted(os.listdir(root_dir)):
        pdir = os.path.join(root_dir, part)
        if not os.path.isdir(pdir):
            continue
        for dp, _dn, fns in os.walk(pdir):
            for fn in fns:
                if not fn.endswith(".xml"):
                    continue
                fp = os.path.join(dp, fn)
                if os.path.islink(fp):
                    continue
                rel = "/" + os.path.relpath(fp, pdir)
                entry = {"partition": part, "path": rel, "size": os.path.getsize(fp)}
                try:
                    r = ET.parse(fp).getroot()
                except ET.ParseError as ex:
                    entry["root"] = "(parse-error)"
                    entry["error"] = str(ex)
                    index.append(entry)
                    continue
                tag = local(r.tag)
                entry["root"] = tag
                roots[tag] = roots.get(tag, 0) + 1
                if tag == "manifest":
                    hals = parse_vintf_manifest(r)
                    entry["hal_count"] = len(hals)
                    entry["type"] = r.get("type")  # "device" (provides) / "framework"
                    for h in hals:
                        provided_hals.append({**h, "from": f"{part}:{rel}"})
                elif tag == "compatibility-matrix":
                    hals = parse_vintf_manifest(r)
                    entry["required_hal_count"] = len(hals)
                    for h in hals:
                        opt = "optional=true"  # matrix entries mark optional on <hal>
                        required_hals.append({**h, "from": f"{part}:{rel}"})
                elif tag == "permissions":
                    entry["permissions"] = parse_permissions(r)
                elif tag == "MediaCodecs":
                    entry["codecs"] = [c.get("name") for c in r.iter("MediaCodec")]
                elif tag == "audioPolicyConfiguration":
                    entry["modules"] = [m.get("name") for m in r.iter("module")]
                index.append(entry)

    # which required HALs are not provided anywhere (framework needs, vendor lacks)
    prov_names = {(h.get("name"), h.get("interface")) for h in provided_hals}
    prov_simple = {h.get("name") for h in provided_hals}
    unmet = [h for h in required_hals
             if not h.get("optional") and h.get("name") not in prov_simple]

    report = {
        "root_dir": root_dir, "total_xml": len(index),
        "root_tags": dict(sorted(roots.items(), key=lambda kv: -kv[1])),
        "vintf_provided_hals": len(provided_hals),
        "vintf_required_hals": len(required_hals),
        "required_hals_not_obviously_provided": unmet,
        "hals_provided": provided_hals,
        "files": index,
    }
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(index)} XML files")
    print(f"VINTF: {len(provided_hals)} HALs provided, {len(required_hals)} required, "
          f"{len(unmet)} required but not obviously provided")
    parse_errors = sum(1 for e in index if e["root"] == "(parse-error)")
    print(f"parse errors: {parse_errors}")


if __name__ == "__main__":
    main()
