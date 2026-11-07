# החלפת ה-launcher לגמרי (M36 Plus)

## מה רץ היום
`com.android.launcher3` (בפועל: `MtkLauncher3QuickStep`), בנתיב
`/system/system_ext/priv-app/MtkLauncher3QuickStep/MtkLauncher3QuickStep.apk`.
הפעילות שרשומה כ-HOME: `com.android.launcher3.uioverrides.QuickstepLauncher`.

## בדיקת בטיחות: האם מותר למחוק אותו?
מתוך `removal_recipes.json`: **סיכון `degraded`, לא `bootloop`**. שום בדיקת אתחול
(boot_guards) לא תלויה בו, ושום אפליקציה לא חולקת איתו sharedUserId. המקור היחיד
שתלוי בקיום launcher הוא `ActivityTaskManager.startHomeActivity()`: אם אין אף
אפליקציה שמוכרת כ-HOME, המערכת עולה תקין אבל נשאר מסך שחור אחרי אנימציית האתחול.
**כלומר: זה בטוח להחליף, לא רק למחוק.**

## מי עוד מתחרה על להיות ה-launcher
בדקתי את כל 202 האפליקציות: רק 6 פעילויות ברום מצהירות על `category HOME`. חמש
מהן הן מסכים זמניים/מיוחדים, לא launcher אמיתי:

| חבילה | פעילות | מתי היא רלוונטית בפועל |
|---|---|---|
| `com.android.launcher3` | QuickstepLauncher | **זה ה-launcher האמיתי** |
| `com.android.settings` | FallbackHome | רק אם *אין בכלל* launcher מותקן, רשת ביטחון של אנדרואיד |
| `com.android.provision` | DefaultActivity | רק לפני שהגדרת המכשיר (setup wizard) הושלמה |
| `com.android.managedprovisioning` | PostEncryptionActivity | רק מיד אחרי הצפנה ראשונית |
| `com.google.android.apps.restore` | StubLauncherActivity | רק בזמן שחזור נתונים מפיקסל |
| `android` (framework) | SystemUserHomeActivity | מצב משתמשי-מערכת מיוחד, לא רלוונטי כאן |

**המשמעות:** אם מתקינים launcher חדש ומסירים את `MtkLauncher3QuickStep`, הוא
יהיה **היחיד** בפועל ביום-יום, בלי תיבת-בחירה (chooser) שתציק למשתמש.

## איך מחליפים, בפועל
1. **להסיר** את `MtkLauncher3QuickStep.apk` מ-`system_ext/priv-app/` (או רק
   להשבית את ה-component שלו דרך overlay, אם רוצים לשמור אותו כגיבוי לא פעיל).
2. **להתקין את ה-launcher החדש כ-priv-app** (לא אפליקציית משתמש רגילה), באותה
   שיטה: תיקייה תחת `system_ext/priv-app/<YourLauncher>/`, עם `AndroidManifest.xml`
   שמצהיר על אותו intent-filter:
   ```xml
   <activity android:name=".HomeActivity">
     <intent-filter>
       <action android:name="android.intent.action.MAIN"/>
       <category android:name="android.intent.category.HOME"/>
       <category android:name="android.intent.category.DEFAULT"/>
     </intent-filter>
   </activity>
   ```
3. **הרשאות שה-launcher המקורי ביקש** (ולכן כנראה גם שלך תצטרך, תלוי מה הוא עושה):
   `BIND_APPWIDGET`, ‏`WRITE_SECURE_SETTINGS`, ‏`STATUS_BAR`, ‏`STOP_APP_SWITCHES`,
   ‏`START_TASKS_FROM_RECENTS`, ‏`CONTROL_REMOTE_APP_TRANSITION_ANIMATIONS`,
   ‏`BROADCAST_CLOSE_SYSTEM_DIALOGS`, ‏`ALLOW_SLIPPERY_TOUCHES`. אלה **הרשאות
   privileged**, כלומר (כמו שראינו בכל האטלס) חובה להוסיף אותן לקובץ allowlist,
   אחרת `ro.control_privapp_permissions=enforce` יתפוס את זה ויפיל אתחול.
   קובץ האלואליסט המקורי של launcher3 נמצא ב-
   `system_ext/etc/permissions/com.android.launcher3.xml`. צריך קובץ מקביל חדש
   (`system_ext/etc/permissions/<your.package>.xml`) עם **רק** ההרשאות שה-launcher
   החדש שלך באמת צריך (לא חובה להעתיק את כל הרשימה, רק מה שבאמת בשימוש).
4. **אם ה-launcher החדש צריך לקרוא/לכתוב הגדרות מערכת** (כמו טפט, grid, מצב
   כהה): `WRITE_SECURE_SETTINGS` כבר ברשימה למעלה, מכסה את רוב המקרים.

## רמת ביטחון
מי מתחרה על HOME ואילו הרשאות privileged נדרשות: **ודאי**, נשלף ישירות מהרום.
ההמלצה הכללית (priv-app + allowlist): **גבוהה**, זהה לדפוס שכבר ראינו בכל שאר
האטלס (overlays, deps אחרים). לא נבדק בפועל על מכשיר.
