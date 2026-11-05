# מדריך ל-AI: איך לקרוא את תיעוד הרום הזה

מסמך זה נועד ל-**מודל AI** שמקבל את התיקייה הזו ונשאל שאלה כמו:
*"איך אני מוחק את החבילה X מהרום בלי שהמכשיר ייכנס ללולאת אתחול?"*

## המכשיר
Qin F21 Pro · MediaTek MT6761 · אנדרואיד 11 (SDK 30) · גרסת GTR.
האימות (AVB/dm-verity) כבוי ברום הזה — ראה `BOOT_CHAIN.md` — כך ששינוי קבצי מערכת לא ייחסם.

## הקובץ המרכזי לענות על "איך למחוק את X"
**`removal_recipes.json`** — לכל חבילה:
- `verdict` + `risk` — שורה תחתונה: `bootloop` / `critical` / `degraded` / `safe`.
- `roles_filled` — תפקידי מערכת שהחבילה ממלאת (אם היא ממלאת תפקיד חובה, מחיקתה מפילה אתחול).
- `boot_guards` — כל בדיקה בקוד שתזרוק שגיאה אם החבילה חסרה, עם:
  - `method` — המתודה המדויקת בקוד.
  - `distance_from_boot` — כמה קריאות מתחילת האתחול (קטן = קריסה ודאית יותר).
  - `neutralize` — **איך לנטרל את הבדיקה** כדי שהמחיקה לא תפיל אתחול.
  - `confidence` — `high` / `low` / `do-not-remove` / `unknown`.
- `shares_uid_with` — חבילות שחולקות sharedUserId; מחיקה עלולה לשבור אותן.

### דוגמה: מחיקת מתקין החבילות
`removal_recipes.json` → `com.android.packageinstaller`:
- `risk: bootloop` — אי אפשר פשוט למחוק.
- שתי בדיקות קריטיות: `getRequiredInstallerLPr`, `getRequiredUninstallerLPr`.
- נטרול (confidence high): לשנות את שתי המתודות ב-`services.jar` כך שיחזירו `null`, ולמחוק את `services.odex/vdex/art`.
- פירוט מלא עם הקוד עצמו: `deps/installer.md`.

## קבצים תומכים (אם צריך להעמיק)
| קובץ | מה יש בו |
|---|---|
| `boot_roles.json` | התפקידים שאנדרואיד דורש באתחול, ואיזו חבילה ממלאת כל אחד |
| `boot_guards.json` | כל בדיקת "חובה" בקוד המערכת (services/framework), עם מסלול מהאתחול |
| `apks.json` | כל 175 ה-APK: הרשאות, priv-app, sharedUserId, intent-filters |
| `init_graph.json` | 188 שירותי init: מי מפעיל את מי, מה קריטי |
| `native_deps.json` | גרף התלויות של 2,630 ספריות ‎.so (DT_NEEDED) |
| `framework_config_refs.json` | שמות חבילות שמקובעים ב-framework-res (config_*) |
| `avb.json` | שרשרת האימות: מה חתום, באילו מפתחות |
| `coverage.json` | כל 5,130 הקבצים ברום עם sha256 וסיווג — להוכחת כיסוי מלא |
| `deps/*.md` | ניתוח קוד מלא לרכיבים נבחרים (מתקין, ספק הגדרות) |

## חוקי בטיחות שה-AI חייב לשמור
1. **אל תסתמך רק על `verdict`.** בדוק גם `boot_guards` וגם `shares_uid_with` לפני שתמליץ למחוק.
2. `confidence: do-not-remove` = אל תמליץ למחוק את הרכיב, גם אם המשתמש מתעקש — אין נטרל בטוח.
3. `confidence: unknown` = יש בדיקה שלא נמצא לה נטרל אוטומטי; הפנה לקריאה ידנית של המתודה ב-`boot_guards.json`.
4. אחרי כל שינוי ב-jar/apk של מערכת: למחוק את קבצי ה-AOT התואמים (`.odex/.vdex/.art/.oat`), אחרת הקוד הישן עלול לרוץ.
5. כל התחזיות **תיאורטיות** (מניתוח סטטי של קוד אנדרואיד 11) ולא נבדקו על מכשיר. ציין זאת.
