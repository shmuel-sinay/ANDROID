# הסרה מדויקת: אייקון בשורת הסטטוס / שורה בהגדרות (M36 Plus)

> נתונים מתוך `ui_deep.json` — 1,586 שורות הגדרות ב-254 מסכים, ו-35 slots של שורת הסטטוס.
> שיטה: Overlay (RRO) — ראו `deps/overlays.md`. האימות פעיל ברום — ראו `BOOT_CHAIN.md`.

## שורת הסטטוס — 35 האייקונים לפי סדר
סדר ה-slots (מ-`config_statusBarIcons` ב-framework-res):

`no_calling, call_strength, alarm_clock, rotate, headset, data_saver, ime,
sync_failing, sync_active, nfc, tty, speakerphone, cdma_eri, data_connection,
phone_evdo_signal, phone_signal, secure, managed_profile, cast, screen_record,
vpn, bluetooth, camera, microphone, location, mute, volume, zen, ethernet,
wifi, hotspot, mobile, airplane, battery, sensors_off`

### איך מסירים אייקון מסוים
לכל אייקון יש שם slot. שלוש דרכים, מהפשוטה לעמוקה:
1. **Blocklist של SystemUI** (ללא עריכת קבצים): ההגדרה הנסתרת
   `icon_blacklist` ב-Settings.Secure מקבלת רשימת slots מופרדים בפסיק.
   למשל להסתרת ה-NFC וה-VPN: `settings put secure icon_blacklist "nfc,vpn"`.
   זו הדרך הנקייה — לא דורסת קבצים, שורדת צריבה של super (נשמר ב-userdata/settings).
2. **Overlay על framework-res**: דורסים את `config_statusBarIcons` ומשמיטים את ה-slot.
3. **Overlay על SystemUI**: חלק מהאייקונים יש להם `bool` ייעודי (ראו למטה).

### מתגי SystemUI רלוונטיים לשורת הסטטוס
(מתוך הסריקה — `ui_deep.json` → `status_bar.systemui_statusbar_knobs`; וב-`resources.json` יש 109 מתגים)
- `config_showBatteryPercentOnStatusBar` — אחוז סוללה.
- `config_statusBarShowNumber` — מספר על אייקון.

## מסך ההגדרות — 1,586 שורות
כל שורה נשלפה מקובץ `res/xml/<screen>.xml` ב-MtkSettings, עם ה-`key` שלה.

### איך מסירים שורה מסוימת
1. מאתרים את השורה ב-`ui_deep.json` → `settings.rows` לפי `title` או `key`,
   ורואים באיזה `file` (מסך) היא ומה ה-`key`.
2. **הדרך הנקייה (controller):** רוב השורות ב-MtkSettings מנוהלות ע"י
   `BasePreferenceController` שבודק `getAvailabilityStatus()`. חלק נשלטות ע"י
   `config_*_available` / `config_show*` ב-framework או ב-Settings עצמו — דורסים ב-overlay ל-false.
2. **הדרך הישירה (overlay על res/xml):** overlay שמחליף את קובץ המסך ומסיר את ה-`<Preference>`.
3. **הסרה לפי feature:** אם השורה תלויה ב-system feature (ראו `apks.json` → uses-feature
   ו-`xml_config.json` → sysconfig), הסרת ה-feature מסתירה את השורה אוטומטית.

### 25 המסכים עם הכי הרבה שורות
ראו `ui_deep.summary.json` → `top_screens` (למשל מסכי נגישות, רשת, תצוגה).

## חשוב
- כל שינוי שנשמר ב-Settings (דרך 1 של שורת הסטטוס, ו-secure/global keys) — **שורד צריבה של super**,
  כי הוא ב-userdata. שינוי שדורס קובצי מערכת — נמחק ב-"Format and Download".
- רמת ביטחון: רשימת ה-slots וה-keys **ודאית** (נשלפה מהקבצים). איזה controller בדיוק שולט בכל
  שורה — חלק דורש קריאת הקוד של MtkSettings. לא נבדק על מכשיר.
