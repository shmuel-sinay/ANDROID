#!/usr/bin/env python3
"""Find which packages fill the roles Android 11 needs while booting.

Usage: boot_roles.py apks.json init_graph.json > boot_roles.json

Each role says what happens (by reading the AOSP 11 boot code path) when
no package fills it:
  "bootloop"  - system_server throws during start -> restarts forever
  "degraded"  - boots, but a feature or the UI is missing
The "basis" field names the AOSP code path the verdict relies on, and
"confidence" marks verdicts that still need a check against real logs.
"""
import json
import sys


def matches(f, action=None, category=None, scheme=None, mime=None, component=None):
    if component and f["component"] != component:
        return False
    if action and action not in f["actions"]:
        return False
    if category and category not in f["categories"]:
        return False
    if scheme and scheme not in f["schemes"]:
        return False
    if mime and mime not in f["mimes"]:
        return False
    return True


ROLES = [
    {"role": "installer", "if_missing": "bootloop", "confidence": "high",
     "basis": "PackageManagerService.getRequiredInstallerLPr(): 'There must be exactly one installer'",
     "find": dict(component="activity", action="android.intent.action.INSTALL_PACKAGE",
                  scheme="content", mime="application/vnd.android.package-archive")},
    {"role": "uninstaller", "if_missing": "bootloop", "confidence": "high",
     "basis": "PackageManagerService.getRequiredUninstallerLPr(): 'There must be exactly one uninstaller'",
     "find": dict(component="activity", action="android.intent.action.DELETE", scheme="package")},
    {"role": "permission_controller", "if_missing": "bootloop", "confidence": "high",
     "basis": "PackageManagerService.getRequiredPermissionControllerLPr(): 'There must be exactly one permission controller'",
     "find": dict(component="activity", action="android.intent.action.MANAGE_PERMISSIONS")},
    {"role": "shared_library android.ext.shared", "if_missing": "bootloop", "confidence": "high",
     "basis": "PackageManagerService.getRequiredSharedLibraryLPr(): 'Missing required shared library'",
     "library": "android.ext.shared"},
    {"role": "services_extension (ExtServices)", "if_missing": "bootloop", "confidence": "medium",
     "basis": "PackageManagerService.getRequiredServicesExtensionPackageLPr()",
     "package": "android.ext.services"},
    {"role": "settings_provider", "if_missing": "bootloop", "confidence": "high",
     "basis": "ActivityManagerService.installSystemProviders(): Settings.* reads fail in system_server",
     "provider": "settings"},
    {"role": "framework (android)", "if_missing": "bootloop", "confidence": "high",
     "basis": "framework-res.apk is package 'android' - resources of system_server",
     "package": "android"},
    {"role": "package_verifier", "if_missing": "degraded", "confidence": "high",
     "basis": "getRequiredButNotReallyRequiredVerifierLPr() returns null",
     "find": dict(component="receiver", action="android.intent.action.PACKAGE_NEEDS_VERIFICATION")},
    {"role": "home / launcher", "if_missing": "degraded", "confidence": "high",
     "basis": "ActivityTaskManager.startHomeActivity(): no HOME -> black screen after boot animation",
     "find": dict(component="activity", action="android.intent.action.MAIN",
                  category="android.intent.category.HOME")},
    {"role": "system_ui", "if_missing": "degraded", "confidence": "medium",
     "basis": "SystemServer.startSystemUi(): no status bar / navigation / lock screen",
     "package": "com.android.systemui"},
    {"role": "setup_wizard", "if_missing": "degraded", "confidence": "high",
     "basis": "getSetupWizardPackageNameImpl() returns null; device may stay 'not provisioned'",
     "find": dict(component="activity", action="android.intent.action.MAIN",
                  category="android.intent.category.SETUP_WIZARD")},
    {"role": "telephony (com.android.phone)", "if_missing": "degraded", "confidence": "high",
     "basis": "persistent app; without it there is no calling/SMS",
     "package": "com.android.phone"},
]


def main():
    apks = json.load(open(sys.argv[1]))["apks"]
    init = json.load(open(sys.argv[2]))
    out = []
    for r in ROLES:
        found = []
        for a in apks:
            if "find" in r:
                if any(matches(f, **r["find"]) for f in a.get("intent_filters", [])):
                    found.append(a)
            elif "library" in r:
                if r["library"] in a.get("libraries_declared", []):
                    found.append(a)
            elif "provider" in r:
                if any(r["provider"] in (p or "").split(";") for p in a.get("providers", [])):
                    found.append(a)
            elif "package" in r:
                if a.get("package") == r["package"]:
                    found.append(a)
        pkgs = sorted({a["package"] for a in found})
        out.append({k: r[k] for k in ("role", "if_missing", "confidence", "basis")} | {
            "filled_by": pkgs,
            "paths": sorted(a["path"] for a in found),
            "status": "ok" if pkgs else "MISSING",
            "note": ("more than one package: PMS demands exactly one" if len(pkgs) > 1
                     and r["role"] in ("installer", "uninstaller", "permission_controller")
                     else None),
        })

    critical = sorted(n for n, s in init["services"].items()
                      if any(f.startswith("critical") for f in s["flags"]))
    print(json.dumps({
        "roles": out,
        "critical_init_services": critical,
        "critical_note": "init reboots into bootloader/recovery if a critical service "
                         "crashes more than 4 times in 4 minutes",
        "persistent_apps": sorted({a["package"] for a in apks if a.get("persistent")}),
        "persistent_note": "repeated crashes of persistent apps trigger RescueParty, "
                           "which ends in the 'Can't load Android system' recovery prompt",
    }, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
