#!/usr/bin/env python3
"""Deep UI analysis: map every Settings row and every status-bar icon slot
to the key/resource that controls it, so a specific row or icon can be
located and removed.

Two parts:
  settings  -> parse Settings' res/xml/*.xml PreferenceScreens: every
               Preference with its key, title, fragment/intent, and the
               `dependency` / `settingsKey` that gates it.
  statusbar -> framework config_statusBarIcons slot order + the SystemUI
               drawable and knob for each slot where resolvable.

Usage: ui_deep.py OUT.json SETTINGS.apk SYSTEMUI.apk FRAMEWORK-RES.apk
Needs: aapt (for resource ids) and unzip (for res/xml binaries).
Because res/xml is compiled (binary XML), we use `aapt dump xmltree`.
"""
import json
import re
import subprocess
import sys
import zipfile


def xmltree_of(apk, entry):
    try:
        return subprocess.run(["aapt", "dump", "xmltree", apk, entry],
                              capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    except (subprocess.TimeoutExpired, OSError):
        return ""


ATTR = re.compile(r'A: (?:[\w.]+:)?(\w+)\([^)]*\)=(?:"([^"]*)"|\(type [^)]*\)(\S+))')
ELEM = re.compile(r"E: ([\w.]+)")


def parse_prefs(apk, entry):
    """Return the list of preference rows declared in one res/xml file."""
    out = []
    txt = xmltree_of(apk, entry)
    cur = None
    for line in txt.splitlines():
        s = line.strip()
        me = ELEM.match(s)
        if me:
            tag = me.group(1)
            if "Preference" in tag or tag.endswith("Fragment") or tag == "intent":
                cur = {"type": tag, "file": entry}
                out.append(cur)
            else:
                cur = None
            continue
        ma = ATTR.match(s)
        if ma and cur is not None:
            name = ma.group(1)
            val = ma.group(2) if ma.group(2) is not None else ma.group(3)
            if name in ("key", "title", "summary", "fragment", "targetClass",
                        "targetPackage", "dependency", "action", "persistent",
                        "controller", "settingsKey", "defaultValue"):
                cur[name] = val
    return [p for p in out if p.get("key") or p.get("title") or p.get("fragment")]


def settings_rows(apk):
    rows = []
    with zipfile.ZipFile(apk) as z:
        xmls = [n for n in z.namelist() if n.startswith("res/xml/") and n.endswith(".xml")]
    for entry in sorted(xmls):
        for p in parse_prefs(apk, entry):
            rows.append(p)
    return rows


def status_bar(sysui, framework):
    # slot order from framework config_statusBarIcons
    slots = []
    txt = subprocess.run(["aapt", "dump", "--values", "resources", framework],
                         capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
    grab = False
    for line in txt.splitlines():
        s = line.strip()
        if "array/config_statusBarIcons:" in s and "spec" not in s:
            grab = True
            continue
        if grab:
            m = re.search(r'\(string8\) "([^"]+)"', s)
            if m:
                slots.append(m.group(1))
            elif s.startswith("resource ") or s.startswith("spec "):
                grab = False
    # SystemUI knobs that mention the status bar
    sui_txt = subprocess.run(["aapt", "dump", "--values", "resources", sysui],
                             capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
    knobs = {}
    pend = None
    for line in sui_txt.splitlines():
        s = line.strip()
        m = re.match(r"resource 0x[0-9a-f]+ [^:]+:(bool|integer)/(\S+?): ", s)
        if m and any(w in m.group(2).lower() for w in ("statusbar", "status_bar", "icon", "battery", "clock")):
            pend = m.group(2)
            continue
        m2 = re.match(r"\((boolean|integer)\)\s*(.*)", s)
        if m2 and pend:
            knobs[pend] = m2.group(2).strip()
            pend = None
    return {"slot_order": slots, "systemui_statusbar_knobs": knobs}


def main():
    out, settings_apk, sysui_apk, fw_apk = sys.argv[1:5]
    rows = settings_rows(settings_apk)
    sb = status_bar(sysui_apk, fw_apk)
    report = {
        "settings": {"apk": settings_apk, "row_count": len(rows), "rows": rows},
        "status_bar": sb,
    }
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"settings rows: {len(rows)} | status-bar slots: {len(sb['slot_order'])} "
          f"| status-bar knobs: {len(sb['systemui_statusbar_knobs'])}")


if __name__ == "__main__":
    main()
