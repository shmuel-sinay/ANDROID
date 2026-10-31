# מפת דרכים

## שלב 0 – תשתית
- [x] מבנה ריפו ומדיניות
- [x] פענוח scatter של MediaTek
- [x] כלי פירוק super (liblp) – `tools/lp_unpack.py`
- [ ] כלי פענוח vbmeta (AVB) עצמאי
- [ ] כלי פירוק boot.img (kernel / ramdisk / cmdline)
- [ ] סקריפט פירוק אוטומטי מקצה לקצה לכל רום

## שלב 1 – מצאי
- [ ] מפת מחיצות פיזיות ולוגיות + תפקיד כל מחיצה
- [ ] מצאי קבצים לכל מחיצה (JSON)
- [ ] מצאי APK: חבילה, מיקום, הרשאות, sharedUserId, priv-app

## שלב 2 – שרשרת אתחול ואימות
- [ ] preloader → lk → tee → vbmeta → boot
- [ ] vbmeta: מה מאומת, באילו מפתחות, איזה דגלים
- [ ] fstab: מחיצות, דגלי avb/verity
- [ ] ramdisk ו-first stage init
- [ ] גרף init.rc: שירותים, טריגרים, properties

## שלב 3 – גרף אפליקציות ותלויות
- [ ] אפליקציות חובה של PackageManager (installer, permission controller, וכו')
- [ ] privapp-permissions מול מניפסטים
- [ ] ספריות משותפות, uses-library, sharedUserId
- [ ] הגדרות framework-res שמפנות לחבילות
- [ ] חיזוי: "מה יקרה אם אמחק X"

## שלב 4 – שכבות עמוקות
- [ ] SELinux, APEX, overlays, HAL של vendor

## שלב 5 – אתר תיעוד
- [ ] אתר סטטי בעברית (RTL), חיפוש, גרפים, עמוד לכל רכיב
- [ ] פרסום ב-GitHub Pages

## שלב 6 – השוואה בין רומים
- [ ] רום מקורי (restore) כבסיס
- [ ] השוואה לרומים מותאמים: מה הוסר והמערכת עדיין עולה
