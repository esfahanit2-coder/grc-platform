
# برنامه اضطراری ۷۲ ساعته تحویل GRC — تا ۱۵ اکتبر ۲۰۲۶ / ۲۳ مهر ۱۴۰۵

**هدف قابل قبول:** ارائه یک Pilot Candidate واقعی با قابلیت نصب روی لینوکس تحت کنترل مشتری و شواهد قابل‌ردیابی GitHub برای کد، بسته امضا، کارکرد هسته و بازیابی مصنوعی. **غیرقابل ادعا:** Production-Ready، گواهی انطباق، SoA تصویب‌شده، تست نفوذ مستقل، UAT واقعی مشتری، RPO/RTO اندازه‌گیری‌شده یا دریافت مجوز حقوقی استاندارد از روی CI.

## ۱. همین لحظه: توقف گسترش محدوده

- Freeze توسعه ویژگی‌های جدید ISO/COBIT/افتا، تأیید رسمی SoA، ماژول‌های اضافی و بازنویسی معماری.
- فقط رفع خطاهای P0 و P1 که مستقیماً جلوی نصب، کارکرد، خروجی یا امنیت را می‌گیرند.
- کد مرجع: یک Commit دقیق از main که CI کامل، Release Gate و آزمون‌های موقت را پاس کند؛ **Commit را قبل از نتیجه واقعی درج نکنید**.
- روی سرور آزمایشی، داده ساختگی و محتوای داخلی غیرمحرمانه استفاده شود. هیچ استاندارد دارای حق نشر یا Credential در GitHub عمومی یا لاگ CI قرار نمی‌گیرد.
- برای تحویل عملیاتی حتماً اختیار قانونی استفاده از بسته استاندارد و مسئول پشتیبانی روشن شود.

## ۲. راهکار سرور موقت، بدون خرید سرور دائمی

ریپازیتوری عمومی است. GitHub Actions به ازای هر Job یک Ubuntu Linux موقت می‌دهد و پس از اتمام آن را حذف می‌کند. workflow `.github/workflows/72h-ephemeral-install-rehearsal.yml` چهار آزمون را **به‌طور مستقل** اجرا می‌کند:

| Job | کارکرد | محدودیت صریح |
| --- | --- | --- |
| real-signed-core | اجرای اسکریپت امضا، بوت هسته واقعی Django/Postgres/S3 و بازیابی نمونه با داده ساختگی | محیط موقت، نه Host مشتری |
| signed-offline-package | رد امضای نامعتبر/دستکاری فایل و نصب آرشیو Imageهای کوچک ساختگی بدون نیاز به Registry هنگام نصب | خود Imageهای واقعی محصول در این Job بسته‌بندی نمی‌شوند |
| synthetic-db-objectstore-recovery | بازیابی PostgreSQL و S3 ساختگی روی Runtime موقت | RPO/RTO واقعی را اندازه نمی‌گیرد |
| encrypted-custody-smoke | رفت‌وبرگشت رمزنگاری با کلیدهای یک‌بارمصرف age | نه کنترل واقعی کلید مشتری و نه ۲ Host مستقل |

**آزمون سبز GitHub صرفاً نشان می‌دهد اسکریپت در همان ماشین موقت اجرا شده است.** بررسی عمر Job، زمان اجرا، پارتیشن دیسک و نتیجه هر Job ضروری است. عدم موفقیت یا قطع ارتباط Registry نتیجه BLOCKED/FAIL تلقی می‌شود، نه PASS.

گزینه مکمل، VPS ساعتی/چندروزه یا VM مجاز مشتری است. این گزینه برای آزمایش مستقل، HTTPS واقعی و پذیرش کاربر ترجیح دارد؛ مستلزم اقدام مالک حساب/میزبان است. دسترسی SSH، OTP یا رمز نباید در Issue عمومی یا گفتگو وارد شود. GitHub Codespaces ابزار توسعه است و جایگزین دیتاسنتر مشتری نیست.

## ۳. نقشه اجرایی روزانه

| بازه | اقدامات اصلی | معیار پایان |
| --- | --- | --- |
| روز اول: ۱۲ تا ۱۳ اکتبر | اطمینان از Main CI و Release Gate بعد از PR #156، اجرای تمام چهار Job موقت، تهیه فهرست نقص واقعی، Freeze P0/P1 | حداقل یک اجرای موفق یا گزارش صریح نقص هر Job، SHA معلوم |
| روز دوم: ۱۳ تا ۱۴ اکتبر | رفع خطاهای نصب/امنیت، بازاجرای چهار آزمون، بررسی مسیر Build/Sign/Verify و نصب آفلاین بسته واقعی توسط اپراتور مجاز روی میزبان قابل‌تهیه در صورت دسترسی | بسته/رویه امضا و Verify تست‌شده، گزارش B/U/R، هیچ blocker فنی CI باز |
| روز سوم: ۱۴ تا ۱۵ اکتبر | مرور نهایی Backend/Frontend، درخواست تأیید Release Gate، چک‌لیست تحویل، تست UI و سناریوی طلایی با داده ساختگی؛ نهایی‌کردن راهنما و قرارداد پذیرش پایلوت | Handoff دقیق با Commit، Digest/Manifest معتبر و مرز ادعا؛ وضعیت پذیرش خارجی BLOCKED تا ارائه شاهد واقعی |

زمان‌ها هدف‌گذاری‌اند نه جایگزین گزارش اجرا. هیچ اتوماسیونی نباید خودکار Release رسمی v1.0.0 یا گواهی ISO صادر کند.

## ۴. بسته نصب رسمی — مسیر فعلی پروژه را دوباره‌نویسی نکنید

مرجع: `docs/DATACENTER_OPERATIONS.md` و `scripts/datacenterctl`.

۱. روی ماشین سازنده مورد اعتماد با Checkout پاک و همان Commit تأییدشده، خروجی دقیق backend/frontend Imageها، ابزارهای Infrastructure Pin‌شده، SBOM و Security Evidence را با `scripts/offline-release-build.sh <version> <exact-source-ref>` بسازید.

۲. با Private Signing Key سازمان که **خارج از GitHub و CI عمومی** نگهداری می‌شود، از `scripts/offline-release-sign.sh` برای امضا و از `scripts/offline-release-verify.sh` برای اعتبارسنجی بسته و کلید عمومی مورد اعتماد استفاده کنید. کلید CI یک‌بارمصرف برای تست است، نه کلید توزیع واقعی.

۳. روی میزبان Linux رسمی: Docker Engine، Compose >=2.24.4، Git، Python >=3.12، OpenSSL، DNS/NTP و TLS، ذخیره‌سازی Backup جداگانه و ظرفیت بر اساس بار اندازه‌گیری‌شده لازم است. پورت اصلی 443 باشد؛ DB/Redis/S3/Backend به‌صورت پورت خارجی باز نشوند.

۴. فایل پیکربندی تولیدی با `scripts/server-pilot-env.py` تحت کنترل اپراتور ساخته می‌شود؛ از قالب نمونه بدون تغییر استفاده نشود. بعد از آماده‌شدن TLS و آدرس‌ها، مسیر استاندارد:

```bash
bash scripts/offline-release-apply.sh install \
  <signed-bundle.tar.gz> <trusted-release-public-key.pem> \
  /opt/grc <production-env-file>

cd /opt/grc/repository
CONFIRM_INSTALL=YES bash scripts/datacenterctl install

bash scripts/datacenterctl bootstrap \
  --tenant-code <customer-code> \
  --tenant-name "<customer-name>" \
  --admin-username <admin-login> \
  --admin-email <admin-email>

bash scripts/datacenterctl verify --json-out artifacts/datacenter-verification.json
```

رمز اولیه Administrator در Prompt امن دریافت می‌شود؛ Credential هرگز در Shell History یا لاگ قرار نگیرد.

۵. برای Backup واقعی: `bash scripts/datacenterctl backup <backup-name>`؛ سپس `bash scripts/datacenterctl recovery-preflight <backup-name>` به‌صورت صرفاً خواندنی. Restore تخریبی با `CONFIRM_RESTORE=YES bash scripts/datacenterctl restore <backup-name>` **فقط روی محیط بازیابی مجاز و با تأیید اپراتور/مالک داده** انجام شود. RPO/RTO را واقعاً اندازه بگیرید؛ از زمان اجرای GitHub Action تخمین نزنید.

## ۵. آزمون عملکردی حداقلی از مرورگر

- HTTPS / گواهی، صفحه Login، MFA، Admin و عضویت.
- Tenant A و Tenant B: نشت داده و IDOR ممنوع.
- ایجاد سازمان، Framework مجاز یا نمونه داخلی بدون حق نشر، کنترل مشترک و دارایی.
- ارزیابی ریسک و درمان، ارتباط کنترل، Assessment و Evidence امن، Finding و اقدام اصلاحی.
- صفحه Work Center، Task/Workflow، ممیزی، گزارش و داشبورد فارسی با Empty/Loading/Error State.
- پیش‌نویس SoA: انتخاب/استثنا با دلیل، رابطه درمان/شاهد، بازبینی مستقل، Stale 409 پس از تغییر؛ هیچ Approve/Sign/Publish یا صدور SoA رسمی وجود ندارد.
- Import/Export، گزارش چاپی، Audit Events، Backup/Restore و پایداری پس از Restart.
- Connector واقعی، محتوای ISO دارای مجوز و AI محلی در صورت نداشتن محیط مناسب به‌صورت «NOT TESTED / BLOCKED»، نه PASS، ثبت شوند.

## ۶. تعریف دقیق سند تحویل و ممنوعیت ادعای اضافی

برای هر آزمون، تاریخ، Commit، Run URL، تصویر Docker Digest، نتیجه واقعی PASS/FAIL/BLOCKED و مسئول/تاییدکننده مشخص باشد. لینک خام Customer Data، Secret یا کد استاندارد حق‌نشردار به GitHub عمومی داده نشود.

**غیرقابل چشم‌پوشی برای Production:** حقوق/محتوای استاندارد (#5)، سه Connector واقعی (#6 اگر در دامنه نسخه باشد)، نصب و بازیابی روی Host مستقل (#7)، تست امنیت مستقل (#8)، UAT/RTL واقعی (#42/#74)، معیارهای بسته تجاری (#44/#68)، تصویب انسانی و رسمی SoA در صورت فروش این قابلیت (#143/#151). وجود CI سبز به هیچ‌یک مجوز عبور نمی‌دهد.

## ۷. خروجی مورد انتظار تا ۱۵ اکتبر

نسخه قابل بررسی و نصب، راهنمای اجرایی، شواهد واقعی GitHub Actions، فهرست نواقص باقی‌مانده و راهنمای تحویل به اپراتور. اگر Server واقعی تا مهلت فراهم نشد، خروجی «**Deployable Pilot Candidate — customer-host installation and acceptance pending**» است، نه «آماده بهره‌برداری قطعی».

مسئول فنی و Product Owner باید یک تصمیم Go/No-Go جدا برای استفاده میدانی ثبت کنند. شروع آزمون UAT یا نصب روی محیط واقعی نیازمند مالک محیط و دسترسی‌های مورد تأیید اوست.
