# תלות: מתקין החבילות (PackageInstaller) — M36 Plus

> קוד מפורק מתוך `system/framework/services.jar` של M36 Plus (androguard).
> חבילה ברום: `com.google.android.packageinstaller`
> (שונה משם החבילה ב-F21/GTR, שם זו `com.android.packageinstaller`)
> נתיב: `/system/priv-app/GooglePackageInstaller/GooglePackageInstaller.apk`

זהו תרגיל מלא בשיטה שביקשת: **לכל בדיקה, לבדוק אם יש בדיקה נוספת שסומכת עליה, ועוד
אחת, עד שאין יותר.** נמצאו **שתי שכבות נפרדות** בקוד, לא אחת. כל שלב כאן מתועד עד הסוף.

## שכבה 1: שתי הבדיקות ש"חייבות" installer/uninstaller (מפילות אתחול)

זהה למה שנמצא ב-F21 (ראו ההסבר המלא שם): בבנאי של `PackageManagerService`,
`getRequiredInstallerLPr()` ו-`getRequiredUninstallerLPr()` דורשות **בדיוק אפליקציה אחת**
שמגיבה ל-`INSTALL_PACKAGE`/`UNINSTALL_PACKAGE`. אפס או שתיים: `RuntimeException`,
‏`system_server` קורס, לולאת אתחול.

**נטרול:** לגרום לשתי המתודות להחזיר `null` במקום לזרוק, ולמחוק את `services.odex/vdex/art`
התואמים (אחרת ART עלול להמשיך להריץ את הקוד הישן מה-AOT המהודר מראש).

## שכבה 2: האם יש בדיקה נוספת שתלויה בקיום ה-installer?

חיפשתי בכל הקוד (init.rc, SELinux seapp_contexts, service_contexts) אזכור ישיר לשם
החבילה `com.google.android.packageinstaller` או לקובץ שלה, מעבר לבדיקת
PackageManagerService. **לא נמצא אף הפניה נוספת** (לא שירות init, לא כלל SELinux ייעודי).

אבל הסריקה האוטומטית (`boot_guards.py`) כן מצאה **מתודה שלישית** בקוד שעלולה להיראות
קשורה: `getInstantAppInstallerLPr()`. פירקתי אותה כדי לדעת בוודאות מה היא עושה:

```java
// PackageManagerService.getInstantAppInstallerLPr(), מקוצר
Intent i = new Intent().setAction("android.intent.action.INSTALL_INSTANT_APP_PACKAGE");
List matches = computer.queryIntentActivitiesInternal(i, MIME, flags, 0);
// מסנן רק פעילויות עם הרשאת INSTALL_PACKAGES
if (matches.size() != 0) {
    if (matches.size() != 1)
        throw new RuntimeException("There must be at most one ephemeral installer; found " + matches);
    return matches.get(0).getComponentInfo();
}
return null;   // <-- אפס תוצאות: לא זורק, רק מחזיר null
```

**התשובה המדויקת:** הבדיקה הזו זורקת שגיאה רק אם יש **שתיים או יותר** אפליקציות
שמגיבות ל-`INSTALL_INSTANT_APP_PACKAGE`. אם אין אף אחת (המצב אחרי מחיקת ה-installer),
היא פשוט מחזירה `null` בלי לזרוק. **זו לא תלות נוספת שחוסמת מחיקה.** המסקנה: שכבה 2
כבר "בטוחה מעצמה" מול המצב של אפס, ולא צריך לנטרל אותה בנפרד.

## שכבה 3: מי עוד קורא לתוצאה (לא רק את הבדיקה, גם מי משתמש בה)

כמו ב-F21: `getPackageInstallerPackageName()` חושף את השם החוצה, ונקרא מ-
`PackageInstallerSession.makeSessionActiveLocked` כדי לפתוח למשתמש את מסך "אשר התקנה".
אם השם `null`: הקריאה `intent.setPackage(null)` לא קורסת, רק לא ימצא מי שיציג את המסך.
**אין כאן שכבה רביעית** שצריך לבדוק; זה הסוף של השרשרת.

## מסקנה מעשית
כדי למחוק את `com.google.android.packageinstaller` ב-M36 Plus בלי לקרוס:
1. לנטרל את שתי המתודות בשכבה 1 (installer + uninstaller) ב-`services.jar`.
2. למחוק את `services.odex/vdex/art`.
3. שכבה 2 (instant-app installer) ושכבה 3 (שימוש בשם) לא דורשות כלום נוסף.

**מה יפסיק לעבוד:** התקנת APK מתוך הטלפון, מסך "הסר אפליקציה". **מה ימשיך:** `adb install`.

## רמת ביטחון
שכבה 1: **ודאי** (זהה ל-F21, קוד זהה ב-AOSP). שכבה 2: **ודאי**, פורקה ישירות מ-M36
עצמו (לא הנחה, קוד אמיתי). שכבה 3: **גבוהה**. לא נבדק בפועל על מכשיר.
