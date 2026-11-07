# חסימת וידיאו ברמת המערכת, בלי רוט, בלי אפליקציה חיצונית (M36 Plus)

> מטרה: לחסום ניגון/פתיחת קבצי וידיאו למשתמש, באופן שתקף לכל אפליקציה (לא רק לדפדפן
> או לנגן אחד), בלי להסתמך על אפליקציית חסימה שרצה עם הרשאות רוט.

## העיקרון: לאנדרואיד יש שתי שכבות לפענוח וידיאו, לא אחת

כמעט כל אפליקציה (כולל וואטסאפ, דפדפנים, גלריה) לא "יודעת" לפענח וידיאו בעצמה.
היא פונה למסגרת המערכתית (MediaCodec), וזו בוחרת מפענח (decoder) מתוך **שתי רשימות
נפרדות** שקיימות ברום הזה. **חוסמים רק אחת, השנייה עדיין עובדת.**

### שכבה 1: מפענחי חומרה (vendor)
קובץ: `vendor/etc/media_codecs_c2.xml` (וגם `media_codecs_performance.xml`).
מפענחי הווידיאו שמוצהרים שם:
```
c2.mtk.avc.decoder      (H.264)
c2.mtk.hevc.decoder     (H.265)
c2.mtk.vp9.decoder
c2.mtk.mpeg4.decoder
c2.mtk.mpeg2.decoder
c2.mtk.h263.decoder
c2.android.avc.decoder
c2.android.hevc.decoder
c2.android.vp8.decoder
c2.android.vp9.decoder
c2.android.av1.decoder
c2.android.mpeg2.decoder
c2.android.mpeg4.decoder
c2.android.h263.decoder
```

### שכבה 2: מפענחי תוכנה (APEX, גיבוי של גוגל)
קובץ: `apex_extracted/com.google.android.media.swcodec/etc/media_codecs.xml`,
מגובה ע"י ספריות אמיתיות שקיימות ברום:
```
libstagefright_soft_avcdec.so
libstagefright_soft_hevcdec.so
libstagefright_soft_mpeg2dec.so
libstagefright_soft_mpeg4dec.so
libstagefright_soft_vpxdec.so   (VP8/VP9)
```
אותו APEX **מצהיר מחדש** על `c2.android.avc.decoder`, `c2.android.hevc.decoder` וכו׳.
כלומר: גם אם מוחקים/מרוקנים את `media_codecs_c2.xml` של ה-vendor (שכבה 1), המערכת
עדיין תמצא את אותם שמות מפענח דרך ה-APEX (שכבה 2), ב-**תוכנה**, בלי צורך בחומרה.

## מה צריך לעשות, בפועל, כדי שזה באמת ייחסם

נטרול אמיתי דורש **את שתי השכבות יחד**:

1. ב-`vendor/etc/media_codecs_c2.xml` וב-`media_codecs_performance.xml`: למחוק/להעיר את
   כל אלמנט `<MediaCodec>` ששמו מכיל `avc`, `hevc`, `vp8`, `vp9`, `av1`, `mpeg2`, `mpeg4`,
   `h263` ו**-decoder** (לא encoder, כדי לא לפגוע בצילום).
2. באותו האופן ב-`apex_extracted/com.google.android.media.swcodec/etc/media_codecs.xml`
   (הקובץ בתוך ה-payload של ה-APEX `com.google.android.media.swcodec.apex`, ראו
   `tools/apex_unpack.py` באטלס לאיך לפתוח ולסגור APEX מחדש).
3. **מומלץ גם**: לנטרל את קבצי ה-`.so` עצמם (שינוי שם/מחיקה של
   `libstagefright_soft_*dec.so` הרלוונטיים בתוך ה-APEX), כגיבוי אם משהו עדיין מצליח
   לטעון אותם ישירות בלי לעבור דרך רשימת ה-XML.

## התלות הבאה בשרשרת (עוד "דור")

לאחר שינוי קובץ בתוך APEX, צריך לחתום ולארוז אותו מחדש (`apex_payload.img` + המניפסט),
אחרת `apexd` (השירות שטוען APEX-ים בעלייה) עלול לדחות אותו כפגום. זו בדיוק הדוגמה
לעיקרון שביקשת: **כל נטרול עלול לעורר בדיקה נוספת במעלה השרשרת** (כאן: apexd בודק את
תקינות ה-APEX), וצריך לבדוק גם אותה.

## מה זה לא פותר (כנות לגבי המגבלה)

- **אפליקציה שמביאה מפענח וידיאו משלה בתוך ה-APK** ממשיכה לעבוד, כי היא לא עוברת דרך
  MediaCodec בכלל. הפעם כן נבדק: `tools/bundled_decoders.py` פותח כל אחת מ-202
  האפליקציות ובודק עם `nm -D` את חתימות הפונקציות האמיתיות בכל ספריית `.so`, לא רק
  מה שהאפליקציה מצהירה. נמצאו **שתי אפליקציות** עם מפענח עצמאי אמיתי:
  `preinstall/vlc.apk` (VLC מלא, כולל H.264/MKV) ו-`preinstall/AmazonMusic.apk`
  (ספריית libavcodec אמיתית, `avcodec_decode_audio4`). פירוט מלא ופתרון מוצע:
  ראו `deps/video_gatekeeper_design.md`.
- וידיאו שמוצג כרצף תמונות (GIF/WebP אנימטיבי) לא עובר דרך MediaCodec כלל, לא נחסם בזה.

## רמת ביטחון
רשימות המפענחים ושמות הקבצים: **ודאיות**, נשלפו ישירות מהרום (`xml_config.json`,
`native_deps.json`). שרשרת apexd ודרישת החתימה מחדש: **גבוהה** (התנהגות AOSP מתועדת).
לא נבדק בפועל על מכשיר.
