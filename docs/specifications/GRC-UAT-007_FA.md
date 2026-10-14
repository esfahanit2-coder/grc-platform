# برنامه آزمون پذیرش و شواهد (UAT) — GRC Platform

> **شناسه:** GRC-UAT-007 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`؛ `pilot-20261013-r1`  
> **مراجع:** [PRD](GRC-PRD-001_FA.md)، [SRS](GRC-SRS-002_FA.md)، [RTM](GRC-RTM-006_FA.md)
>
> **مهم:** مشاهده UI و اجرای محلی روی WSL2 جایگزین گواهی امنیت/تأیید مشتری یا Host مستقل نمی‌شود.

## ۱. شرایط آزمون
- فقط داده ساختگی؛ هیچ داده حساس مشتری، استاندارد محدود دارای حق نشر یا رمز در Evidence عمومی قرار نگیرد.
- مشخصات: Host/OS/Browser/Version/Source SHA/Release Digest/Operator/Test Date ثبت شود.
- دسته وضعیت: `PASS` / `FAIL` / `BLOCKED` / `NOT-RUN` / `N/A(reason)`.
- هر PASS نیازمند Evidence مثل Response سانسورشده، Screenshot مجاز، Log و Hash فایل خروجی است.
- «کد وجود دارد» یا «Service Running» به‌تنهایی اثبات کارکرد یا کارایی نیست.
- هنگام آزمون بین چند Tenant، تنها داده ساختگی به‌کار رود و خروجی Cross-Tenant نباید به Issue عمومی نشت کند.
- هر سناریو نتیجه Expected/Observed و Issue/PR نقص داشته باشد.
- آزمون Restore تخریبی تنها در محیط بازیابی مستقل و با اجازه رسمی، نه روی محل تنها نسخه داده.

## ۲. سناریوهای اصلی

### UAT-001 — نصب و سلامت
**پیش‌شرط:** Host مجاز، بسته امضاشده، کلید عمومی مورد اعتماد، TLS، DNS، بدون Secrets در Repo.  
**مراحل:**
1. تأیید SHA/Manifest/signature.
2. نصب Imageهای نسخه دقیق، بدون `pull`/Build هنگام Install.
3. اجرای Preflight و Startup سرویس‌ها.
4. بررسی Gateway/Backend/Migrations/Health.
5. ثبت وضعیت Beat/Worker/Queue/Backup و Django Deploy Warnings.
**Expected:** خدمات سالم، API `/health/live` و `/ready` = 200 و `operational_status` با معیار مصوب؛ هشدارهای مهم ثبت/رفع.
**Baseline فعلی:** Local install/start و HTTPS PASS؛ عملیات در خروجی اولیه `critical` و دو هشدار Django؛ **کل UAT هنوز PASS نیست**.

### UAT-002 — هویت و Bootstrap
**مراحل:** ساخت Tenant/ادمین از مسیر رسمی؛ رمز قوی؛ Login؛ MFA مطابق Policy؛ Logout؛ Session expiration؛ Refresh؛ Invalid Password و Rate Limit.  
**Expected:** تمام عملیات حساس مجاز، رمز در Prompt مخفی و نه Log؛ کاربر ناشناس Redirect/Login؛ Session نامعتبر داده‌ای نبیند.
**Baseline:** Bootstrap و Login کاربر آزمایشی موفق؛ Anonymous Dashboard API=401؛ UI Root Redirect، MFA و Logout کامل هنوز اثبات نشده است.

### UAT-003 — دارایی و ریسک مرتبط
**مراحل:** ایجاد `TEST-ASSET-001`، Refresh و بررسی؛ ایجاد `TEST-RISK-001` با همان Unit و Asset؛ Refresh؛ مشاهده پیوند در UI؛ ویرایش مجاز ریسک/دارایی؛ تلاش Unit/Asset نامعتبر.  
**Expected:** FK Tenant/Unit معتبر، Display صحیح، ثبت و ویرایش Audited، Reject اتصال نامعتبر.
**Baseline:** ایجاد و Persistence دارایی، ایجاد ریسک و FK مستقیم سالم؛ ویرایش ریسک UI ندارد (#183)؛ **Partial**.

### UAT-004 — Methodology، Evaluation و RTP
**مراحل:** ایجاد روش 5×5، مشاهده Active/Default؛ ارزیابی Inherent با likelihood=3 و impact=4؛ Refresh و انتظار Score 12 و Level High با Threshold نمونه؛ ثبت Residual؛ Treatment+Action؛ Export RTP DOCX.  
**Expected:** Backend Score و History مستقل، Threshold معتبر؛ خروجی RTP مرتبط و بازشدنی.
**Baseline:** `POST /api/v1/risk-methodologies/` HTTP 400؛ دلایل Response هنوز بررسی نشده؛ **BLOCKED**.

### UAT-005 — کنترل، شواهد و آزمون
**مراحل:** ایجاد Common Control، نگاشت به دو Requirement داخلی، ایجاد Implementation، بارگذاری فایل تست در Quarantine، اسکن واقعی، لینک Evidence، تعریف ControlTest/Run.  
**Expected:** کنترل مشترک، Data Scope سالم، Download فقط پس از Clean، نتیجه آزمون تاریخ‌دار؛ Evidence در محدوده مجاز reusable.
**Baseline:** NOT-RUN؛ اسکنر واقعی باید موجود/مجاز باشد.

### UAT-006 — ارزیابی انطباق تا CAPA
**مراحل:** ورود بسته مجاز غیرمحدود، قفل FrameworkVersion، ساخت Assessment/Items با Snapshot، پاسخ/Review، ایجاد Finding و Action، ارزیابی اثر تغییر نسخه.  
**Expected:** Score/Progress مستقل، Requirement Snapshot و Audit محفوظ، Scope و Permission درست.
**Baseline:** NOT-RUN؛ محتوای رسمی حقوقی باید جداگانه تأیید شود.

### UAT-007 — ممیزی و سند
**مراحل:** Plan، Engagement، Workpaper، Finding، Action؛ Draft Document و Version؛ Review/Approve با کاربران مجاز؛ Audit Report.  
**Expected:** History، تفکیک Owner/Reviewer، خروجی قابل بازکردن.
**Baseline:** NOT-RUN.

### UAT-008 — پیش‌نویس SoA و کنترل مرز تصویب
**مراحل:** ایجاد SoA Draft روی FrameworkVersion قفل‌شده مجاز، Included/Excluded با توجیه، Readiness، ارسال درخواست Review، تغییر محتوای Draft و آزمون Stale Conflict، بررسی نبود تأیید/امضای غیرمجاز.  
**Expected:** Draft واضح، Review history، رد وضعیت `approved` و عدم ادعای Formal Attestation.
**Baseline:** NOT-RUN؛ «SoA Approved» ممنوع.

### UAT-009 — گزارش/فایل
**مراحل:** انتخاب RTP/Findings/Actions/Executive و Draft SoA، Preview، خروجی‌های اعلام‌شده PDF/DOCX/XLSX/CSV، بازکردن فایل و بررسی تاریخ/RTL/Scope؛ تلاش خروج خارج Scope.  
**Expected:** فایل معتبر، محتوای درست، محرمانگی، نام‌گذاری/سربرگ و هشدار Draft در SoA.
**Baseline:** NOT-RUN؛ تاریخ شمسی مشکل شناخته‌شده #182.

### UAT-010 — کنترل مجوز و حسابرسی
**مراحل:** دو Tenant با داده متفاوت، دو Unit، Admin و User محدود؛ List/Detail/Export/API با UUID حدسی؛ POST/PATCH/DELETE نامجاز؛ بررسی Audit events و Chain.  
**Expected:** 401/403/404 مطابق Policy، نشت 0، Change مجاز Audit شده، Export محدود.
**Baseline:** تنها Anonymous Dashboard GET=401؛ **آزمون جامع NOT-RUN**.

### UAT-011 — Backup/Restore و Upgrade
**مراحل:** Backup DB/Object/Config، بررسی Manifest، Restore تخریبی روی محیط دوم، تطبیق تعداد/Checksum رکوردها، اندازه‌گیری RPO/RTO، شبیه‌سازی شکست و Rollback.  
**Expected:** Restore کامل، سازگاری Version، زمان‌های **واقعاً اندازه‌گیری‌شده** و Evidence مستقل.
**Baseline:** NOT-RUN؛ نبود رکورد Backup در Health اولیه گزارش شده.

### UAT-012 — AI و Connector
**مراحل:** AI محلی با Model واقعی و No-Egress؛ آزمون Source Permissions و Prompt Injection؛ ثبت/رد پیشنهاد؛ قطع Provider. سپس Connectorهای مجاز AD/FortiGate/Veeam/Tenable و Evidence دارای provenance و خطای Sync.  
**Expected:** AI هیچ Authoritative State بدون Human Review تغییر ندهد؛ Connector شواهد تولید کند نه نتیجه Compliance.
**Baseline:** AI Enabled=0 در نصب فعلی؛ Live Connector آزمون نشده؛ `NOT-RUN`.

### UAT-013 — فارسی، شمسی و دسترس‌پذیری
**مراحل:** واردکردن تاریخ جلالی پایان ماه/کبیسه، ذخیره، Refresh، مشاهده در لیست/Detail/Export؛ بررسی تبدیل ISO روز دقیق؛ Keyboard navigation و RTL همراه IP/UUID.  
**Expected:** بدون جابه‌جایی روز، بدون مخلوط‌شدن LTR/RTL و با خطای تاریخ نامعتبر.
**Baseline:** FAIL برای تاریخ شمسی (#182).

## ۳. سناریوهای منفی مشترک
- Duplicate Code در Tenant؛ Duplicate Submit.
- User غیرفعال/Role منقضی.
- Asset متعلق به Tenant یا Unit دیگر.
- Risk Methodology بدون گزینه/Scale یا Formula نامعتبر؛ نمایش دقیق Field Error.
- Evidence منقضی/قرنطینه؛ دانلود ممنوع.
- Approval یا SoA روی نسخه تغییرکرده؛ 409.
- Export گزارشی با Scope خارج مجوز؛ منع نشتی.
- AI context دارای Prompt Injection یا Source ID مجعول.
- در زمان قطع Redis/Object Storage/DB، خطا قابل تشخیص و بدون ادعای موفقیت باشد.
- Backup Fail یا Beat heartbeat ثبت‌نشده، Status عملیاتی سبز نشود.

## ۴. قالب ثبت نتیجه
```text
Test ID:
Requirement ID:
Environment / Host / Browser:
Source SHA / Release Digest:
Date / Timezone:
Tester / Approver:
Prerequisites:
Inputs (synthetic):
Steps executed:
Expected:
Observed:
Result [PASS | FAIL | BLOCKED | NOT-RUN]:
Evidence links or hashes:
Issue/PR:
Retest date:
```

## ۵. Gate پذیرش پایلوت و مشتری

### Gate-Pilot
- نصب Signed موفق با Key تستی و حدود ادعا روشن.
- Golden Journey با داده ساختگی تا خروجی قابل بازکردن اجرا.
- حداقل نقص‌های Security/Authorization رد و P0ها اصلاح/ثبت شوند.
- خطاها و محدودیت‌ها آشکار باشند؛ BLOCKED جای PASS نگیرد.

### Gate-Customer (مجزا)
- مجوز قانوني منبع محتوا و حقوق بازتوزیع.
- TLS و Key Custody تحت کنترل رسمی مشتری/تأمین‌کننده.
- آزمون Host مستقل، Restore مخرب و RPO/RTO اندازه‌گیری‌شده.
- Security/Pentest sign-off و نبود Critical/High بدون تصمیم رسمی.
- Connector/AI واقعی فقط در صورت تعهد و Scope مصوب.
- UAT نقش‌های واقعی مشتری و صورتجلسه تصویب/محدودیت.

**تا تکمیل Gate-Customer، محصول «Pilot Candidate / pre-RC» است و نباید Production-Ready معرفی شود.**

## ۶. منابع و پیگیری
- گزارش نصب/آزمون: https://github.com/esfahanit2-coder/grc-platform/issues/161
- تاریخ شمسی: https://github.com/esfahanit2-coder/grc-platform/issues/182
- ویرایش ریسک: https://github.com/esfahanit2-coder/grc-platform/issues/183
- مستندات مرجع: `docs/FINAL_RELEASE_ACCEPTANCE.md`, `docs/DATACENTER_OPERATIONS.md`, `docs/field/72H_GRC_INSTALL_DELIVERY_FA.md`.
