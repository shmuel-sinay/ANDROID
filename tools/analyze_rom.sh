#!/usr/bin/env bash
# Run the full analysis pipeline on one extracted ROM.
#
# Usage: analyze_rom.sh <ROM_WORKDIR> <slug> [scatter_path]
#   ROM_WORKDIR : holds fs/{system,vendor,product}, boot/rd, super/, and the
#                 raw partition images (boot.img, vbmeta*.img, dtbo.img ...).
#   slug        : output name, e.g. "f22-a13-restore" -> roms/<slug>/ and site.
#
# Produces every JSON dataset in $REPO/roms/<slug>/, the summaries the site
# reads, and the static site at $REPO/docs/site/<slug>/. Idempotent.
set -uo pipefail
T=/home/user/android/tools
REPO=/home/user/android
W="$1"; SLUG="$2"; SC="${3:-}"
G="$REPO/roms/$SLUG"; mkdir -p "$G/deps"
cd "$W" || { echo "no workdir $W"; exit 1; }

echo "[1/12] metadata"
[ -n "$SC" ] && cp "$SC" "$G/" 2>/dev/null
cp super/lp_metadata.json "$G/" 2>/dev/null
for p in system vendor product; do
  debugfs -R "cat /$([ $p = system ] && echo system/)build.prop" super/${p}_a.img 2>/dev/null > "$G/$p.build.prop"
done
debugfs -R "cat /product/etc/build.prop" super/product_a.img 2>/dev/null >> "$G/product.build.prop"

echo "[2/12] APEX extract"
python3 "$T/apex_unpack.py" fs > "$G/apex_extracted.json" 2>/dev/null

echo "[3/12] AVB"
imgs=""; for f in boot.img dtbo.img vbmeta.img vbmeta_system*.img vbmeta_vendor*.img; do [ -f "$f" ] && imgs="$imgs $f"; done
python3 "$T/avb_info.py" $imgs super/system_a.img super/vendor_a.img super/product_a.img > "$G/avb.json" 2>/dev/null

echo "[4/12] init graph"
python3 "$T/init_rc.py" ramdisk=boot/rd system=fs/system vendor=fs/vendor product=fs/product > "$G/init_graph.json" 2>/dev/null

echo "[5/12] APK inventory (incl APEX)"
APEXARG=""; [ -d fs/apex_extracted ] && APEXARG="apex=fs/apex_extracted"
python3 "$T/apk_inventory.py" system=fs/system vendor=fs/vendor product=fs/product $APEXARG > "$G/apks.json" 2>/dev/null

echo "[6/12] boot roles"
python3 "$T/boot_roles.py" "$G/apks.json" "$G/init_graph.json" > "$G/boot_roles.json" 2>/dev/null

echo "[7/12] boot guards"
( cd fs/system/system/framework 2>/dev/null && \
  python3 "$T/boot_guards.py" "$G/boot_guards.json" \
    services.jar mediatek-services.jar framework.jar mediatek-framework.jar 2>/dev/null ) || echo '{"guards":[]}' > "$G/boot_guards.json"

echo "[8/12] native deps / xml / selinux / misc"
python3 "$T/native_deps.py" fs "$G/native_deps.json" 2>/dev/null
python3 "$T/xml_config.py"  fs "$G/xml_config.json"  2>/dev/null
python3 "$T/selinux.py"     fs "$G/selinux.json"     2>/dev/null
python3 "$T/misc_files.py"  fs "$G/misc_files.json"  2>/dev/null

echo "[9/12] deep resources (per-app knobs)"
python3 "$T/resources.py" "$G/resources.json" --walk fs 2>/dev/null

echo "[10/12] coverage"
python3 "$T/coverage.py" fs "$G/coverage.json" --hash 2>/dev/null

echo "[11/12] removal recipes"
( cd "$G" && python3 "$T/removal_recipe.py" . removal_recipes.json 2>/dev/null )

echo "[12/12] summaries + site"
python3 - "$G" <<'PY'
import json, os, sys
G = sys.argv[1]
def trim(src, dst, drop):
    if not os.path.exists(os.path.join(G, src)): return
    d = json.load(open(os.path.join(G, src), encoding="utf-8"))
    for k in drop: d.pop(k, None)
    json.dump(d, open(os.path.join(G, dst), "w"), indent=1, ensure_ascii=False)
trim("coverage.json", "coverage.summary.json", ["files"])
trim("native_deps.json", "native_deps.summary.json", ["libs", "needed_by"])
if os.path.exists(os.path.join(G, "resources.json")):
    r = json.load(open(os.path.join(G, "resources.json")))["apks"]
    apps = sorted(({"package": v.get("package"), "path": p, "knobs": v["knob_count"],
                    "drawables": v["drawable_count"], "arrays": len(v.get("arrays", {}))}
                   for p, v in r.items()), key=lambda a: -a["knobs"])
    json.dump({"apk_count": len(r), "total_knobs": sum(a["knobs"] for a in apps), "apps": apps},
              open(os.path.join(G, "resources.summary.json"), "w"), indent=1, ensure_ascii=False)
PY
python3 "$T/build_site.py" "$G" "$REPO/docs/site/$SLUG" 2>&1 | tail -1
echo "DONE $SLUG"
