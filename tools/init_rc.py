#!/usr/bin/env python3
"""Parse Android init .rc files into a JSON graph.

Usage: init_rc.py ROOT_LABEL=DIR [ROOT_LABEL=DIR ...] > init_graph.json

Each DIR is scanned recursively for *.rc. Paths in the output are given as
"<label>:<path inside DIR>" so files from several partitions can be mixed.

Output:
  services: name -> {file, exec, args, class, user, group, flags, ...}
  actions:  list of {trigger, file, commands}
  imports:  list of {file, path}
"""
import json
import os
import re
import sys

SERVICE_FLAGS = {"disabled", "oneshot", "critical", "core", "restart_period",
                 "updatable", "override", "seclabel"}


def logical_lines(text):
    buf = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        line = (buf + line).strip()
        buf = ""
        if line and not line.startswith("#"):
            yield line


def parse_file(label, root, path, result):
    rel = f"{label}:{os.path.relpath(path, root)}"
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return
    section = None
    for line in logical_lines(text):
        parts = line.split()
        kw = parts[0]
        if kw == "service" and len(parts) >= 3:
            name = parts[1]
            section = {"file": rel, "exec": parts[2], "args": parts[3:],
                       "classes": [], "user": None, "groups": [], "flags": [],
                       "capabilities": [], "sockets": [], "onrestart": [],
                       "interface": [], "writepid": [], "other": []}
            if name in result["services"]:
                section["overrides"] = result["services"][name]["file"]
            result["services"][name] = section
            section = ("service", section)
        elif kw == "on":
            act = {"trigger": " ".join(parts[1:]), "file": rel, "commands": []}
            result["actions"].append(act)
            section = ("action", act)
        elif kw == "import":
            result["imports"].append({"file": rel, "path": " ".join(parts[1:])})
            section = None
        elif section and section[0] == "action":
            section[1]["commands"].append(line)
        elif section and section[0] == "service":
            s = section[1]
            if kw == "class":
                s["classes"] += parts[1:]
            elif kw == "user":
                s["user"] = parts[1] if len(parts) > 1 else None
            elif kw == "group":
                s["groups"] += parts[1:]
            elif kw == "capabilities":
                s["capabilities"] += parts[1:]
            elif kw == "socket":
                s["sockets"].append(" ".join(parts[1:]))
            elif kw == "onrestart":
                s["onrestart"].append(" ".join(parts[1:]))
            elif kw == "interface":
                s["interface"].append(" ".join(parts[1:]))
            elif kw == "writepid":
                s["writepid"] += parts[1:]
            elif kw in SERVICE_FLAGS:
                s["flags"].append(" ".join(parts))
            else:
                s["other"].append(line)


# property names used in triggers and setprop/property commands
PROP_RE = re.compile(r"property:([\w.\-]+)=")


def summarize(result):
    sets, reads = {}, {}
    for a in result["actions"]:
        for p in PROP_RE.findall(a["trigger"]):
            reads.setdefault(p, []).append(a["trigger"])
        for c in a["commands"]:
            parts = c.split()
            if parts[0] == "setprop" and len(parts) >= 2:
                sets.setdefault(parts[1], []).append(a["file"])
    # which actions start / stop which services
    starts = {}
    for a in result["actions"]:
        for c in a["commands"]:
            parts = c.split()
            if parts[0] in ("start", "restart", "stop", "enable") and len(parts) > 1:
                starts.setdefault(parts[1], []).append(
                    {"by": a["trigger"], "verb": parts[0], "file": a["file"]})
            if parts[0] in ("class_start", "class_stop", "class_reset",
                            "class_restart") and len(parts) > 1:
                starts.setdefault("class:" + parts[1], []).append(
                    {"by": a["trigger"], "verb": parts[0], "file": a["file"]})
    result["property_triggers"] = reads
    result["property_setters"] = sets
    result["service_control"] = starts
    return result


def main():
    result = {"services": {}, "actions": [], "imports": []}
    for arg in sys.argv[1:]:
        label, root = arg.split("=", 1)
        for dp, _dn, files in os.walk(root):
            for f in sorted(files):
                if f.endswith(".rc"):
                    p = os.path.join(dp, f)
                    if os.path.isfile(p) and not os.path.islink(p):
                        parse_file(label, root, p, result)
    print(json.dumps(summarize(result), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
