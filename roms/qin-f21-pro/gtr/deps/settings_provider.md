# תלות: ספק ההגדרות (SettingsProvider)

> קוד מפורק מתוך `services.jar` ו-`framework.jar` של הרום הזה.
> חבילה ברום: `com.android.providers.settings` (authority: `settings`), רצה בתהליך `system` עם `sharedUserId=android.uid.system`.

## סוג התלות: עקיפה (קריסת NullPointerException, לא בדיקה מפורשת)

אין בקוד שורה שאומרת "SettingsProvider חובה". הקריסה נובעת מכך שקוד המערכת **מניח** שהוא קיים.

## השרשרת

### 1. `ActivityManagerService.installSystemProviders()`
נקרא מ-`SystemServer.startOtherServices()`, מוקדם באתחול:

```java
List providers = generateApplicationProvidersLocked(processNames.get("system", 1000));
// מסנן ספקים שאינם אפליקציית מערכת
mSystemThread.installSystemProviders(providers);   // מתקין את ספקי התהליך "system"
mSystemProvidersInstalled = true;
mConstants.start(mContext.getContentResolver());   // ← קורא הגדרות מיד
mCoreSettingsObserver = new CoreSettingsObserver(this);
mActivityTaskManager.installSystemProviders();
mDevelopmentSettingsObserver = new DevelopmentSettingsObserver(this);
SettingsToPropertiesMapper.start(resolver);
mOomAdjuster.initSettings();
RescueParty.onSettingsProviderPublished(mContext);
```

רק ספקים של אפליקציות שרצות **בתהליך `system`** מותקנים כאן. SettingsProvider הוא כזה.
אם הוא נמחק – הרשימה פשוט לא כוללת אותו, ואין שגיאה **בשלב הזה**.

### 2. כל קריאה ל-`Settings.Global/Secure/System.get*()`
`android.provider.Settings$NameValueCache.getStringForUser()` (framework.jar):

```java
IContentProvider cp = mProviderHolder.getProvider(cr);   // acquireProvider("settings") → null
...
Bundle b = cp.call(pkg, tag, authority, mCallGetCommand, name, args);  // ← אין בדיקת null
```

`ContentProviderHolder.getProvider()` מחזיר את מה ש-`acquireProvider("settings")` החזיר – `null` כשהספק לא קיים.
הקריאה `cp.call(...)` על `null` זורקת `NullPointerException`. בלוקי ה-catch שם תופסים רק `RemoteException`.

### 3. התוצאה
`mConstants.start()` / `CoreSettingsObserver` קוראים הגדרות ← NPE בתוך system_server ← קריסה ← zygote מאתחל ← **לולאת אתחול**.

## האם אפשר לבטל?
**לא בקלות.** עשרות שירותים קוראים הגדרות (ActivityManager, WindowManager, PowerManager, Wi-Fi, ...).
ביטול התלות ידרוש מימוש חלופי של ספק `settings` – כלומר, להחזיר אותו בצורה אחרת. המסקנה המעשית: **לא למחוק**.

## אפליקציות שתלויות בו גם כן
כל אפליקציה שקוראת `Settings.*` – כלומר כמעט כולן. בלעדיו גם הן יקרסו.

## רמת ביטחון
- השרשרת והקוד: **ודאי** (מהרום).
- ההנחה ש-`acquireProvider` מחזיר null לספק שאינו קיים: **גבוהה** (התנהגות AOSP מתועדת).
- לא נבדק על מכשיר.
