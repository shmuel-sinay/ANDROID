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
