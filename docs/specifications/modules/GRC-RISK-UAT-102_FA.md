# سناریوها و معیارهای آزمون ماژول مدیریت ریسک — GRC Platform

> **شناسه:** GRC-RISK-UAT-102 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT  
> **وابسته به:** [Risk Functional Spec 101](GRC-RISK-101_FA.md) · [Master UAT](../GRC-UAT-007_FA.md)  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`، `pilot-20261013-r1`  
> **قواعد:** PASS فقط با مشاهده/اثبات بر نسخه واقعی. حالت `TO-BE` باید تا پیاده‌سازی و اجرای آزمون، `NOT-RUN` یا `BLOCKED` بماند.

## ۱. محیط و Fixtures

**داده آزمایشی:**
- Tenant A: `grc-pilot`، Tenant B: `grc-pilot-second` (تنها پس از ایجاد مجاز روی محیط آزمون مستقل).
- Unit A1: Root یا Unit آزمایشی مجاز؛ Unit A2 برای Scope Negative Tests.
- Admin: `pilotadmin`، Risk Manager A1، Risk Viewer A1، Risk Evaluator A1، Approval User A1 که Requester نیست؛ تمام کاربران تست، بدون رمز در Issue.
- Asset: `TEST-ASSET-001` با `title=سامانه آزمایشی مدیریت اسناد`؛ Risk: `TEST-RISK-001`.
- Methodology: `TEST-METHOD-5X5` یا نام فارسی یکتا؛ 1..5 و Threshold `1..4=low,5..9=medium,10..16=high,17..25=critical`.
- دو ControlImplementation با Unit همسان/متفاوت برای Test.
- تمام داده‌ها ساختگی و دارای شناسه Test؛ از محتوای واقعی محرمانه و استاندارد دارای حق نشر در CI عمومی استفاده نشود.

**الزامات شواهد برای هر Test:** `case_id, requirement_id, environment, source_sha, release_digest, timestamp/timezone, tester, request_status (redacted), expected, observed, screenshots/response-log/DB-assertion, result, issue_id`.

## ۲. مسیرهای مثبت

### RSK-TC-001 — ثبت و ماندگاری ریسک/دارایی
**نیازمندی:** FR-AST-001 / FR-RSK-001 / RSK-AC-01.  
**پیش‌شرط:** Tenant A و Asset Test با مالک فعال موجود.  
**مراحل:** در `/risks` ایجاد ریسک با Code/Title/Unit/Owner و Asset هم‌واحد؛ ذخیره؛ Reload؛ روی Code کلیک؛ نمایش Asset؛ بررسی FK بدون تغییر DB.  
**Expected:** 201 در POST، Risk در فهرست و Detail قابل دیدن، `asset_title` مطابق Asset، `asset_id` صحیح؛ Record پس از Restart پابرجا.  
**Baseline evidence:** Asset و Risk واقعاً ساخته و در DB ارتباط تأیید شده؛ UI لینک/نمایش prominent هنوز بررسی کامل نشده. **PARTIAL**.

### RSK-TC-002 — ویرایش امن ریسک
**نیازمندی:** FR-RSK-001 / RSK-AC-02 / #183.  
**مراحل:** از Detail روی Edit، prefill؛ تغییر Title و Scenario؛ Cancel یک‌بار و Save یک‌بار؛ Refresh؛ مقایسه Owner/Asset/Evaluations/ControlLinks؛ مشاهده Audit.  
**Expected:** PATCH موفق، مقادیر تغییرکرده پابرجا، پیوندها/تاریخچه حذف نشوند؛ کاربر فاقد `risk.manage` نتواند PATCH کند.  
**Baseline:** **BLOCKED — UI Edit موجود نیست.**

### RSK-TC-003 — ساخت Methodology ۵×۵
**نیازمندی:** FR-RSK-002 / RSK-AC-03.  
**مراحل:** `/risks/methodologies` → افزودن روش یکتا، تعیین 1..5، Formula product و Thresholdها → ذخیره → Refresh → مراجعه به Risk Detail → انتخاب روش.  
**Expected:** HTTP 201، نام و Status active در فهرست، روش در Combo ارزیابی؛ خطاها Field-level.  
**Baseline:** **FAIL/BLOCKED** در پایلوت: POST=400، Body هنوز بررسی نشده؛ بررسی علت با Network Response لازم.

### RSK-TC-004 — ارزیابی ذاتی و محاسبه قطعی
**نیازمندی:** FR-RSK-003 / RSK-AC-04.  
**مراحل:** روش فعال و مجاز → Risk Detail → Inherent → Likelihood=3,Impact=4,Rationale → Save → Refresh.  
**Expected:** 201، `score=12` (ممکن است در API `12.0000` باشد)، `level=high` با آستانه آزمایشی، Actor/Time ثبت و کارت ذاتی به‌روز.  
**Baseline:** **BLOCKED** به‌دلیل TC-003.

### RSK-TC-005 — تاریخچه ارزیابی‌های چندگانه
**نیازمندی:** FR-RSK-003 / RSK-AC-05.  
**مراحل:** ارزیابی دوم `residual: L=2,I=2`، سپس ارزیابی `residual: L=2,I=3`؛ Query/History/Latest.  
**Expected:** همه رکوردها باقی؛ Last Residual=6/medium؛ Inherent=12/high دست‌نخورده؛ کامل‌بودن جدول تاریخچه در TO-BE.  
**Baseline:** **NOT-RUN**؛ History کامل UX به توسعه نیاز دارد.

### RSK-TC-006 — کنترل و درمان و اقدام
**نیازمندی:** FR-RSK-004 / RSK-AC-07/08.  
**مراحل:** ControlImplementation مجاز به Risk link؛ Treatment reduce و Owner/Target → Action با DueDate → پیشرفت → RTP JSON/DOCX.  
**Expected:** ارتباط هم‌Tenant/Unit، Treatment/Action در Detail و RTP؛ داده و دسترسی صحیح؛ هیچ Accept خودکار RiskAcceptance ایجاد نشود.  
**Baseline:** **NOT-RUN**.

### RSK-TC-007 — ایجاد و تصویب اشتهای ریسک
**نیازمندی:** FR-RSK-005 / RSK-AC-09.  
**مراحل:** Appetite Draft با Code/Version/Owner/EffectiveFrom، Tolerance residual با سقف 9، Approve با شخص دیگری.  
**Expected:** سیاست Approved، تاریخ مؤثر صحیح، Owner نتواند Self-Approve کند، Draft بدونه Tolerance رد شود، Approved immutable باشد.  
**Baseline:** **NOT-RUN**.

### RSK-TC-008 — درخواست پذیرش داخل Tolerance
**نیازمندی:** FR-RSK-005 / RSK-AC-10.  
**مراحل:** Risk با Residual=6/medium و Policy سقف9 → Request با دلیل و تاریخ Review/Expiry → Approver مستقل Approve.  
**Expected:** Snapshot Score/Method type/Tolerance ثبت شود؛ Accepted Request به دلیل داشتن تأیید مؤثر شناخته شود؛ درخواست‌دهنده خود را تأیید نکند.  
**Baseline:** **NOT-RUN**.

### RSK-TC-009 — پذیرش خارج Tolerance با Override
**نیازمندی:** FR-RSK-005 / RSK-AC-11.  
**مراحل:** Residual=12 و سقف9 → Request با Exception Justification → Approve بدون `risk.accept.override` و سپس با Approver دارای مجوز و Decision Note.  
**Expected:** بدون override رد؛ با مجوز و توجیه/Note مناسب و تفکیک متقاضی/تأییدکننده قابل ثبت؛ Snapshot Score/Tolerance ثابت.  
**Baseline:** **NOT-RUN**.

### RSK-TC-010 — Supersession و انقضا
**نیازمندی:** FR-RSK-005 / RSK-AC-12.  
**مراحل:** یک Acceptance Approved جاری؛ تلاش Approval دوم بدون supersedes → سپس درخواست supersedes درست → بررسی تاریخ انقضا و `is_current`.  
**Expected:** پذیرش موازی رد، قبلی superseded، expired current نباشد، History باقی.  
**Baseline:** **NOT-RUN**.

### RSK-TC-011 — گزارش و فایل RTP
**نیازمندی:** FR-RPT-001 / RSK-AC-13.  
**مراحل:** تک‌ریسک `?format=json` و `?format=docx`، سپس مرکز گزارش `type=rtp` با Unit/Date/Status → Preview → خروجی مطابق Catalog → بازکردن فایل.  
**Expected:** ریسک، مالک، امتیاز، Treatment/Action صحیح؛ فایل بازشدنی، Scope معتبر، Audit Export، RTL فارسی در TO-BE.  
**Baseline:** **NOT-RUN**؛ کد DOCX ثابت انگلیسی است.

### RSK-TC-012 — رابط شمسی و گردش زمان
**نیازمندی:** FR-LOC-001 / RSK-AC-14 / #182.  
**مراحل:** ReviewDate/TargetDate/EffectiveFrom/ReviewOn/ExpiresOn را به شمسی وارد، ذخیره، Refresh، API ISO و چاپ بررسی شود؛ لبه پایان ماه، سال کبیسه و timezone.  
**Expected:** تاریخ معادل Gregorian درست بدون drift؛ نمایش شمسی، API ISO.  
**Baseline:** **FAIL برای نیاز شمسی** در فرم‌های فعلی.

### RSK-TC-013 — AI پیشنهاد غیرمقتدر
**نیازمندی:** FR-AI-001/002/003 / RSK-AC-15.  
**مراحل:** مدل محلی واقعی با Tenant A مجاز؛ Risk AI Analysis؛ پیشنهاد را Reject/Accept Review؛ بررسی Domain State؛ سپس Prompt Injection در Evidence مصنوعی.  
**Expected:** فقط Interaction/Suggestion، منبع صحیح و Scope؛ هیچ Risk Close/Accept خودکار؛ Prompt Injection بی‌اثر.  
**Baseline:** **NOT-RUN — AI خاموش است**.

## ۳. تست‌های منفی و کنترل مرزها

| TC | سناریوی منفی | Expected | وضعیت |
|---|---|---|---|
| RSK-NEG-01 | Risk دارای Asset از Tenant B | 4xx؛ هیچ Link | NOT-RUN |
| RSK-NEG-02 | Risk Unit A1 با Asset Unit A2 | 4xx؛ Asset mismatch | NOT-RUN |
| RSK-NEG-03 | Owner عضو غیرفعال Tenant | 4xx | NOT-RUN |
| RSK-NEG-04 | Methodology از Tenant دیگر | 4xx بدون افشای منبع | NOT-RUN |
| RSK-NEG-05 | L=7 یا I=-1 برای ۵×۵ | 4xx؛ **ممکن است برای 7 در AS-IS enforce نشود؛ Gap** | NOT-RUN |
| RSK-NEG-06 | Formula غیر product | 4xx معنادار، نه 500 | NOT-RUN |
| RSK-NEG-07 | Threshold همپوشان/دارای شکاف | Reject در TO-BE | NOT-RUN |
| RSK-NEG-08 | دو ارزیابی همزمان یا Double Submit | بدون تناقض؛ Policy Idempotency در TO-BE | NOT-RUN |
| RSK-NEG-09 | Risk PATCH بدون risk.manage | 403 | NOT-RUN |
| RSK-NEG-10 | Risk Export خارج Scope | رد بدون افشای داده | NOT-RUN |
| RSK-NEG-11 | RiskControl دارای CI از Unit دیگر | 4xx | NOT-RUN |
| RSK-NEG-12 | Self-Approve Appetite | 403 | NOT-RUN |
| RSK-NEG-13 | Approved Appetite Edit | 4xx | NOT-RUN |
| RSK-NEG-14 | Self-Approve Acceptance | 403 | NOT-RUN |
| RSK-NEG-15 | Acceptance با Inherent/Target | 400 | NOT-RUN |
| RSK-NEG-16 | Acceptance Approved دوم بدون Supersession | 400 | NOT-RUN |
| RSK-NEG-17 | Risk `accepted/closed` با PATCH بدون Workflow | رد در TO-BE؛ **Gap** | NOT-RUN |
| RSK-NEG-18 | Treatment Accept به‌دست submitter بدون مجوز approve مستقل | رد در TO-BE؛ **Gap SoD** | NOT-RUN |
| RSK-NEG-19 | expired Acceptance در داشبورد معتبر شناخته شود | باید False باشد | NOT-RUN |
| RSK-NEG-20 | RAG داده Tenant B یا دستور مخرب در Evidence | هیچ نشت/Tool action | NOT-RUN |

## ۴. شواهد موردنیاز در هر مرحله
1. **Request/Response:** HTTP Method/Path/Status/Body سانسورشده؛ هیچ Cookie/Authorization/Credential.
2. **Database:** Query فقط خواندنیِ FK/History یا Assertion تستی؛ بدون ویرایش دستی وضعیت.
3. **UI:** تصویر وضعیت معتبر و بعد از Refresh با User/Scope مشخص اما بدون اسرار.
4. **Audit:** Actor، Action، ObjectID، Time/RequestID و Chain Check (در صورت الزام).
5. **Documents:** نام، Size، SHA-256، شماره نسخه و آزمون بازشدن DOCX/PDF/XLSX.
6. **Decision:** approval/rejection/exception دارای Reviewer و Rationale.
7. **Negative Path:** در وضعیت شکست **هیچ Side Effect** یا تغییر غیرمجاز در Domain State.

## ۵. شکست مشاهده‌شده: بازتولید کنترل‌شده HTTP 400
- مسیر: `/risks/methodologies`؛ ارسال Name به دکمه `+ روش 5×5`.
- خروجی موجود از اپراتور: `POST /api/v1/risk-methodologies/` status=400؛ قبل از آن GET=401، `refresh=200`، سپس Methodology=400 دیده شده است.
- علت 400 از لاگ Request مشخص نیست؛ **Response Body باید بررسی شود**؛ هیچ نتیجه قطعی درباره Method Validation، CSRF، Tenant یا Token صادر نشود.
- تست پس از رفع: همان Tenant/Role/Browser و ردیابی Request ID؛ 201 و `GET` فهرست Active؛ Evaluation 3×4=12/high؛ Refresh و Export RTP.

## ۶. پروتکل نتیجه
```yaml
case_id: RSK-TC-003
requirement_ids: [FR-RSK-002]
release: pilot-20261013-r1
source_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
environment: Windows11_WSL2_Ubuntu-24.04_DockerDesktop
tester: pilot-operator
result: BLOCKED
observed: "POST /api/v1/risk-methodologies/ = HTTP 400"
expected: "201; active methodology visible in risk evaluation form"
evidence: "https://github.com/esfahanit2-coder/grc-platform/issues/161"
defect: "RISK-GAP-01"
retest: pending
```

**برای `PASS` باید شاهد واقعی پیوست شود؛ هیچ Test Case این سند صرفاً با تدوین‌شدن اجراشده محسوب نمی‌شود.**

## ۷. Gateهای پذیرش ماژول
### RISK-GATE-PILOT
- TC-001 تا TC-006 (به‌ویژه Method/Evaluation/RTP) در یک Build امضاشده جدید PASS.
- تمام NEG مربوط Tenant/Scope/Owner/Method/Role PASS؛ هیچ P0 بدون Fix.
- UX Create/Edit/Detail/روش ارزیابی و پیام خطا قابل استفاده؛ Jalali طبق دامنه R1 ممکن است با محدودیت مستند، نه به‌عنوان PASS شمسی.
- Audit و تاریخچه ارزیابی محفوظ.

### RISK-GATE-CUSTOMER
- Appetite/Acceptance مستقل، روش مصوب و نسخه ثابت، معیارهای رسمی خطر و Risk Closure.
- فارسی/Jalali و گزارش‌های چاپی با آزمون حقیقی.
- مجوزها و سیاست‌های مشتری، محتوا و بازیابی قابل اتکا.
- ممیزی امنیت و UAT نقش‌های واقعی؛ امضای Product/Security/QA/Customer.

---
**وضعیت امروز:** بخش‌هایی از TC-001 با شواهد پایلوت برقرار، TC-003 **FAIL/BLOCKED**، باقی تست‌ها اکثراً NOT-RUN؛ هیچ ادعای تکمیل کل Risk Lifecycle وجود ندارد.
