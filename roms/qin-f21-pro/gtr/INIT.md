# Qin F21 Pro (GTR) – מפת init

- 188 שירותים, 566 פעולות (`on ...`), 101 קבצי import

## מחלקות (class) – הסדר שבו הן מופעלות

`early_hal` ← `core` ← `hal` ← `main` ← `late_start`. `animation` = שירותים שצריכים לרוץ בזמן אנימציית האתחול.

| מחלקה | שירותים |
|---|---|
| main (67) | `PPLAgent`, `agpsd`, `atcid-daemon-u`, `audio-daemon`, `batterywarning`, `bugreportd`, `camerahalserver`, `camerapostalgo`, `cameraserver`, `clear-bcb`, `cmmb`, `connsyslogger`, `drm`, `dualmdlogger`, `dumpstate`, `dumpstatez`, `emdlogger1`, `emdlogger2`, `emdlogger3`, `emdlogger5`, `emdlogger6`, `fuelgauged_nvram`, `getgameserver`, `hostapd`, `idmap2d`, `incidentd`, `installd`, `iorapd`, `ipsec_mon`, `keystore`, `lbs_dbg`, `loghidlsysservice`, `loghidlvendorservice`, `mdlogger`, `mdnsd`, `media`, `media.swcodec`, `mediacodec`, `mediaextractor`, `mediametrics`, `mms-1-5`, `mnld`, `mtk.plpath.utils.link`, `mtpd`, `netd`, `nvram_daemon`, `osi`, `permission_check`, `pq-2-2`, `racoon`, `setup-bcb`, `statsd`, `storaged`, `thermal`, `thermald`, `thermalloadalgod`, `uncrypt`, `vendor.gsm0710muxd`, `vendor.ril-daemon-mtk`, `vendor.sensors-hal-2-0`, `vendor_flash_recovery`, `vtservice`, `wificond`, `wlan_assistant`, `wpa_supplicant`, `zygote`, `zygote_secondary` |
| (ללא) (47) | `akmd8963`, `apexd-bootstrap`, `apexd-snapshotde`, `blank_screen`, `boot-hal-1-0`, `boot-hal-1-1`, `boottrace`, `boringssl_self_test32`, `boringssl_self_test32_vendor`, `boringssl_self_test64`, `boringssl_self_test64_vendor`, `boringssl_self_test_apex32`, `boringssl_self_test_apex64`, `bpfloader`, `ccci3_mdinit`, `ccci_mdinit`, `ccci_rpcd`, `charger`, `cppreopts`, `derive_sdk`, `emsvr`, `emsvr_user`, `factory_no_image`, `fastbootd`, `gsid`, `health-hal-2-0`, `logd`, `logd-auditctl`, `logd-reinit`, `lpdumpd`, `md_minilog_util`, `meta_tst`, `msensord`, `pppd`, `pppd_gprs`, `pppoe_wlan0`, `recovery`, `spm_script`, `thermal_manager`, `tombstoned`, `update_verifier`, `update_verifier_nonencrypted`, `vendor.ccci3_fsd`, `vendor.ccci_fsd`, `wait_for_keymaster`, `wmt_launcher`, `wmt_loader` |
| core (31) | `adbd`, `apexd`, `audioserver`, `bootanim`, `bootlogoupdater`, `bt_dump`, `conninfra_loader`, `console`, `credstore`, `fuelgauged`, `gpu`, `lmkd`, `remosaic_daemon`, `servicemanager`, `stp_dump`, `surfaceflinger`, `terservice`, `ueventd`, `vendor.bip`, `vendor.ccci_rpcd`, `vendor.muxreport-daemon`, `vendor.volte_imcb`, `vendor.volte_stack`, `vendor.volte_ua`, `viarild`, `vndservicemanager`, `vold`, `volte_imsm_93`, `volte_md_status`, `wfca`, `wifi_dump` |
| hal (27) | `PPLAgent`, `atcid-daemon-u`, `bluetooth-1-0`, `emhidl_user`, `gnss_service`, `gpu-1-0`, `health-hal-2-1`, `hidl_memory`, `lbs_hidl_service`, `mtk_secure_element_hal_service`, `mtkcodecservice-1-1`, `nvram-hidl-1-1`, `power-hal-1-0`, `vendor.audio-hal`, `vendor.cas-hal-1-2`, `vendor.drm-clearkey-hal-1-3`, `vendor.drm-widevine-hal-1-3`, `vendor.gatekeeper-1-0`, `vendor.gralloc-4-0`, `vendor.hwcomposer-2-1`, `vendor.ir-hal-1-0`, `vendor.light-default`, `vendor.memtrack-hal-1-0`, `vendor.thermal-hal-2-0.mtk`, `vendor.usb-hal-1-1`, `vendor.vibrator-default`, `vendor.wifi_hal_legacy` |
| late_start (13) | `bugreport`, `fuse_usbotg`, `gatekeeperd`, `heapprofd`, `netdagent`, `rss_hwm_reset`, `traced`, `traced_perf`, `traced_probes`, `update_engine`, `usbd`, `vendor.epdg_wod`, `vendor.move_data_sh` |
| animation (6) | `bootanim`, `hwservicemanager`, `servicemanager`, `surfaceflinger`, `vendor.gralloc-4-0`, `vendor.hwcomposer-2-1` |
| early_hal (3) | `system_suspend`, `vendor.boot-hal-1-1`, `vendor.keymaster-4-0` |
| charger (2) | `health-hal-2-1`, `kpoc_charger` |

## שרשרת onrestart – מה מפיל מה

כשהשירות בעמודה הראשונה מתאתחל, init מאתחל איתו גם את השירותים שבעמודה השנייה:

| שירות | onrestart |
|---|---|
| `audioserver` | `restart vendor.audio-hal`<br>`restart vendor.audio-hal-4-0-msd`<br>`restart vendor.audio-hal-2-0`<br>`restart audio-hal-2-0` |
| `heapprofd` | `exec_background - nobody shell -- /system/bin/heapprofd --cleanup-after-crash` |
| `hwservicemanager` | `setprop hwservicemanager.ready false`<br>`class_restart main`<br>`class_restart hal`<br>`class_restart early_hal` |
| `netd` | `restart zygote`<br>`restart zygote_secondary` |
| `servicemanager` | `restart healthd`<br>`restart zygote`<br>`restart audioserver`<br>`restart media`<br>`restart surfaceflinger`<br>`restart inputflinger`<br>`restart drm`<br>`restart cameraserver`<br>`restart keystore`<br>`restart gatekeeperd`<br>`restart thermalservice` |
| `surfaceflinger` | `restart zygote` |
| `traced_probes` | `exec_background - nobody shell -- /system/bin/traced_probes --cleanup-after-crash` |
| `vendor.gralloc-4-0` | `restart surfaceflinger` |
| `vendor.hwcomposer-2-1` | `restart surfaceflinger` |
| `zygote` | `exec_background - system system -- /system/bin/vdc volume abort_fuse`<br>`write /sys/power/state on`<br>`restart audioserver`<br>`restart cameraserver`<br>`restart media`<br>`restart netd`<br>`restart wificond` |
| `zygote_secondary` | `restart zygote` |
