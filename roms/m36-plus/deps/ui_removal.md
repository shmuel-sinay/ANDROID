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

## בדיקה אמיתית על מכשיר (M36 Plus): `icon_blacklist` ל-wifi/mobile/cast

נסיון בפועל: `adb shell settings put secure icon_blacklist wifi,mobile,cast` — נשמר נכון
(`settings get` החזיר את הערך), אבל הסמלים **לא נעלמו** אחרי `adb shell am crash com.android.systemui`
(הפעלה מחדש מבוקרת של התהליך, לא reboot מלא).

פירקתי (androguard, DEX ישירות מ-`MtkSystemUI.apk` של M36 Plus) את כל שרשרת הקוד בפועל כדי
לשלול/לאשר כל חוליה:

| חוליה | ממצא | סטטוס |
|---|---|---|
| שמות ה-slots `wifi`/`mobile`/`cast` | אומתו מול `framework-res.apk` עצמו (`status_bar_wifi`, `status_bar_mobile`, `status_bar_cast`) — תואמים ל-100% | ✅ תקין |
| `TunerServiceImpl.addTunable` | רושם ContentObserver ל-`icon_blacklist`, **וגם קורא את הערך הנוכחי באופן סינכרוני** בזמן הרישום | ✅ תקין |
| `StatusBarIconControllerImpl`/`StatusBarSignalPolicy` constructors | שניהם קוראים ל-`addTunable` — כל עלייה מחדש של SystemUI אמורה לקרוא את הערך העדכני | ✅ תקין |
| `addSystemIcon`/`addHolder` (cast, type כללי) | מעביר כרטיס `blocked` נכון ל-`onCreateStatusBarIconView`, בונה View עם מצב מוסתר | ✅ תקין |
| `setWifiIndicators`/`setMobileDataIndicators` (wifi/mobile) | מחשבים `state.visible = !mHideWifi/mHideMobile` נכון | ✅ תקין |
| `StatusBarWifiView`/`StatusBarMobileView` — `initViewState`/`updateState` | שניהם קוראים ל-`setVisibility(GONE)` על הקונטיינר כש-`!visible` | ✅ תקין |
| layout של `StatusBarMobileView` | ה-`mMobileGroup` הוא הילד **היחיד**, רוחב `wrap_content` — הסתרתו קורסת לרוחב 0, אין "שארית" ויזואלית | ✅ תקין |
| שכבת OEM (`ISystemUIStatusBarExt`/`OpSystemUICustomizationFactoryBase`) | נבדק: טוען פלאגין `OP01/02/07/08/09/12/18/20SystemUI.apk` **רק אם קיים ברום** — נבדק ברום המלא, **אין אף קובץ כזה** → fallback ל-`DefaultSystemUIStatusBarExt` שהוא no-op מלא בכל המתודות | ✅ לא רלוונטי, שלילה מאומתת |
| `updateCast()` (cast ספציפית) | מציג אייקון cast רק כשיש מכשיר cast פעיל (`CastDevice.state` ∈ {CONNECTING, CONNECTED}) — אם שום דבר לא מוקרן כרגע, אין אייקון cast מוצג כלל ע"י המסלול הזה | ℹ️ הערה — אם "סמל ה-cast" שהמשתמש מתכוון אליו מוצג כל הזמן, הוא כנראה **לא** האייקון הזה |

**מסקנה:** בדקתי כל חוליה בשרשרת בקוד בפועל של M36 Plus — **אין שום באג בקוד ואין שכבת OEM
שמתערבת.** הערך נשמר נכון, וה-SystemUI אמור לקרוא אותו מחדש בכל עלייה. הגורם הנותר היחיד שלא
אומת: אולי `am crash` (הפעלה-מחדש "רכה" של התהליך) לא מספיק, וצריך **reboot מלא** למכשיר כדי
שהכל ייקרא נכון מהדיסק. זה הניסוי הבא שצריך לבצע בפועל על המכשיר — לא עוד ניחוש קוד.

רמת ביטחון על הממצאים בטבלה: **ודאית** — כל שורה נשלפה ונפורקה ישירות מה-DEX והמשאבים של
M36 Plus, לא מהנחה כללית על AOSP.
