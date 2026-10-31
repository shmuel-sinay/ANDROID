# התקדמות

## מקורות
- Qin F21 Pro – חבילת "f21 GTR" (תיקיית Drive מהפורום, סיסמת ארכיון: TripleU)
- הרום המקורי (spflash-f21pro-restore-1.0.8) – נעול להורדה בתיקייה; המשתמש יעלה עותק

## ממצאים – Qin F21 Pro (GTR)
- MT6761, אנדרואיד 11 (SDK 30), patch 2020-12-05
- fingerprint: Qin/full_k61v1_64_gms/k61v1_64_bsp:11/RP1A.200720.011/79:user/release-keys
- 48 מחיצות פיזיות (scatter), A/B – רק חריץ A צרוב
- super: system_a 2.1GB, vendor_a 355MB, product_a 163MB, system_b 37MB – כולן ext4
- system-as-root

- שרשרת אתחול ו-AVB מתועדות: `roms/qin-f21-pro/gtr/BOOT_CHAIN.md`
- GTR עוקף אימות בארבע שכבות: דגלי vbmeta, הסרת avb מ-fstab, system/vendor לא חתומים, boot ללא footer + ramdisk לא מאובטח

## שרת המשתמש
- Ubuntu 24.04 ARM64 (Oracle), 4 ליבות, 23GB RAM, 17GB פנוי, ללא KVM, sudo ללא סיסמה, docker קיים
- Remote Control רץ ב-~/android-docs (סביבת bridge). שירות קבוע – ממתין לאישור המשתמש בסשן השרת

- init: 188 שירותים, 5 קריטיים (ueventd, servicemanager, hwservicemanager, lmkd, charger); 26 שירותים מצביעים על קובץ חסר והמערכת עולה – `INIT.md`
- 175 APK, 12 persistent, privapp enforce ללא הפרות; אין package verifier (אין GMS) – `DELETE_IMPACT.md`

## הצעד הבא
- תלויות ברמת ספריות (.so) ו-uses-library, ותלות framework-res בשמות חבילות (config_*)
- SELinux: אילו דומיינים מגדירים שירותים קריטיים
- התחלת אתר התיעוד (GitHub Pages)
