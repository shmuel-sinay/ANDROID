# מפת דרכים

## שלב 0 – תשתית
- [x] מבנה ריפו ומדיניות
- [x] פענוח scatter של MediaTek
- [x] כלי פירוק super (liblp) – `tools/lp_unpack.py`
- [x] כלי פענוח vbmeta (AVB) עצמאי – `tools/avb_info.py`
- [x] כלי פירוק boot.img – `tools/bootimg.py`
- [ ] סקריפט פירוק אוטומטי מקצה לקצה לכל רום

## שלב 1 – מצאי
- [ ] מפת מחיצות פיזיות ולוגיות + תפקיד כל מחיצה
- [ ] מצאי קבצים לכל מחיצה (JSON)
- [x] מצאי APK: חבילה, מיקום, הרשאות, sharedUserId, priv-app – `tools/apk_inventory.py`

## שלב 2 – שרשרת אתחול ואימות
- [x] preloader → lk → tee → vbmeta → boot
- [x] vbmeta: מה מאומת, באילו מפתחות, איזה דגלים
- [x] fstab: מחיצות, דגלי avb/verity
- [ ] ramdisk ו-first stage init
- [x] גרף init.rc: שירותים, טריגרים, properties – `tools/init_rc.py`

## שלב 3 – גרף אפליקציות ותלויות
- [x] אפליקציות חובה של PackageManager – `tools/boot_roles.py`
- [x] privapp-permissions מול מניפסטים
- [ ] ספריות משותפות, uses-library, sharedUserId
- [ ] הגדרות framework-res שמפנות לחבילות
- [~] חיזוי: "מה יקרה אם אמחק X" – גרסה ראשונה: `DELETE_IMPACT.md`

## שלב 4 – שכבות עמוקות
- [ ] SELinux, APEX, overlays, HAL של vendor

## שלב 5 – אתר תיעוד
- [ ] אתר סטטי בעברית (RTL), חיפוש, גרפים, עמוד לכל רכיב
- [ ] פרסום ב-GitHub Pages

## שלב 6 – השוואה בין רומים
- [ ] רום מקורי (restore) כבסיס
- [ ] השוואה לרומים מותאמים: מה הוסר והמערכת עדיין עולה
