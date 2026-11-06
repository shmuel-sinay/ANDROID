# התקדמות

## Qin F21 Pro — gapps super — רום עשירי
- כיסוי 100%, 190 אפליקציות, 67 בדיקות אתחול


## Qin F21 Pro — LineageOS 20 — רום תשיעי (הגדול ביותר)
- 698 אפליקציות, 69 בדיקות אתחול, 12 מחיקות מפילות, כיסוי 100%


## Qin F22 Pro — unlocked GTR — רום שמיני
- כיסוי 100%, 187 אפליקציות, 62 בדיקות אתחול


## Qin F21 Pro — LineageOS 18.1 — רום שביעי
- רום קאסטום מלא: 496 אפליקציות (כפול מ-stock), 68 בדיקות אתחול, 13 מחיקות מפילות
- coverage.py: סיווג userland של לינוקס (terminfo/vim/bash/ssh) שמגיע עם Lineage
- כיסוי 100%


## Tiq M5 — רום שישי (מכשיר אחר, אנדרואיד 13 / MT6761)
- כיסוי 100%, 197 אפליקציות, 67 בדיקות אתחול
- מכשיר שונה מ-Qin — מרחיב את מאגר ההשוואה


## Qin F21 Pro — A.I.V כשרה — רום חמישי
- כיסוי 100%, 195 אפליקציות, 67 בדיקות אתחול
- coverage.py: סיווג קובצי גיבוי (.bak/.a) שהשאיר בונה הרום


## Qin F21 Pro — AOSP 13 beta (AIV) — רום רביעי
- אותו מכשיר (MT6761) עם אנדרואיד 13 — השוואה בין-גרסאות על אותה חומרה
- כיסוי 100%, 190 אפליקציות, 68 בדיקות אתחול, 9 מחיקות מפילות אתחול
- תיקון: boot_guards מדלג על jar חסר (AOSP ללא mediatek-*.jar)


## Qin F22 Pro — רום שלישי (אנדרואיד 12 / MT6768)
- רום מקורי, כיסוי 100% (0 ממתינים), 210 אפליקציות, **15,431 מתגי תצורה**
- רץ דרך הצינור האוטומטי (`extract_mtk.sh` + `analyze_rom.sh`) — פקודה אחת
- 3,711 ספריות native (9 תלויות מסופקות דרך APEX בזמן ריצה), VINTF שלם
- אתר: docs/site/f22-pro-a13


## M36 Plus — רום שני (סריקת עומק, אנדרואיד 13 / MT6765)
- רום מקורי עם AVB פעיל (ניגוד ל-F21 GTR שאימות כבוי)
- כיסוי 100%: 6,615 קבצים (4.31GB כולל APEX מחולץ), 0 ממתינים
- חילוץ APEX: 30 חבילות, 1,719 קבצים (`tools/apex_unpack.py`) — קריטי כי ב-A13 רכיבי מפתח בתוך APEX
- סריקת עומק: 202 אפליקציות, **11,808 מתגי תצורה** (`tools/resources.py`) — לכל אפליקציה config_*/bool/integer
- SystemUI: 109 מתגים לשורת הסטטוס; Settings: 734 מתגים — `deps/overlays.md` (שיטת RRO להוספה/הסרה)
- removal_recipes: 180 חבילות (8 bootloop)
- VINTF: 0 HAL חובה חסרים; native: 3,000+ ELF, 0 תלויות חסרות
- אתר: docs/site/m36-plus (כולל עמוד "מתגי תצורה")


## מקורות
- Qin F21 Pro – חבילת "f21 GTR" (תיקיית Drive מהפורום, סיסמת ארכיון: TripleU)
- הרום המקורי (spflash-f21pro-restore-1.0.8) – נעול להורדה בתיקייה; המשתמש יעלה עותק

## ממצאים – Qin F21 Pro (GTR)
- MT6761, אנדרואיד 11 (SDK 30), patch 2020-12-05
- fingerprint: Qin/full_k61v1_64_gms/k61v1_64_bsp:11/RP1A.200720.011/79:user/release-keys
- 48 מחיצות פיזיות (scatter), A/B – רק חריץ A צרוב
- super: system_a 2.1GB, vendor_a 355MB, product_a 163MB, system_b 37MB – כולן ext4
- system-as-root

- שרשרת אתחול ו-AVB מתועדות: `roms/qin-f21-pro/gtr/BOOT_CHAIN.md`
- GTR עוקף אימות בארבע שכבות: דגלי vbmeta, הסרת avb מ-fstab, system/vendor לא חתומים, boot ללא footer + ramdisk לא מאובטח

## שרת המשתמש
- Ubuntu 24.04 ARM64 (Oracle), 4 ליבות, 23GB RAM, 17GB פנוי, ללא KVM, sudo ללא סיסמה, docker קיים
- Remote Control רץ ב-~/android-docs (סביבת bridge). שירות קבוע – ממתין לאישור המשתמש בסשן השרת

- init: 188 שירותים, 5 קריטיים (ueventd, servicemanager, hwservicemanager, lmkd, charger); 26 שירותים מצביעים על קובץ חסר והמערכת עולה – `INIT.md`
- 175 APK, 12 persistent, privapp enforce ללא הפרות; אין package verifier (אין GMS) – `DELETE_IMPACT.md`

- **ניתוח קוד ברמת מקור:** `tools/boot_guards.py` סורק את services.jar ומוצא כל מקום שזורק שגיאה כשמשהו "חובה" חסר, ובודק אם הוא במסלול האתחול. ברום הזה: 552 בדיקות, 40 במסלול האתחול – `boot_guards.json`
- תלות ראשונה מפורקת עד הסוף: המתקין – `deps/installer.md` (הקוד, 4 התנאים, כל הקוראים, ומה צריך לשנות כדי לבטל)

## כיסוי מלא (לבקשת המשתמש – לא לדגום, לעבור על הכל)
- `tools/coverage.py`: רישום כל 5,130 הקבצים ברום עם sha256 וסיווג. עומק הניתוח לכל קטגוריה – `coverage.json`, ובאתר תחת "כיסוי הניתוח".
- `tools/native_deps.py`: גרף התלויות של 2,630 ספריות native (‎.so). כל DT_NEEDED נפתר – אפס תלויות חסרות. הספריות הכי נשענות: libc, libm, libdl, libc++, liblog – `native_deps.json`.
- מצב כיסוי נוכחי: 3,126 קבצים נותחו ע"י כלי (parsed/partial), 1,451 נרשמו (assets/data), 1,069 ממתינים לכלי (xml config, selinux, protobuf, scripts).

## כיסוי מלא הושלם — 0 קבצים ממתינים
כל 5,130 הקבצים ברום מכוסים (`coverage.summary.json`):
- 3,663 נותחו לעומק · 75 חלקית (jars) · 1,908 נרשמו ומסווגים · **0 ממתינים**
- כלים חדשים: `native_deps.py` (הורחב לקבצי הרצה: 2,778 ספריות + 268 executables), `xml_config.py` (VINTF: 337 HAL מסופקים, 396 נדרשים, **0 חובה חסרים**), `selinux.py` (contexts, CIL, seccomp), `misc_files.py` (scripts, APEX manifests, modules.dep)
- כל שכבות התלות שלמות: native (0 .so חסרים), VINTF (0 HAL חובה חסרים), kernel modules (modules.dep)

## הצעד הבא
- לפרק כל אחת מ-40 הבדיקות שבמסלול האתחול לקובץ `deps/` משלה (כמו installer.md)
- להוסיף framework.jar ו-mediatek-services.jar לסריקה
- תלויות שאינן "זריקה" (למשל SettingsProvider – קריסה עקיפה)
- תלויות ברמת ספריות (.so) ו-uses-library, ותלות framework-res בשמות חבילות (config_*)
- SELinux: אילו דומיינים מגדירים שירותים קריטיים
- התחלת אתר התיעוד (GitHub Pages)
