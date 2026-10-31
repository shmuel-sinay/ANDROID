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


PAGE = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#0f1117;--card:#1a1d27;--br:#2a2f3e;--fg:#e6e8ee;--mut:#9aa2b4;
--ac:#6ea8fe;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;--chip:#242838}}
@media(prefers-color-scheme:light){{:root:not([data-theme=dark]){{--bg:#f6f7f9;
--card:#fff;--br:#e3e6ec;--fg:#1a1d27;--mut:#5b6472;--ac:#2563eb;--chip:#eef1f6}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
font-family:system-ui,"Segoe UI",Arial,sans-serif;line-height:1.6}}
a{{color:var(--ac);text-decoration:none}}a:hover{{text-decoration:underline}}
.wrap{{max-width:1040px;margin:0 auto;padding:16px}}
header.top{{border-bottom:1px solid var(--br);background:var(--card)}}
header.top .wrap{{display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}}
header.top h1{{font-size:18px;margin:12px 0}}
nav.crumbs{{font-size:13px;color:var(--mut);margin:12px 0}}
.grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}}
.card{{background:var(--card);border:1px solid var(--br);border-radius:12px;padding:16px}}
.card h3{{margin:0 0 8px}}
.muted{{color:var(--mut)}}
.chip{{display:inline-block;background:var(--chip);border:1px solid var(--br);
border-radius:999px;padding:1px 10px;font-size:12px;margin:2px 2px}}
.ok{{color:var(--ok)}}.warn{{color:var(--warn)}}.bad{{color:var(--bad)}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}}
th,td{{border:1px solid var(--br);padding:7px 9px;text-align:right;vertical-align:top}}
th{{background:var(--chip)}}
code,pre{{font-family:ui-monospace,Menlo,Consolas,monospace;direction:ltr;unicode-bidi:plaintext}}
code{{background:var(--chip);padding:1px 5px;border-radius:5px;font-size:13px}}
pre{{background:var(--chip);border:1px solid var(--br);border-radius:10px;padding:12px;overflow:auto;text-align:left}}
h2{{border-bottom:1px solid var(--br);padding-bottom:6px;margin-top:28px}}
input#q{{width:100%;padding:10px 14px;border-radius:10px;border:1px solid var(--br);
background:var(--card);color:var(--fg);font-size:15px;margin:10px 0}}
.row{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--br);padding:8px 0}}
.row:last-child{{border-bottom:none}}
.pill{{font-size:11px;padding:1px 8px;border-radius:999px}}
.pill.b{{background:rgba(248,113,113,.15);color:var(--bad)}}
.pill.d{{background:rgba(251,191,36,.15);color:var(--warn)}}
.pill.o{{background:rgba(74,222,128,.15);color:var(--ok)}}
footer{{color:var(--mut);font-size:12px;border-top:1px solid var(--br);margin-top:40px}}
footer .wrap{{padding:16px}}
</style>
</head>
<body>
<header class="top"><div class="wrap">
<h1><a href="{root}index.html">אטלס אנדרואיד</a></h1>
<span class="muted">{subtitle}</span>
</div></header>
<div class="wrap">
<nav class="crumbs">{crumbs}</nav>
{body}
</div>
<footer><div class="wrap">נוצר אוטומטית מניתוח הרום · תיעוד תיאורטי, לא נבדק על מכשיר · {stamp}</div></footer>
</body></html>"""


def page(path, title, subtitle, crumbs, body, depth):
    root = "../" * depth
    open(path, "w", encoding="utf-8").write(PAGE.format(
        title=e(title), subtitle=e(subtitle), crumbs=crumbs, body=body,
        root=root, stamp="GTR · Qin F21 Pro"))


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
    cards = f"""
<div class="grid">
<div class="card"><h3>המכשיר</h3>
<div class="row"><span class="muted">דגם</span><b>{e(model)}</b></div>
<div class="row"><span class="muted">אנדרואיד</span><b>{e(ver)} (SDK {e(sysprop.get('ro.build.version.sdk',''))})</b></div>
<div class="row"><span class="muted">עדכון אבטחה</span><b dir=ltr>{e(patch)}</b></div>
<div class="row"><span class="muted">מעבד</span><b>MediaTek MT6761</b></div>
</div>
<div class="card"><h3>רכיבים</h3>
<div class="row"><span class="muted">אפליקציות (APK)</span><b>{len(apks)}</b></div>
<div class="row"><span class="muted">שירותי init</span><b>{len(init['services'])}</b></div>
<div class="row"><span class="muted">בדיקות "חובה" במסלול אתחול</span><b>{len(onboot)}</b></div>
<div class="row"><span class="muted">מחיקות שמפילות אתחול</span><b class="bad">{len(bl)}</b></div>
</div>
</div>
<h2>מה הכי חשוב לדעת</h2>
<div class="grid">
<a class="card" href="delete/index.html"><h3>מה יקרה אם אמחק?</h3>
<p class="muted">לכל רכיב: האם מחיקה שלו תפיל את המערכת, ולמה.</p></a>
<a class="card" href="boot/index.html"><h3>שרשרת האתחול והאימות</h3>
<p class="muted">preloader → lk → boot → init, ואיך הרום עוקף את ה-AVB.</p></a>
<a class="card" href="apps/index.html"><h3>כל האפליקציות</h3>
<p class="muted">{len(apks)} אפליקציות: הרשאות, priv-app, sharedUserId.</p></a>
<a class="card" href="init/index.html"><h3>שירותי init</h3>
<p class="muted">מי מפעיל את מי, ומה קריטי.</p></a>
<a class="card" href="guards/index.html"><h3>בדיקות "חובה" בקוד</h3>
<p class="muted">{len(onboot)} מקומות בקוד שזורקים שגיאה כשרכיב חסר.</p></a>
<a class="card" href="deps/index.html"><h3>תלויות מפורקות</h3>
<p class="muted">ניתוח קוד מלא לרכיבים נבחרים.</p></a>
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
