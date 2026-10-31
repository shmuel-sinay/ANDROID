# Qin F21 Pro (GTR) – שרשרת אתחול ואימות

מקור: חבילת "f21 GTR". כל הממצאים נשלפו מהקבצים עצמם בכלים `tools/avb_info.py`, `tools/bootimg.py`, `tools/lp_unpack.py`.

## סדר האתחול (MediaTek MT6761)

```
BootROM (בתוך השבב)
  └─ preloader            ← preloader_k61v1_64_bsp.bin
       └─ lk (LittleKernel) ← lk.img  – בודק seccfg (מצב נעילה) ומאמת vbmeta
            ├─ tee        ← tee.img   – סביבת אבטחה (keymaster, gatekeeper)
            ├─ קושחות עזר: sspm, spmfw, scp, md1img (מודם)
            └─ boot       ← boot.img  – kernel + ramdisk (header v2, page 2048)
                 └─ first-stage init (מתוך ה-ramdisk)
                      ├─ קורא first_stage_ramdisk/fstab.mt6761
                      ├─ מרכיב system / vendor / product מתוך super (logical)
                      └─ עובר ל-/system/bin/init (system-as-root)
```

## AVB – מי מאמת את מי

| רכיב | אלגוריתם | מה הוא מכיל |
|---|---|---|
| `vbmeta_a` | SHA256_RSA2048 | שרשור (chain) ל-`vbmeta_system`, `vbmeta_vendor`, `boot` |
| `vbmeta_system_a` | SHA256_RSA2048 | hashtree ל-`system` ול-`product` |
| `vbmeta_vendor_a` | SHA256_RSA2048 | hashtree ל-`vendor` |
| `boot` | (chain, מפתח נפרד) | אמור לשאת footer עם hash |

כל אחד מהשלושה חתום במפתח אחר (טביעות SHA1 של המפתחות ב-`avb.json`).

## מה GTR שינה כדי שמערכת ערוכה תעלה

אלה בדיוק ה"מחסומים" שצריך לעקוף כשעורכים מחיצת מערכת:

1. **vbmeta_a – דגלים 3** (`HASHTREE_DISABLED` + `VERIFICATION_DISABLED`).
   lk ממשיך לאתחל גם כשהחתימות לא תואמות.
2. **fstab בלי דגלי avb** – לשורות system/vendor/product אין `avb=vbmeta_system` וכו'.
   first-stage init לא מפעיל dm-verity בכלל. (שכבת הגנה שנייה, בנוסף לסעיף 1.)
3. **system ו-vendor נבנו מחדש** – ה-footer שלהם לא חתום (`NONE`, avbtool 1.2.0),
   משתמש ב-sha1, והגודל שונה מהרשום ב-vbmeta_system:
   - system: חתום 1,706,852,352 ← בפועל 2,136,694,784
   - vendor: חתום 318,930,944 ← בפועל 352,223,232
4. **product לא שונה** – ה-root digest שלו זהה לזה שב-vbmeta_system (`f533725e…`).
5. **boot שונה** – אין לו footer של AVB, ובנוסף:
   - `os_patch_level` = 2099-12 (ערך מלאכותי; מונע חסימת rollback של keymaster)
   - cmdline מכיל `buildvariant=eng`
   - ramdisk: `ro.secure=0`, `ro.debuggable=1`, `ro.adb.secure=0` – adb עם הרשאות root ללא אישור

## מחיצות רגישות (לא נכללות בחבילה, לא נשמרות בריפו)
`nvram`, `nvdata`, `nvcfg`, `proinfo`, `protect1/2`, `persist`, `seccfg`, `frp` –
מכילות IMEI, כיול רדיו, מצב נעילה ו-FRP. fstab מרכיב חלק מהן תחת `/mnt/vendor/`.

## עוד בשלב זה
- ה-ramdisk כולל גם את מערכת ה-recovery (מכשיר A/B: recovery בתוך boot).
- `lib/modules/modules.load` ריק – אין מודולי ליבה ב-first stage.
- מפתחות GSI (q/r/s-gsi.avbpubkey) קיימים – המכשיר מוכן לקבל GSI חתום של גוגל.
