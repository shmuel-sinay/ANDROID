# מדריך: הוספה והסרה של תכונות דרך Overlay (RRO)

> שיטה לשינוי התנהגות המערכת **בלי לפרק ולחתום מחדש APK** — דריסת ערכי משאבים.
> חל על M36 Plus (אנדרואיד 13, MT6765). האימות (AVB) פעיל ברום הזה — ראו `BOOT_CHAIN.md`.

## העיקרון
כמעט כל תכונה במערכת נשלטת ע"י **משאב** (resource): ערך `bool`, `integer`, `string` או `array`.
במקום לשנות את האפליקציה עצמה, בונים **Runtime Resource Overlay (RRO)** — חבילת APK קטנה שרק
*דורסת* את הערך. המערכת טוענת אותה מעל האפליקציה המקורית.

הסריקה העמוקה מצאה **11,808 מתגים כאלה** ב-202 האפליקציות (ראו עמוד "מתגי תצורה" באתר, או `resources.json`).

## איך בונים overlay (שלד)
```xml
<!-- AndroidManifest.xml -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.myoverlay">
  <overlay android:targetPackage="com.android.systemui"
           android:isStatic="true" android:priority="1"/>
  <application android:hasCode="false"/>
</manifest>
```
```xml
<!-- res/values/config.xml : הערך הדורס -->
<resources>
  <bool name="config_showBatteryPercentOnStatusBar">false</bool>
</resources>
```
בונים, חותמים (מפתח platform לא חובה ל-RRO סטטי), ומניחים ב-`/product/overlay/`.
האימות פעיל, אז מניחים ב-partition שנכלל ב-vbmeta המתאים, או מכבים אימות קודם.

## דוגמה 1: הסרת אייקון משורת הסטטוס
- סדר האייקונים מוגדר ב-`framework-res` במערך `config_statusBarIcons` (שמות "slot").
- SystemUI חושף **109 מתגים** הקשורים לשורת הסטטוס (ראו `ui_knobs.json`), למשל:
  - `config_showBatteryPercentOnStatusBar` — אחוז סוללה.
  - `config_statusBarShowNumber` — מספר על אייקון.
- **להסרת אייקון מסוים:** דורסים ב-overlay של `com.android.systemui` את ה-string שמגדיר את ה-slot ל-ריק, או מכבים את ה-`bool` המתאים. אם אין מתג ייעודי — דורסים את `config_statusBarIcons` עצמו ומסירים את ה-slot מהרשימה.

## דוגמה 2: הסרת שורה ממסך ההגדרות
- `com.android.settings` חושף **734 מתגים**.
- כל מסך הגדרות בנוי מ-`PreferenceScreen` ב-XML תחת `res/xml/` (למשל `network_and_internet.xml`).
- שורה מוסתרת ע"י:
  1. דריסת ה-`bool` של אותה שורה (רבות מוגנות ב-`config_show<Feature>` או `config_<feature>_available`), או
  2. הסרת ה-feature מ-`framework-res` / sysconfig (אם השורה תלויה ב-system feature — ראו `apks.json` → uses-feature), או
  3. overlay שמחליף את קובץ ה-`res/xml/` של המסך.

## איך למצוא את המתג הנכון
1. פותחים את העמוד "מתגי תצורה" באתר, מחפשים את החבילה.
2. או ב-`resources.json`: `apks[<path>].knobs` — שם המתג, הסוג, והערך הנוכחי.
3. מצליבים עם `apks.json` (uses-feature, uses-library) כדי לוודא שאין תלות נוספת.

## רמת ביטחון
- רשימת המתגים וערכיהם: **ודאי** (נשלף מה-APK עצמו ב-aapt).
- איזה מתג שולט בדיוק באיזו שורה/אייקון: **דורש אימות** — חלק מהשמות מפורשים, חלק דורשים קריאת הקוד של האפליקציה.
- לא נבדק על מכשיר.
