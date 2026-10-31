# Qin F21 Pro (GTR) – מה יקרה אם אמחק?

נוצר אוטומטית מ-`boot_roles.json`, `apks.json`, `init_graph.json` (כלים: `tools/boot_roles.py`, `tools/apk_inventory.py`, `tools/init_rc.py`).

**אזהרה:** אלה תחזיות תיאורטיות לפי קוד האתחול של אנדרואיד 11. רמת הביטחון מצוינת לכל שורה.

## 1. אפליקציות שבלעדיהן המערכת נכנסת ללולאת אתחול

| תפקיד | חבילה ברום | נתיב | ביטחון | למה |
|---|---|---|---|---|
| installer | com.android.packageinstaller | system:/system/priv-app/PackageInstaller/PackageInstaller.apk | high | `PackageManagerService.getRequiredInstallerLPr(): 'There must be exactly one installer'` |
| uninstaller | com.android.packageinstaller | system:/system/priv-app/PackageInstaller/PackageInstaller.apk | high | `PackageManagerService.getRequiredUninstallerLPr(): 'There must be exactly one uninstaller'` |
| permission_controller | com.android.permissioncontroller | system:/system/apex/com.android.permission/priv-app/PermissionController/PermissionController.apk<br>system:/system/priv-app/MtkPermissionController/MtkPermissionController.apk | high | `PackageManagerService.getRequiredPermissionControllerLPr(): 'There must be exactly one permission controller'` |
| shared_library android.ext.shared | android.ext.shared | system:/system/app/ExtShared/ExtShared.apk | high | `PackageManagerService.getRequiredSharedLibraryLPr(): 'Missing required shared library'` |
| services_extension (ExtServices) | android.ext.services | system:/system/apex/com.android.extservices/priv-app/ExtServices/ExtServices.apk | medium | `PackageManagerService.getRequiredServicesExtensionPackageLPr()` |
| settings_provider | com.android.providers.settings | system:/system/priv-app/MtkSettingsProvider/MtkSettingsProvider.apk | high | `ActivityManagerService.installSystemProviders(): Settings.* reads fail in system_server` |
| framework (android) | android | system:/system/framework/framework-res.apk | high | `framework-res.apk is package 'android' - resources of system_server` |

## 2. אפליקציות שבלעדיהן המערכת עולה – אבל חסר משהו

| תפקיד | חבילה ברום | מה יקרה |
|---|---|---|
| package_verifier | — חסר כבר עכשיו | getRequiredButNotReallyRequiredVerifierLPr() returns null |
| home / launcher | android, com.android.launcher3, com.android.managedprovisioning, com.android.provision, com.android.settings | ActivityTaskManager.startHomeActivity(): no HOME -> black screen after boot animation |
| system_ui | com.android.systemui | SystemServer.startSystemUi(): no status bar / navigation / lock screen |
| setup_wizard | com.android.provision | getSetupWizardPackageNameImpl() returns null; device may stay 'not provisioned' |
| telephony (com.android.phone) | com.android.phone | persistent app; without it there is no calling/SMS |

הערה: ברום הזה **אין package verifier** (בדרך כלל Google Play) – והמערכת עולה. זו הוכחה שהתפקיד הזה לא חובה.

## 3. כללי priv-app (privapp-permissions)

`ro.control_privapp_permissions=enforce`: כל אפליקציה בתיקיית `priv-app` שמבקשת הרשאה מיוחסת (privileged) שלא מופיעה בקובץ `privapp-permissions-*.xml` – **עוצרת את האתחול**.

- ברום הזה: 0 הפרות (כל ה-priv-apps מכוסות).
- המשמעות: **הוספה** של אפליקציה ל-`priv-app` בלי להוסיף XML מתאים = לולאת אתחול. **מחיקה** של אפליקציה לא מפרה את הכלל (שורות XML מיותרות לא מזיקות).

## 4. אפליקציות persistent

אם אחת מהן קורסת שוב ושוב – RescueParty מסלים עד מסך "Can't load Android system" ב-recovery. מחיקה שלהן לא גורמת לקריסה ישירה, אבל אפליקציה אחרת שתלויה בהן עלולה לקרוס.

`android`, `com.android.cellbroadcastservice`, `com.android.networkstack`, `com.android.networkstack.tethering`, `com.android.nfc`, `com.android.ons`, `com.android.phone`, `com.android.se`, `com.android.systemui`, `com.mediatek.entitlement.o2`, `com.mediatek.security.service`, `com.mediatek.smartratswitch.service`

## 5. שירותי init קריטיים

אם שירות `critical` קורס יותר מ-4 פעמים ב-4 דקות – init מאתחל ל-bootloader/recovery. מחיקת הקובץ שלהם = לולאה:

- `charger` – `/charger` (מוגדר ב-`ramdisk:init.recovery.hlthchrg.rc`)
- `hwservicemanager` – `/system/bin/hwservicemanager` (מוגדר ב-`system:system/etc/init/hwservicemanager.rc`)
- `lmkd` – `/system/bin/lmkd` (מוגדר ב-`system:system/etc/init/lmkd.rc`)
- `servicemanager` – `/system/bin/servicemanager` (מוגדר ב-`system:system/etc/init/servicemanager.rc`)
- `ueventd` – `/system/bin/ueventd` (מוגדר ב-`vendor:etc/init/hw/meta_init.rc`)

## 6. שירותים מוגדרים שהקובץ שלהם חסר – והמערכת עדיין עולה

ברום הזה 26 שירותי init מצביעים על קובץ שלא קיים. רובם שירותי מצב מפעל/META. זו ראיה ששירות **לא קריטי** בלי קובץ – רק נרשם כשגיאה ביומן:

- `akmd8963` → `/system/bin/akmd8963`
- `bt_dump` → `/vendor/bin/bt_dump`
- `cmmb` → `/system/bin/cmmbsp`
- `conninfra_loader` → `/vendor/bin/conninfra_loader`
- `connsyslogger` → `/system/bin/connsyslogger`
- `dualmdlogger` → `/system/bin/dualmdlogger`
- `emdlogger1` → `/system/system_ext/bin/emdlogger1`
- `emdlogger2` → `/system/bin/emdlogger2`
- `emdlogger3` → `/system/bin/emdlogger3`
- `emdlogger5` → `/system/bin/emdlogger5`
- `emdlogger6` → `/system/bin/emdlogger6`
- `loghidlsysservice` → `/system/bin/loghidlsysservice`
- `loghidlvendorservice` → `/vendor/bin/loghidlvendorservice`
- `md_minilog_util` → `/vendor/bin/md_minilog_util`
- `mdlogger` → `/system/bin/mdlogger`
- `msensord` → `/system/bin/msensord`
- `osi` → `/system/bin/osi`
- `permission_check` → `/vendor/bin/permission_check`
- `pppd_gprs` → `/system/bin/pppd_dt`
- `pppoe_wlan0` → `/vendor/bin/launchpppoe`
- `remosaic_daemon` → `/vendor/bin/remosaic_daemon`
- `spm_script` → `/vendor/bin/spm_loader`
- `vendor_flash_recovery` → `/vendor/bin/install-recovery.sh`
- `viarild` → `/vendor/bin/viarild`
- `volte_md_status` → `/system/vendor/bin/volte_md_status`
- `wifi_dump` → `/vendor/bin/wifi_dump`

## 7. sharedUserId – תלות בין אפליקציות

אפליקציות עם אותו sharedUserId רצות באותו מזהה משתמש. `android.uid.system` משותף ל-framework עצמו – לכן אפליקציות כאלה רצות עם הרשאות מערכת.

- `android.uid.system` (20): android, com.android.deskclock, com.android.dynsystem, com.android.inputdevices, com.android.keychain, com.android.localtransport, com.android.location.fused, com.android.providers.settings, com.android.server.telecom, com.android.settings, com.android.wallpaperbackup, com.duoqin.inputmethod, com.duoqin.systemupdate, com.mediatek, com.mediatek.factorymode, com.mediatek.location.lppe.main, com.mediatek.ppl, com.mediatek.security.service, com.mediatek.simprocessor, com.wapi.wapicertmanager
- `android.uid.phone` (10): com.android.mms.service, com.android.ons, com.android.phone, com.android.providers.telephony, com.android.stk, com.mediatek.capctrl.service, com.mediatek.gba, com.mediatek.ims, com.mediatek.smartratswitch.service, com.mediatek.telephony
- `android.media` (5): com.android.mtp, com.android.providers.downloads, com.android.providers.downloads.ui, com.android.providers.media, com.android.soundpicker
- `android.uid.networkstack` (4): com.android.cellbroadcastservice, com.android.networkstack, com.android.networkstack.permissionconfig, com.android.networkstack.tethering
- `android.uid.shared` (4): com.android.calllogbackup, com.android.providers.blockednumber, com.android.providers.contacts, com.android.providers.userdictionary
- `android.uid.bluetooth` (1): com.android.bluetooth
- `android.uid.nfc` (1): com.android.nfc
- `android.uid.se` (1): com.android.se
- `android.uid.calendar` (1): com.android.providers.calendar
- `android.uid.mms` (1): com.android.mms
- `android.uid.shell` (1): com.android.shell
- `com.android.emergency.uid` (1): com.android.emergency
- `android.uid.systemui` (1): com.android.systemui
