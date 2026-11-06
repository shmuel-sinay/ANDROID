#!/usr/bin/env python3
"""Replace every page under docs/site/ with a small redirect stub pointing
at the new home on kosher-tek.com/roms/, so old links and Google's index
carry over to the new location instead of 404ing.

Usage: make_redirects.py docs/site
"""
import os
import sys

NEW_BASE = "https://kosher-tek.com"

STUB = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0;url={url}">
</head>
<body><p>הדף עבר ל-<a href="{url}">{url}</a></p></body>
</html>
"""


def route_for(site_root, path):
    rel = os.path.relpath(path, site_root).replace(os.sep, "/")
    if rel == "index.html":
        return ""
    if rel.endswith("/index.html"):
        return rel[: -len("/index.html")]
    if rel.endswith(".html"):
        return rel[:-5]
    return None


def main():
    root = sys.argv[1]
    n = 0
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(".html"):
                continue
            fp = os.path.join(dp, fn)
            route = route_for(root, fp)
            if route is None:
                continue
            if route == "":
                url = NEW_BASE + "/roms/"
            else:
                url = NEW_BASE + "/roms/" + route + "/"
            open(fp, "w", encoding="utf-8").write(STUB.format(title="הדף עבר", url=url))
            n += 1
    print(f"{n} redirect stubs written under {root}")


if __name__ == "__main__":
    main()
