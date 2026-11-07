#!/usr/bin/env python3
"""Find apps that carry their OWN native video decoder, bypassing the
system's MediaCodec/Codec2 framework entirely.

This matters for system-level video blocking: neutralizing the system
codec registries (see deps/block_video_system_level.md) does nothing to
an app that links a self-contained decoder (ffmpeg, libvpx, libde265, a
vendor SDK's own .so) and calls it directly. This tool finds such apps so
they can be handled separately (blocked outright, or excluded from the ROM).

Method: for every APK, list native libraries under lib/*/*.so, and flag:
  (a) known decoder library name patterns (ffmpeg, libvpx, libde265, ...)
  (b) any .so whose exported dynamic symbols contain a codec-looking name
      (avcodec_*, vpx_codec_*, h264_decode, hevc_decode, ...), found via
      `nm -D` / readelf, so a renamed library doesn't slip through.

Usage: bundled_decoders.py ROM_FS_DIR OUT.json
Needs: unzip, nm (binutils) or readelf.
"""
import json
import os
import re
import subprocess
import sys
import zipfile

NAME_PATTERNS = re.compile(
    r"ffmpeg|avcodec|avformat|libvpx|vpx|libde265|de265|x264|x265|libaom|"
    r"dav1d|libwebp|mediacodec|openh264|libyuv|gstreamer|exoplayer.*native|"
    r"libstagefright(?!_soft)",  # a *bundled* stagefright clone, not the system one
    re.I)

SYMBOL_PATTERNS = re.compile(
    r"avcodec_(decode|send_packet|receive_frame)|vpx_codec_(decode|dec_init)|"
    r"de265_decode|h264_decode|hevc_decode|H264Decode|HEVCDecode|"
    r"omx_video.*decode|C2SoftAvc|C2SoftHevc", re.I)


def native_symbols(path):
    try:
        out = subprocess.run(["nm", "-D", "--defined-only", path],
                             capture_output=True, text=True, timeout=30).stdout
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return []
    return [ln.rsplit(" ", 1)[-1] for ln in out.splitlines() if ln.strip()]


def scan_apk(apk):
    hits = []
    try:
        with zipfile.ZipFile(apk) as z:
            libs = [n for n in z.namelist() if n.startswith("lib/") and n.endswith(".so")]
            if not libs:
                return hits
            tmp = "/tmp/_bundled_decoder_scan"
            os.makedirs(tmp, exist_ok=True)
            for lib in libs:
                base = os.path.basename(lib)
                name_hit = NAME_PATTERNS.search(base)
                sym_hit = None
                if not name_hit:
                    # only pay the extraction+nm cost for libraries whose
                    # name gives no hint, to keep this fast across 200 APKs
                    try:
                        z.extract(lib, tmp)
                        syms = native_symbols(os.path.join(tmp, lib))
                        m = next((s for s in syms if SYMBOL_PATTERNS.search(s)), None)
                        if m:
                            sym_hit = m
                    except (OSError, KeyError):
                        pass
                    finally:
                        p = os.path.join(tmp, lib)
                        if os.path.exists(p):
                            os.remove(p)
                if name_hit or sym_hit:
                    hits.append({"lib": lib, "matched_name": bool(name_hit), "matched_symbol": sym_hit})
    except (zipfile.BadZipFile, OSError):
        pass
    return hits


def main():
    root, out = sys.argv[1], sys.argv[2]
    results = []
    apks = []
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".apk"):
                apks.append(os.path.join(dp, fn))
    for i, apk in enumerate(sorted(apks)):
        hits = scan_apk(apk)
        if hits:
            results.append({"apk": os.path.relpath(apk, root), "libs": hits})
    json.dump({"apk_count": len(apks), "flagged": results}, open(out, "w"),
              indent=1, ensure_ascii=False)
    print(f"{len(apks)} APKs scanned, {len(results)} carry a possible bundled video decoder")
    for r in results:
        print(" ", r["apk"], [h["lib"] for h in r["libs"]])


if __name__ == "__main__":
    main()
