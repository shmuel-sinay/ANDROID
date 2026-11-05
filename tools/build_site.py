#!/usr/bin/env python3
"""Build a static Hebrew (RTL) documentation site for one analyzed ROM.

Usage: build_site.py ROM_DIR OUT_DIR

ROM_DIR holds the JSON/MD files produced by the other tools. The site is
self-contained HTML (no build step, no external JS) so GitHub Pages can
serve it directly. Every page is generated from the data files, so
re-running the analysis and this script refreshes the whole site.
"""
import html
import json
import os
import re
import sys


def load_json(d, name, default=None):
    p = os.path.join(d, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def read_prop(path):
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def e(s):
    return html.escape(str(s if s is not None else ""))


AUTHOR = "שמואל סיני"
REPO = "https://github.com/shmuel-sinay/ANDROID"

PAGE = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="author" content="{author}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0b0d13;--bg2:#10131c;--card:#161a26;--card2:#1b2030;--br:#272d3e;
--fg:#edeff5;--mut:#9aa3b8;--ac:#7ca8ff;--ac2:#a98bff;--ok:#4ade80;--warn:#fbbf24;
--bad:#fb7185;--chip:#20273a;--shadow:0 10px 30px rgba(0,0,0,.35);
--grad:linear-gradient(135deg,#7c3aed22,#2563eb22)}}
@media(prefers-color-scheme:light){{:root:not([data-theme=dark]){{--bg:#f4f6fb;--bg2:#fff;
--card:#fff;--card2:#f7f9fc;--br:#e5e9f0;--fg:#161a26;--mut:#5c6578;--ac:#2563eb;
--ac2:#7c3aed;--chip:#eef2f9;--shadow:0 8px 24px rgba(30,41,80,.08);
--grad:linear-gradient(135deg,#7c3aed14,#2563eb14)}}}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--fg);
font-family:"Heebo",system-ui,"Segoe UI",Arial,sans-serif;line-height:1.65;
-webkit-font-smoothing:antialiased}}
a{{color:var(--ac);text-decoration:none;transition:color .15s}}
a:hover{{color:var(--ac2)}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}
header.top{{position:sticky;top:0;z-index:20;backdrop-filter:blur(12px);
background:color-mix(in srgb,var(--bg) 82%,transparent);border-bottom:1px solid var(--br)}}
header.top .bar{{display:flex;gap:16px;align-items:center;justify-content:space-between;
max-width:1080px;margin:0 auto;padding:14px 20px}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px}}
.brand .logo{{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--ac),var(--ac2));
display:grid;place-items:center;color:#fff;font-size:17px;box-shadow:var(--shadow)}}
.brand .sub{{font-weight:500;color:var(--mut);font-size:13px}}
.top-links{{display:flex;gap:18px;font-size:14px;font-weight:500}}
nav.crumbs{{font-size:13px;color:var(--mut);margin:22px 0 4px}}
nav.crumbs a{{color:var(--mut)}}
h2{{font-size:22px;font-weight:800;margin:34px 0 4px;letter-spacing:-.01em}}
h2::after{{content:"";display:block;width:44px;height:3px;border-radius:3px;
background:linear-gradient(90deg,var(--ac),var(--ac2));margin-top:8px}}
h3{{margin:0 0 8px;font-weight:700}}h4{{margin:18px 0 6px;font-weight:700}}
p{{margin:10px 0}}
.lead{{color:var(--mut);font-size:15.5px;max-width:70ch}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));margin:18px 0}}
.card{{background:var(--card);border:1px solid var(--br);border-radius:16px;padding:20px;
transition:transform .18s,border-color .18s,box-shadow .18s}}
a.card:hover{{transform:translateY(-3px);border-color:var(--ac);box-shadow:var(--shadow)}}
.card h3{{display:flex;align-items:center;gap:9px}}
.ic{{width:30px;height:30px;border-radius:9px;background:var(--grad);display:grid;
place-items:center;font-size:16px;flex:none}}
.muted{{color:var(--mut)}}
.chip{{display:inline-block;background:var(--chip);border:1px solid var(--br);
border-radius:999px;padding:2px 11px;font-size:12px;margin:2px 2px;font-weight:500}}
.ok{{color:var(--ok)}}.warn{{color:var(--warn)}}.bad{{color:var(--bad)}}
table{{width:100%;border-collapse:separate;border-spacing:0;margin:16px 0;font-size:14px;
background:var(--card);border:1px solid var(--br);border-radius:14px;overflow:hidden}}
th,td{{padding:10px 13px;text-align:right;vertical-align:top;border-bottom:1px solid var(--br)}}
th{{background:var(--card2);font-weight:700;position:sticky;top:61px}}
tr:last-child td{{border-bottom:none}}
tbody tr:hover,table tr:hover{{background:color-mix(in srgb,var(--ac) 6%,transparent)}}
code,pre{{font-family:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;
direction:ltr;unicode-bidi:plaintext}}
code{{background:var(--chip);padding:2px 6px;border-radius:6px;font-size:12.5px}}
pre{{background:#0d1017;border:1px solid var(--br);border-radius:12px;padding:16px;
overflow:auto;text-align:left;font-size:13px;line-height:1.55}}
pre code{{background:none;padding:0}}
blockquote{{border-right:3px solid var(--ac);margin:14px 0;padding:4px 14px;
background:var(--card2);border-radius:0 10px 10px 0}}
input#q{{width:100%;padding:12px 16px;border-radius:12px;border:1px solid var(--br);
background:var(--card);color:var(--fg);font-size:15px;margin:12px 0;font-family:inherit}}
input#q:focus{{outline:none;border-color:var(--ac);box-shadow:0 0 0 3px color-mix(in srgb,var(--ac) 20%,transparent)}}
.row{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--br);padding:9px 0}}
.row:last-child{{border-bottom:none}}
.pill{{font-size:11.5px;padding:2px 10px;border-radius:999px;font-weight:600;white-space:nowrap}}
.pill.b{{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}}
.pill.d{{background:color-mix(in srgb,var(--warn) 16%,transparent);color:var(--warn)}}
.pill.o{{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}}
footer{{border-top:1px solid var(--br);margin-top:56px;background:var(--bg2)}}
footer .wrap{{padding:28px 20px;display:flex;justify-content:space-between;
align-items:center;gap:16px;flex-wrap:wrap}}
footer .by{{font-size:14px}}footer .by b{{color:var(--fg)}}
footer .meta{{font-size:12.5px;color:var(--mut)}}
.avatar{{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--ac2),var(--ac));
display:inline-grid;place-items:center;color:#fff;font-weight:800;margin-left:8px;vertical-align:middle}}
</style>
</head>
<body>
<header class="top"><div class="bar">
<a class="brand" href="{root}index.html">
<span class="logo">◆</span><span>אטלס אנדרואיד<br><span class="sub">{subtitle}</span></span></a>
<nav class="top-links">
<a href="{root}index.html">בית</a>
<a href="{repo}">קוד המקור</a>
</nav>
</div></header>
<div class="wrap">
<nav class="crumbs">{crumbs}</nav>
{body}
</div>
<footer><div class="wrap">
<div class="by"><span class="avatar">{initial}</span>תיעוד ומחקר · <b>{author}</b></div>
<div class="meta">נוצר אוטומטית מניתוח הרום · תיעוד תיאורטי, לא נבדק על מכשיר · {stamp}</div>
</div></footer>
</body></html>"""


def page(path, title, subtitle, crumbs, body, depth):
    root = "../" * depth
    open(path, "w", encoding="utf-8").write(PAGE.format(
        title=e(title), subtitle=e(subtitle), crumbs=crumbs, body=body,
        root=root, stamp="GTR · Qin F21 Pro", author=e(AUTHOR),
        initial=e(AUTHOR.strip()[0]), repo=REPO))


def sev_pill(sev):
    return {"bootloop": '<span class="pill b">לולאת אתחול</span>',
            "degraded": '<span class="pill d">עולה חלקית</span>'}.get(sev, "")


def main():
    rom, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    sysprop = read_prop(os.path.join(rom, "system.build.prop"))
    roles = load_json(rom, "boot_roles.json", {"roles": []})
    apks = load_json(rom, "apks.json", {"apks": []})["apks"]
    guards = load_json(rom, "boot_guards.json", {"guards": []})
    cfg = load_json(rom, "framework_config_refs.json", [])
    init = load_json(rom, "init_graph.json", {"services": {}, "actions": []})

    model = sysprop.get("ro.product.system.model", "Qin F21 Pro")
    ver = sysprop.get("ro.build.version.release", "11")
    patch = sysprop.get("ro.build.version.security_patch", "")

    # ---- index ----
    bl = [r for r in roles["roles"] if r["if_missing"] == "bootloop" and r["status"] == "ok"]
    dg = [r for r in roles["roles"] if r["if_missing"] == "degraded"]
    onboot = [g for g in guards.get("guards", []) if g.get("boot_path")]
    hero = f"""
<section style="padding:30px 0 6px">
<div style="display:inline-block;background:var(--grad);border:1px solid var(--br);
border-radius:999px;padding:5px 14px;font-size:13px;font-weight:600;margin-bottom:14px">
📱 {e(model)} · MediaTek MT6761</div>
<h1 style="font-size:40px;font-weight:800;margin:4px 0 10px;letter-spacing:-.02em;line-height:1.15">
מה בונה מה, ומה יקרה אם אמחק רכיב</h1>
<p class="lead" style="font-size:17px">תיעוד מלא של הרום, שנוצר אוטומטית מניתוח הקבצים עצמם:
שרשרת האתחול, האימות, כל האפליקציה, כל שירות, וכל בדיקת "חובה" בקוד שעלולה להפיל את המערכת.</p>
</section>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:22px">
<div class="card" style="text-align:center;padding:22px 14px">
<div style="font-size:34px;font-weight:800;color:var(--ac)">{len(apks)}</div>
<div class="muted">אפליקציות</div></div>
<div class="card" style="text-align:center;padding:22px 14px">
<div style="font-size:34px;font-weight:800;color:var(--ac)">{len(init['services'])}</div>
<div class="muted">שירותי init</div></div>
<div class="card" style="text-align:center;padding:22px 14px">
<div style="font-size:34px;font-weight:800;color:var(--warn)">{len(onboot)}</div>
<div class="muted">בדיקות חובה באתחול</div></div>
<div class="card" style="text-align:center;padding:22px 14px">
<div style="font-size:34px;font-weight:800;color:var(--bad)">{len(bl)}</div>
<div class="muted">מחיקות שמפילות אתחול</div></div>
</div>"""
    cards = hero + f"""
<h2>מה הכי חשוב לדעת</h2>
<div class="grid">
<a class="card" href="remove/index.html"><h3><span class="ic">🧰</span>מרשמי הסרה</h3>
<p class="muted">איך למחוק רכיב בבטחה — ואיך לנטרל כל תלות. מוכן להעלאה ל-AI.</p></a>
<a class="card" href="delete/index.html"><h3><span class="ic">⚠️</span>מה יקרה אם אמחק?</h3>
<p class="muted">לכל רכיב: האם מחיקה שלו תפיל את המערכת, ולמה.</p></a>
<a class="card" href="deps/index.html"><h3><span class="ic">🔬</span>תלויות מפורקות</h3>
<p class="muted">ניתוח קוד מלא: מה נבדק, מי משתמש בתוצאה, ואיך לבטל.</p></a>
<a class="card" href="guards/index.html"><h3><span class="ic">🛡️</span>בדיקות "חובה" בקוד</h3>
<p class="muted">{len(onboot)} מקומות בקוד שזורקים שגיאה כשרכיב חסר.</p></a>
<a class="card" href="apps/index.html"><h3><span class="ic">📦</span>כל האפליקציות</h3>
<p class="muted">{len(apks)} אפליקציות: הרשאות, priv-app, sharedUserId.</p></a>
<a class="card" href="init/index.html"><h3><span class="ic">⚙️</span>שירותי init</h3>
<p class="muted">מי מפעיל את מי, ומה קריטי לאתחול.</p></a>
<a class="card" href="native/index.html"><h3><span class="ic">🧩</span>ספריות native</h3>
<p class="muted">גרף התלויות של קוד C/C++ המהודר (‎.so).</p></a>
<a class="card" href="coverage/index.html"><h3><span class="ic">✓</span>כיסוי הניתוח</h3>
<p class="muted">כל קובץ ברום, עם טביעת אצבע — מה נותח ומה לא.</p></a>
</div>"""
    page(os.path.join(out, "index.html"), f"אטלס אנדרואיד – {model}",
         f"{model} · אנדרואיד {ver}", "דף הבית", cards, 0)

    # ---- delete impact ----
    os.makedirs(os.path.join(out, "delete"), exist_ok=True)
    rows = ""
    for r in roles["roles"]:
        rows += (f'<tr><td>{e(r["role"])}</td><td>{sev_pill(r["if_missing"])}</td>'
                 f'<td>{"".join(f"<code>{e(p)}</code> " for p in r["filled_by"]) or "<span class=bad>חסר</span>"}</td>'
                 f'<td class="muted">{e(r["confidence"])}</td>'
                 f'<td class="muted" dir=ltr style="font-size:12px">{e(r["basis"])}</td></tr>')
    body = f"""<h2>מה יקרה אם אמחק רכיב?</h2>
<p class="muted">מבוסס על קוד האתחול של אנדרואיד {e(ver)}. תחזית תיאורטית – ראו גם <a href="../guards/index.html">בדיקות החובה</a> ו<a href="../deps/index.html">התלויות המפורקות</a>.</p>
<table><tr><th>תפקיד</th><th>אם חסר</th><th>חבילה ברום</th><th>ביטחון</th><th>מקור בקוד</th></tr>{rows}</table>"""
    page(os.path.join(out, "delete", "index.html"), "מה יקרה אם אמחק",
         f"{model}", '<a href="../index.html">בית</a> / מחיקה', body, 1)

    # ---- apps (with client-side search) ----
    os.makedirs(os.path.join(out, "apps"), exist_ok=True)
    data = [{"p": a.get("package"), "path": a["path"], "priv": a.get("priv_app"),
             "su": a.get("sharedUserId"), "persist": a.get("persistent"),
             "perms": len(a.get("permissions_requested", []))} for a in apks if a.get("package")]
    rows = "".join(
        f'<tr><td><code>{e(d["p"])}</code></td>'
        f'<td>{"<span class=chip>priv</span>" if d["priv"] else ""}'
        f'{"<span class=chip>persistent</span>" if d["persist"] else ""}</td>'
        f'<td class=muted dir=ltr>{e(d["su"] or "")}</td>'
        f'<td>{d["perms"]}</td>'
        f'<td class=muted dir=ltr style="font-size:12px">{e(d["path"])}</td></tr>'
        for d in sorted(data, key=lambda x: x["p"]))
    body = f"""<h2>אפליקציות ({len(data)})</h2>
<input id="q" placeholder="חיפוש לפי שם חבילה או נתיב...">
<table id="t"><tr><th>חבילה</th><th>סוג</th><th>sharedUserId</th><th>הרשאות</th><th>נתיב</th></tr>{rows}</table>
<script>
var q=document.getElementById('q'),rows=[].slice.call(document.querySelectorAll('#t tr')).slice(1);
q.addEventListener('input',function(){{var v=q.value.toLowerCase();rows.forEach(function(r){{
r.style.display=r.textContent.toLowerCase().indexOf(v)<0?'none':'';}});}});
</script>"""
    page(os.path.join(out, "apps", "index.html"), "אפליקציות",
         f"{model}", '<a href="../index.html">בית</a> / אפליקציות', body, 1)

    # ---- init ----
    os.makedirs(os.path.join(out, "init"), exist_ok=True)
    crit = [n for n, s in init["services"].items() if any(f.startswith("critical") for f in s["flags"])]
    srows = "".join(
        f'<tr><td><code>{e(n)}</code></td><td>{" ".join(f"<span class=chip>{e(c)}</span>" for c in s["classes"])}</td>'
        f'<td dir=ltr class=muted style="font-size:12px">{e(s["exec"])}</td>'
        f'<td>{"<span class=bad>critical</span>" if any(f.startswith("critical") for f in s["flags"]) else ""}</td></tr>'
        for n, s in sorted(init["services"].items()))
    body = f"""<h2>שירותי init ({len(init['services'])})</h2>
<p class="muted">שירותים קריטיים: {", ".join(f"<code>{e(c)}</code>" for c in crit)} – קריסה חוזרת שלהם מאתחלת ל-recovery.</p>
<input id="q" placeholder="חיפוש שירות...">
<table id="t"><tr><th>שירות</th><th>מחלקות</th><th>קובץ הרצה</th><th></th></tr>{srows}</table>
<script>var q=document.getElementById('q'),rows=[].slice.call(document.querySelectorAll('#t tr')).slice(1);
q.addEventListener('input',function(){{var v=q.value.toLowerCase();rows.forEach(function(r){{
r.style.display=r.textContent.toLowerCase().indexOf(v)<0?'none':'';}});}});</script>"""
    page(os.path.join(out, "init", "index.html"), "שירותי init",
         f"{model}", '<a href="../index.html">בית</a> / init', body, 1)

    # ---- guards ----
    os.makedirs(os.path.join(out, "guards"), exist_ok=True)
    grows = ""
    for g in sorted(onboot, key=lambda x: len(x["boot_path"])):
        m = g["method"].split("(")[0]
        grows += (f'<tr><td><code dir=ltr>{e(m)}</code></td>'
                  f'<td>{len(g["boot_path"])}</td>'
                  f'<td>{" ".join(f"<span class=chip>{e(x)}</span>" for x in g.get("exceptions",[]))}</td>'
                  f'<td class=muted dir=ltr style="font-size:12px">{e(g["messages"][0][:80])}</td></tr>')
    body = f"""<h2>בדיקות "חובה" במסלול האתחול ({len(onboot)})</h2>
<p class="muted">כל שורה היא מקום בקוד המערכת שזורק שגיאה כשרכיב חסר, ושנמצא במרחק קריאות מתחילת האתחול. מרחק קטן = קרוב יותר לקריסה ודאית.</p>
<table><tr><th>מתודה</th><th>מרחק מהאתחול</th><th>שגיאה</th><th>הודעה</th></tr>{grows}</table>"""
    page(os.path.join(out, "guards", "index.html"), "בדיקות חובה בקוד",
         f"{model}", '<a href="../index.html">בית</a> / בדיקות', body, 1)

    # ---- coverage ----
    cov = load_json(rom, "coverage.summary.json") or load_json(rom, "coverage.json")
    if cov:
        os.makedirs(os.path.join(out, "coverage"), exist_ok=True)
        depth_he = {"parsed": ("נותח לעומק", "ok"), "partial": ("נותח חלקית", "warn"),
                    "listed": ("נרשם ומסווג", "muted"), "pending": ("ממתין לכלי ניתוח", "bad")}
        bd = cov["by_depth"]
        tot = cov["totals"]["files"]
        bars = ""
        for d in ("parsed", "partial", "listed", "pending"):
            if d in bd:
                lab, cls = depth_he[d]
                pct = 100 * bd[d]["count"] / tot
                bars += (f'<div style="margin:10px 0"><div class="row" style="border:none;padding:2px 0">'
                         f'<span>{lab}</span><span class="{cls}"><b>{bd[d]["count"]}</b> קבצים ({pct:.0f}%)</span></div>'
                         f'<div style="height:9px;background:var(--chip);border-radius:6px;overflow:hidden">'
                         f'<div style="height:100%;width:{pct:.1f}%;background:var(--ac)"></div></div></div>')
        crows = "".join(
            f'<tr><td><code>{e(c)}</code></td><td>{v["count"]}</td>'
            f'<td>{v["bytes"]/1e6:.1f} MB</td>'
            f'<td><span class="{depth_he[v["depth"]][1]}">{depth_he[v["depth"]][0]}</span></td>'
            f'<td class="muted" style="font-size:13px">{e(v["how"])}</td></tr>'
            for c, v in cov["categories"].items())
        body = f"""<h2>כיסוי הניתוח</h2>
<p class="lead">כדי שלא יהיו הפתעות: כל קובץ ברום רשום כאן עם טביעת אצבע (sha256), מסווג, ומסומן באיזו עומק נותח. ככה "לא דילגתי על כלום" הוא מספר שאפשר לבדוק.</p>
<div class="card" style="margin:18px 0">
<div class="row" style="border:none"><b>סה"כ {tot} קבצים</b><span class="muted">{cov['totals']['bytes']/1e9:.2f} GB · {cov['totals']['symlinks']} קישורים</span></div>
{bars}</div>
<table><tr><th>קטגוריה</th><th>קבצים</th><th>נפח</th><th>עומק</th><th>איך נותח</th></tr>{crows}</table>"""
        page(os.path.join(out, "coverage", "index.html"), "כיסוי הניתוח", model,
             '<a href="../index.html">בית</a> / כיסוי', body, 1)

    # ---- native libraries ----
    nat = load_json(rom, "native_deps.summary.json") or load_json(rom, "native_deps.json")
    if nat:
        os.makedirs(os.path.join(out, "native"), exist_ok=True)
        top = "".join(f'<tr><td><code dir=ltr>{e(t["lib"])}</code></td><td>{t["needed_by_count"]}</td></tr>'
                      for t in nat["top_depended_on"][:25])
        miss = nat.get("missing_dependencies", {})
        miss_html = ("<p class='ok'>✓ כל התלויות קיימות ברום — אין ספרייה שמפנה ל-.so חסר.</p>"
                     if not miss else "<table><tr><th>חסר</th><th>כמה צריכים</th></tr>" +
                     "".join(f"<tr><td><code dir=ltr>{e(k)}</code></td><td>{v}</td></tr>" for k, v in list(miss.items())[:30]) + "</table>")
        arch = nat["machines"]
        body = f"""<h2>ספריות native ({nat['total_libs']})</h2>
<p class="lead">קוד C/C++ מהודר. מופה גרף התלויות: מה כל ספרייה צריכה (DT_NEEDED) וממה. ארכיטקטורות: {arch.get('EM_AARCH64',0)} ‏64-bit, {arch.get('EM_ARM',0)} ‏32-bit.</p>
<h3>שלמות</h3>{miss_html}
<h3>הספריות ש"הכל בנוי עליהן"</h3>
<p class="muted">מספר הספריות שתלויות בכל אחת. מחיקה של ספרייה כזו שוברת את כל התלויות בה.</p>
<table><tr><th>ספרייה</th><th>כמה תלויים בה</th></tr>{top}</table>"""
        page(os.path.join(out, "native", "index.html"), "ספריות native", model,
             '<a href="../index.html">בית</a> / native', body, 1)

    # ---- removal recipes ----
    rec = load_json(rom, "removal_recipes.json")
    if rec:
        os.makedirs(os.path.join(out, "remove"), exist_ok=True)
        risk_he = {"bootloop": ("לולאת אתחול", "b"), "critical": ("קריטי — לא למחוק", "b"),
                   "degraded": ("יאבד פונקציה", "d"), "safe": ("כנראה בטוח", "o")}
        order = {"bootloop": 0, "critical": 1, "degraded": 2, "safe": 3}
        rows = ""
        for pkg, r in sorted(rec["recipes"].items(), key=lambda kv: (order[kv[1]["risk"]], kv[0])):
            lab, cls = risk_he[r["risk"]]
            g = ""
            for x in r["boot_guards"][:3]:
                g += f'<div style="font-size:12px" class="muted"><code dir=ltr>{e(x["method"].split(".")[-1])}</code> — {e(x["neutralize"][:90])}</div>'
            roles = " ".join(f'<span class="chip">{e(x["role"])}</span>' for x in r["roles_filled"])
            rows += (f'<tr><td><code>{e(pkg)}</code>{"<br><span class=chip>persistent</span>" if r["persistent"] else ""}</td>'
                     f'<td><span class="pill {cls}">{lab}</span></td>'
                     f'<td>{roles}</td><td>{g or "<span class=muted>—</span>"}</td>'
                     f'<td class=muted>{e(", ".join(r["shares_uid_with"][:3]))}</td></tr>')
        br = rec["summary"]["by_risk"]
        body = f"""<h2>מרשמי הסרה</h2>
<p class="lead">לכל חבילה: האם אפשר למחוק, מה יקרוס, ואיך לנטרל כל בדיקה כדי שהמחיקה לא תפיל את האתחול.
זה הקובץ שאפשר להעלות ל-AI ולשאול "איך אני מוחק את X בבטחה".</p>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))">
<div class="card" style="text-align:center"><div style="font-size:30px;font-weight:800" class="bad">{len(br["bootloop"])+len(br["critical"])}</div><div class="muted">אסור למחוק</div></div>
<div class="card" style="text-align:center"><div style="font-size:30px;font-weight:800" class="warn">{len(br["degraded"])}</div><div class="muted">יאבד פונקציה</div></div>
<div class="card" style="text-align:center"><div style="font-size:30px;font-weight:800" class="ok">{len(br["safe"])}</div><div class="muted">כנראה בטוח</div></div>
</div>
<p class="muted">להורדה לשימוש ב-AI: <code>removal_recipes.json</code> + <code>AI_EXPORT.md</code> (מדריך קריאה) בריפו.</p>
<input id="q" placeholder="חיפוש חבילה...">
<table id="t"><tr><th>חבילה</th><th>סיכון</th><th>תפקידים</th><th>נטרול הבדיקות</th><th>משתף uid עם</th></tr>{rows}</table>
<script>var q=document.getElementById('q'),rows=[].slice.call(document.querySelectorAll('#t tr')).slice(1);
q.addEventListener('input',function(){{var v=q.value.toLowerCase();rows.forEach(function(r){{
r.style.display=r.textContent.toLowerCase().indexOf(v)<0?'none':'';}});}});</script>"""
        page(os.path.join(out, "remove", "index.html"), "מרשמי הסרה", model,
             '<a href="../index.html">בית</a> / הסרה', body, 1)

    # ---- deps (render the hand-written markdown files) ----
    os.makedirs(os.path.join(out, "deps"), exist_ok=True)
    deps_dir = os.path.join(rom, "deps")
    items = []
    if os.path.isdir(deps_dir):
        for fn in sorted(os.listdir(deps_dir)):
            if fn.endswith(".md"):
                slug = fn[:-3]
                md = open(os.path.join(deps_dir, fn), encoding="utf-8").read()
                title = next((l[2:] for l in md.splitlines() if l.startswith("# ")), slug)
                body = f'<article>{md_to_html(md)}</article>'
                page(os.path.join(out, "deps", slug + ".html"), title, model,
                     '<a href="../index.html">בית</a> / <a href="index.html">תלויות</a> / ' + e(title),
                     body, 1)
                items.append((slug, title))
    links = "".join(f'<a class="card" href="{e(s)}.html"><h3>{e(t)}</h3></a>' for s, t in items)
    body = f'<h2>תלויות מפורקות</h2><p class="muted">ניתוח קוד מלא: מה נבדק, מי משתמש בתוצאה, ואיך אפשר לבטל.</p><div class="grid">{links or "<p class=muted>אין עדיין.</p>"}</div>'
    page(os.path.join(out, "deps", "index.html"), "תלויות", model,
         '<a href="../index.html">בית</a> / תלויות', body, 1)

    print(f"site built: {out} ({len(apks)} apks, {len(onboot)} guards, {len(items)} deps)")


def md_to_html(md):
    """Tiny Markdown subset -> HTML (headings, code fences, inline code,
    tables, blockquotes, lists, bold). Enough for the deps .md files."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(e(lines[i]))
                i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
        elif ln.startswith("#"):
            n = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{min(n+1,4)}>{inline(ln[n:].strip())}</h{min(n+1,4)}>")
        elif ln.startswith(">"):
            out.append(f'<blockquote class="muted">{inline(ln[1:].strip())}</blockquote>')
        elif ln.strip().startswith("|") and i + 1 < len(lines) and set(lines[i+1].strip()) <= set("|-: "):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</table>")
            continue
        elif ln.strip().startswith(("- ", "* ")):
            out.append("<ul>")
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                out.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def inline(s):
    s = e(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


if __name__ == "__main__":
    main()
