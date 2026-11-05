#!/usr/bin/env python3
"""Build a per-component "removal recipe" for a ROM.

For each package the ROM can remove, gather EVERYTHING another AI (or a
human) needs to delete it without bricking boot:
  - the roles it fills (from boot_roles.json) and the bootloop risk
  - the boot guards in code that name it or its role (from boot_guards.json)
  - its native dependents and dependencies (from native_deps.json)
  - which other packages share its sharedUserId (from apks.json)
  - a neutralization plan per guard, with a confidence level

Output is one JSON file keyed by package, plus a flat list, designed to be
uploaded to an assistant and queried ("how do I remove X safely?").

Usage: removal_recipe.py ROM_DIR OUT.json
"""
import json
import os
import re
import sys


def load(d, name, default=None):
    p = os.path.join(d, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


# How to neutralize each kind of boot guard. Keyed by a signature found in the
# guard's message or method name. Each entry: (human action, confidence).
NEUTRALIZE = [
    (re.compile(r"exactly one installer", re.I),
     "ב-services.jar: לגרום ל-getRequiredInstallerLPr להחזיר null במקום לזרוק. "
     "למחוק services.odex/vdex/art. מאבדים התקנת APK מהמכשיר; adb install עובד.", "high"),
    (re.compile(r"exactly one uninstaller", re.I),
     "ב-services.jar: getRequiredUninstallerLPr יחזיר null. מאבדים מסך הסרה; pm uninstall עובד.", "high"),
    (re.compile(r"permissions? manager|MANAGE_PERMISSIONS", re.I),
     "אין לנטרל בבטחה: PermissionController מנהל את כל ההרשאות. לא למחוק.", "do-not-remove"),
    (re.compile(r"services extension|servicesExtensionPackage", re.I),
     "להשאיר config_servicesExtensionPackage מצביע לחבילה קיימת, או לרוקן אותו ב-overlay. סיכון גבוה.", "low"),
    (re.compile(r"shared library|getRequiredSharedLibrary", re.I),
     "ספריית android.ext.shared נדרשת ע\"י PMS. לא למחוק; אפשר רק להחליף במימוש ריק חתום.", "do-not-remove"),
    (re.compile(r"settings|SettingsProvider", re.I),
     "ספק settings נקרא ע\"י כל שירות. לא למחוק.", "do-not-remove"),
    (re.compile(r"exactly one verifier|PACKAGE_NEEDS_VERIFICATION", re.I),
     "ה-verifier אופציונלי (getRequiredButNotReallyRequired). מחיקה בטוחה.", "high"),
]


def neutralize_for(guard):
    text = " ".join(guard.get("messages", [])) + " " + guard["method"]
    for rx, action, conf in NEUTRALIZE:
        if rx.search(text):
            return action, conf
    return "לא נמצא מרשם נטרול אוטומטי — דורש בדיקה ידנית של הקוד.", "unknown"


def main():
    rom, out = sys.argv[1], sys.argv[2]
    apks = load(rom, "apks.json", {"apks": []})["apks"]
    roles = load(rom, "boot_roles.json", {"roles": []})
    guards = load(rom, "boot_guards.json", {"guards": []})
    nat = load(rom, "native_deps.json", {"needed_by": {}, "libs": {}})

    by_pkg = {}
    for a in apks:
        if a.get("package"):
            by_pkg.setdefault(a["package"], []).append(a)

    # roles indexed by the packages that fill them
    role_of = {}
    for r in roles["roles"]:
        for p in r["filled_by"]:
            role_of.setdefault(p, []).append(r)

    onboot_guards = [g for g in guards.get("guards", []) if g.get("boot_path")]

    recipes = {}
    for pkg, entries in sorted(by_pkg.items()):
        paths = [e["path"] for e in entries]
        pkg_roles = role_of.get(pkg, [])
        # guards whose message or method mentions this package or one of its roles
        hit_guards = []
        role_words = " ".join(r["role"] for r in pkg_roles)
        for g in onboot_guards:
            blob = " ".join(g.get("messages", [])) + " " + g["method"]
            if pkg in blob or any(rw.split()[0] in blob for rw in role_words.split("(") if rw.strip()):
                action, conf = neutralize_for(g)
                hit_guards.append({"method": g["method"].split("(")[0],
                                   "message": g["messages"][0][:100],
                                   "distance_from_boot": len(g["boot_path"]),
                                   "neutralize": action, "confidence": conf})

        bootloop = [r for r in pkg_roles if r["if_missing"] == "bootloop"]
        degraded = [r for r in pkg_roles if r["if_missing"] == "degraded"]
        shared = sorted({a["sharedUserId"] for a in entries if a.get("sharedUserId")})
        co_shared = sorted({o["package"] for o in apks
                            if o.get("sharedUserId") and o["sharedUserId"] in shared
                            and o["package"] != pkg}) if shared else []

        if bootloop:
            verdict, risk = "לא למחוק ללא נטרול", "bootloop"
        elif hit_guards and any(g["confidence"] == "do-not-remove" for g in hit_guards):
            verdict, risk = "לא למחוק", "critical"
        elif degraded:
            verdict, risk = "מחיקה אפשרית — תאבד פונקציה", "degraded"
        else:
            verdict, risk = "כנראה בטוח למחיקה", "safe"

        recipes[pkg] = {
            "package": pkg, "paths": paths, "priv_app": entries[0].get("priv_app"),
            "persistent": any(e.get("persistent") for e in entries),
            "risk": risk, "verdict": verdict,
            "roles_filled": [{"role": r["role"], "if_missing": r["if_missing"],
                              "basis": r["basis"]} for r in pkg_roles],
            "boot_guards": hit_guards,
            "sharedUserId": shared, "shares_uid_with": co_shared,
            "notes": ("משתף uid עם חבילות אחרות — מחיקה עלולה לשבור אותן." if co_shared else None),
        }

    summary = {
        "by_risk": {k: sorted(p for p, r in recipes.items() if r["risk"] == k)
                    for k in ("bootloop", "critical", "degraded", "safe")},
    }
    json.dump({"generated_for": rom,
               "how_to_use": "לכל חבילה: roles_filled = מה היא נותנת; boot_guards = מה יקרוס "
                             "ואיך לנטרל; shares_uid_with = מה עוד עלול להישבר; verdict = שורה תחתונה.",
               "summary": summary, "recipes": recipes},
              open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(recipes)} packages")
    for k in ("bootloop", "critical", "degraded", "safe"):
        print(f"  {k}: {len(summary['by_risk'][k])}")


if __name__ == "__main__":
    main()
