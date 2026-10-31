#!/usr/bin/env python3
"""Inventory every APK of an extracted ROM and check priv-app allowlists.

Usage: apk_inventory.py LABEL=DIR [LABEL=DIR ...] > apks.json
Needs `aapt` (apt package "aapt").

For each APK: package, location, priv-app?, sharedUserId, persistent,
coreApp, requested permissions, uses-library, providers, HOME/launcher,
plus the privileged permissions it requests that are NOT allowlisted in
privapp-permissions XML (on Android 11 "enforce" mode that blocks boot).
"""
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ATTR_RE = re.compile(r'A: (?:[\w]+:)?([\w]+)(?:\(0x[0-9a-f]+\))?=(?:"([^"]*)"|\(type 0x[0-9a-f]+\)(0x[0-9a-f]+)|(\S+))')
ELEM_RE = re.compile(r"E: ([\w\-:.]+)")


def xmltree(apk):
    """Return the manifest as nested dicts: {tag, attrs, children}."""
    try:
        out = subprocess.run(["aapt", "dump", "xmltree", apk, "AndroidManifest.xml"],
                             capture_output=True, text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        return None
    root, stack = None, []
    for line in out.splitlines():
        depth = (len(line) - len(line.lstrip())) // 2
        s = line.strip()
        m = ELEM_RE.match(s)
        if m:
            node = {"tag": m.group(1), "attrs": {}, "children": []}
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(node)
            else:
                root = node
            stack.append((depth, node))
            continue
        m = ATTR_RE.match(s)
        if m and stack:
            val = m.group(2) if m.group(2) is not None else (m.group(3) or m.group(4))
            stack[-1][1]["attrs"][m.group(1)] = val
    return root


def walk(node, tag):
    if node is None:
        return
    if node["tag"] == tag:
        yield node
    for c in node["children"]:
        yield from walk(c, tag)


COMPONENTS = ("activity", "activity-alias", "service", "receiver", "provider")


def intent_filters(app):
    """List of {component, name, actions, categories, schemes, mimes}."""
    out = []
    for comp in app.get("children", []):
        if comp["tag"] not in COMPONENTS:
            continue
        for f in comp["children"]:
            if f["tag"] != "intent-filter":
                continue
            kids = f["children"]
            out.append({
                "component": comp["tag"],
                "name": comp["attrs"].get("name"),
                "enabled": comp["attrs"].get("enabled") not in ("false", "0x0"),
                "permission": comp["attrs"].get("permission"),
                "actions": [k["attrs"].get("name") for k in kids if k["tag"] == "action"],
                "categories": [k["attrs"].get("name") for k in kids if k["tag"] == "category"],
                "schemes": [k["attrs"].get("scheme") for k in kids
                            if k["tag"] == "data" and k["attrs"].get("scheme")],
                "mimes": [k["attrs"].get("mimeType") for k in kids
                          if k["tag"] == "data" and k["attrs"].get("mimeType")],
            })
    return out


def truthy(v):
    return v in ("true", "0xffffffff", "-1")


def load_allowlists(dirs):
    allow = {}
    for d in dirs:
        for dp, _dn, files in os.walk(d):
            if not dp.endswith("etc/permissions") and "/etc/permissions" not in dp:
                continue
            for f in files:
                if not f.endswith(".xml"):
                    continue
                try:
                    tree = ET.parse(os.path.join(dp, f))
                except ET.ParseError:
                    continue
                for pa in tree.getroot().iter("privapp-permissions"):
                    pkg = pa.get("package")
                    entry = allow.setdefault(pkg, {"grant": set(), "deny": set(), "files": set()})
                    entry["files"].add(f)
                    for p in pa.iter("permission"):
                        entry["grant"].add(p.get("name"))
                    for p in pa.iter("deny-permission"):
                        entry["deny"].add(p.get("name"))
    return allow


def privileged_permissions(framework_res):
    """Permission names whose protectionLevel includes 'privileged' (0x10)."""
    priv = set()
    tree = xmltree(framework_res)
    for p in walk(tree, "permission"):
        lvl = p["attrs"].get("protectionLevel")
        try:
            if lvl and int(lvl, 16) & 0x10:
                priv.add(p["attrs"].get("name"))
        except ValueError:
            pass
    return priv


def main():
    roots = [a.split("=", 1) for a in sys.argv[1:]]
    apks = []
    for label, d in roots:
        for dp, _dn, files in os.walk(d):
            for f in files:
                if f.endswith(".apk"):
                    apks.append((label, d, os.path.join(dp, f)))

    fw = next((p for _l, _d, p in apks if p.endswith("framework/framework-res.apk")), None)
    priv_perms = privileged_permissions(fw) if fw else set()
    allow = load_allowlists([d for _l, d in roots])

    result = []
    for label, d, path in sorted(apks, key=lambda x: x[2]):
        rel = "/" + os.path.relpath(path, d)
        t = xmltree(path)
        if t is None:
            result.append({"path": f"{label}:{rel}", "error": "unreadable"})
            continue
        a = t["attrs"]
        app = next(walk(t, "application"), {"attrs": {}})
        perms = sorted({p["attrs"].get("name") for p in walk(t, "uses-permission")} - {None})
        is_priv = "/priv-app/" in rel
        home = any(
            any(c["tag"] == "category" and c["attrs"].get("name") == "android.intent.category.HOME"
                for c in f["children"])
            for f in walk(t, "intent-filter"))
        entry = {
            "path": f"{label}:{rel}",
            "package": a.get("package"),
            "version": a.get("versionName"),
            "priv_app": is_priv,
            "overlay": next(walk(t, "overlay"), None) is not None,
            "sharedUserId": a.get("sharedUserId"),
            "coreApp": truthy(a.get("coreApp", "")),
            "persistent": truthy(app["attrs"].get("persistent", "")),
            "has_code": app["attrs"].get("hasCode") not in ("false", "0x0"),
            "home_activity": home,
            "uses_library": sorted({(u["attrs"].get("name"), not (u["attrs"].get("required") in ("false", "0x0")))
                                    for u in walk(t, "uses-library")} - {(None, True), (None, False)}),
            "providers": sorted({p["attrs"].get("authorities") for p in walk(t, "provider")} - {None}),
            "permissions_requested": perms,
            "libraries_declared": sorted({x["attrs"].get("name") for x in walk(t, "library")} - {None}),
            "intent_filters": intent_filters(app),
        }
        if is_priv:
            al = allow.get(entry["package"], {"grant": set(), "deny": set()})
            needed = [p for p in perms if p in priv_perms]
            entry["privileged_perms_needed"] = needed
            entry["privileged_perms_not_allowlisted"] = [
                p for p in needed if p not in al["grant"] and p not in al["deny"]]
        result.append(entry)

    print(json.dumps({"privileged_permission_count": len(priv_perms),
                      "allowlisted_packages": sorted(k for k in allow if k),
                      "apks": result}, indent=1, ensure_ascii=False, default=list))


if __name__ == "__main__":
    main()
