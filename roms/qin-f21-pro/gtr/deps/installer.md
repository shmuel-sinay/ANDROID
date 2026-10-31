# תלות: המתקין (PackageInstaller)

> קוד מפורק מתוך `system/framework/services.jar` של הרום הזה (androguard).
> חבילה ברום: `com.android.packageinstaller` – `/system/priv-app/PackageInstaller/PackageInstaller.apk`

## למה מחיקה שלו מפילה את האתחול

`PackageManagerService.<init>` – הבנאי של מנהל החבילות, שרץ מוקדם מאוד ב-`SystemServer.startBootstrapServices` – קורא:

```java
mRequiredInstallerPackage   = getRequiredInstallerLPr();
mRequiredUninstallerPackage = getRequiredUninstallerLPr();
```

### `getRequiredInstallerLPr()` (כפי שהוא ברום)

```java
Intent i = new Intent("android.intent.action.INSTALL_PACKAGE");
i.addCategory("android.intent.category.DEFAULT");
i.setDataAndType(Uri.parse("content://com.example/foo.apk"),
                 "application/vnd.android.package-archive");
List matches = queryIntentActivitiesInternal(i, MIME, 0x1C0000 /*MATCH_SYSTEM_ONLY|DIRECT_BOOT_*/, 0);
if (matches.size() != 1)
    throw new RuntimeException("There must be exactly one installer; found " + matches);
if (!matches.get(0).activityInfo.applicationInfo.isPrivilegedApp())
    throw new RuntimeException("The installer must be a privileged app");
return matches.get(0).getComponentInfo().packageName;
```

### `getRequiredUninstallerLPr()`

```java
Intent i = new Intent("android.intent.action.UNINSTALL_PACKAGE");
i.setData(Uri.fromParts("package", "foo.bar", null));
ResolveInfo r = resolveIntent(i, null, 0x1C0000, 0);
if (r == null || mResolveActivity.name.equals(r.getComponentInfo().name))
    throw new RuntimeException("There must be exactly one uninstaller; found " + r);
return r.getComponentInfo().packageName;
```

### מה בדיוק נבדק – 4 תנאים
1. קיימת **בדיוק אחת** פעילות מערכת שמגיבה ל-`INSTALL_PACKAGE` עם `content://` ו-MIME של APK.
   – אפס **או שתיים** = קריסה. (התקנת מתקין נוסף כאפליקציית מערכת עם אותו intent-filter תפיל גם היא!)
2. האפליקציה הזו חייבת להיות **priv-app** (בתיקיית `priv-app`).
3. קיימת פעילות שמגיבה ל-`UNINSTALL_PACKAGE` עם `package:`.
4. התשובה ל-(3) לא יכולה להיות מסך "בחר אפליקציה" (`ResolverActivity`) – כלומר שוב: בדיוק אחת.

`RuntimeException` בבנאי של PackageManagerService ← `system_server` קורס ← zygote מאתחל אותו ← אותה קריסה ← **לולאת אתחול** (אנימציית האתחול לא נגמרת).

## מי משתמש בתוצאה (אם נבטל את הבדיקה)

נבדק בהצלבה על כל `services.jar` – כל מי שקורא את השדות:

| שדה | נקרא ב- | האם בטוח ל-`null` |
|---|---|---|
| `mRequiredInstallerPackage` | `getPackageInstallerPackageName()` | מחזיר `null` |
| | `canSuspendPackageForUserInternal` | כן – `name.equals(null)` מחזיר false |
| | `handlePackagePostInstall` | כן – יש בדיקת `!= null` לפני שליחת broadcast |
| `getPackageInstallerPackageName()` | `PackageInstallerSession.makeSessionActiveLocked` | לא קורס: `intent.setPackage(null)`. אבל בקשת "אישור התקנה" לא תמצא מי שיציג אותה |
| `mRequiredUninstallerPackage` | `canSuspendPackageForUserInternal` | כן |
| | `isCallerAllowedToSilentlyUninstall` | כן – בדיקת `!= null` |

## מסקנה – איך מבטלים את התלות

**שינוי מינימלי:** ב-`services.jar`, לגרום ל-`getRequiredInstallerLPr` ול-`getRequiredUninstallerLPr` להחזיר `null` במקום לזרוק.

לפי הניתוח למעלה, אף קורא בתוך system_server לא ייפול על `null`.

**מה יפסיק לעבוד:**
- התקנה מתוך אפליקציות (קובץ APK שנפתח מקבצים/דפדפן) – אין מי שיציג את מסך האישור.
- הסרת אפליקציה דרך ממשק "הסר".

**מה ימשיך לעבוד:** `adb install` / `pm install` (לא דורשים אישור משתמש), עדכונים שקטים של אפליקציות מערכת.

**חשוב לביצוע בפועל:**
- `services.jar` מגיע עם קבצי AOT מוכנים: `framework/oat/arm64/services.odex`, `services.vdex`, `services.art`.
  אם משנים את ה-jar ולא מוחקים אותם – ART עלול לדחות אותם ולהריץ מה-jar, או (אם ה-checksum לא נבדק כמצופה) להמשיך להריץ את הקוד הישן. הדרך הבטוחה: למחוק את שלושתם אחרי השינוי.
- ברום זה האימות כבוי (ראה `BOOT_CHAIN.md`), כך ששינוי ב-system לא ייחסם על ידי dm-verity.

## רמת ביטחון
- הקוד: **ודאי** – נלקח ישירות מהרום.
- רשימת הקוראים: **גבוהה** – הצלבה סטטית; קריאה דרך reflection לא הייתה מתגלה.
- ההשפעה בזמן ריצה: **תיאורטית** – לא נבדקה על מכשיר.
