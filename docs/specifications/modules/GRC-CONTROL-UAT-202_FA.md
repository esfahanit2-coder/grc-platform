# برنامه آزمون پذیرش تفصیلی مدیریت کنترل‌ها — GRC Platform

> **شناسه:** GRC-CONTROL-UAT-202 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT / NOT EXECUTED  
> **مرجع:** [GRC-CONTROL-201](GRC-CONTROL-201_FA.md) و [UAT مادر](../GRC-UAT-007_FA.md)  
> **Baseline Source:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`، آزمایش نصب‌شده `pilot-20261013-r1`.  
> **حد ادعا:** این سند Test Plan است، نه Test Report؛ آزمون‌های این فایل هنوز در مرورگر/Backend پایلوت اجرا نشده‌اند. مرور کد و ۴ تست موجود `backend/apps/controls/tests.py` بخشی از شواهد پیاده‌سازی‌اند، نه جایگزین UAT جامع.

## ۱. Fixtures و پیش‌نیازها

- دو Tenant ساختگی A و B با کاربران جداگانه، دو واحد A1/A2 در Tenant A؛ حساب‌های Creator، Owner، Operator، Mapping Reviewer، Test Executor، Test Reviewer، Auditor/ViewOnly.
- FrameworkVersion A1 و A2 با Requirement ساختگی دارای حق استفاده؛ برای تست Cross-Tenant نسخه B1 در Tenant B.
- کنترل ساختگی: `CTL-TEST-BACKUP-001`، یک Control Global فعال `GLOBAL-BACKUP`، دسته‌های محلی و مرجع.
- Implementation A1 شامل Owner/Unit و یک Implementation A2 برای کنترل مرز؛ Risk A1، AssessmentItem A1، Finding و Action مربوط.
- Test Plan «آزمون بازیابی فایل» با Method/Expected/Frequency/Owner؛ دو Run (Pass/Fail)، Evidence فایل کوچک مجاز با Hash و Status Clean در Environment دارای Scanner تأییدشده.
- No Secrets / no customer sensitive data / no copyrighted framework bodies در گزارش GitHub عمومی.
- پروفایل Production و Local Test باید جداگانه بررسی شوند؛ پیش‌فرض `EVIDENCE_REQUIRE_CLEAN_DOWNLOAD` در Production روشن و در محیط دیگر ممکن است خاموش باشد.
- همه شناسه‌های Data ساختگی را اپراتور پس از ایجاد از API مجاز دریافت کند؛ `id`های ثابت نمونه جای UUID واقعی نیستند.
- نتیجه هر Case: `PASS | FAIL | BLOCKED | NOT-RUN | N/A(reason)`. بارگذاری کد یا صرف دیدن Page مجوز PASS نیست.

## ۲. سناریوهای مثبت

### CTL-TC-001 — ایجاد Control Draft و Reload
**نیازمندی/AC:** FR-CTL-001، CTL-AC-01.  
**مراحل:** Login با `control.manage` → `/controls` → ایجاد `code,title,objective,description` → ذخیره → Refresh → GET `/controls/{id}/`.  
**Expected:** 201، `status=draft`، `tenant` از سرور؛ رکورد پس از Refresh پابرجا؛ Audit Create.  
**وضعیت:** NOT-RUN روی پایلوت.

### CTL-TC-002 — کنترل Global و Duplicate
**نیازمندی/AC:** FR-CTL-001، CTL-AC-02.  
**مراحل:** نمایش Global فعال → تلاش PATCH آن با ادمین Tenant (403) → `POST /controls/{id}/duplicate/` با Code جدید → Refresh.  
**Expected:** Global تغییر نکند؛ Clone متعلق به Tenant و Draft باشد؛ `Mapping.approved=false` حتی اگر منبع تأیید داشته؛ کد تکراری خطا دهد.  
**شاهد کد:** `ControlEngineTests.test_global_control_is_read_only_but_implementable`.  
**وضعیت:** NOT-RUN روی پایلوت.

### CTL-TC-003 — نگاشت یک کنترل به دو Framework
**نیازمندی/AC:** FR-FWK-003، FR-CTL-001، CTL-AC-03.  
**مراحل:** دو Requirement از نسخه‌های مختلف → ایجاد Mapping با `coverage,mapping_type,rationale,source` → نمایش `framework_code,requirement_code`.  
**Expected:** دو نگاشت مستقل و Draft؛ تعداد Frameworkها با معنای درست، Coverage نه Compliance.  
**شاهد کد:** `test_one_control_maps_to_multiple_frameworks`.  
**وضعیت:** NOT-RUN روی پایلوت.

### CTL-TC-004 — بازبینی و تصویب نگاشت
**نیازمندی/AC:** FR-CTL-001، CTL-AC-04.  
**مراحل:** Mapping جدید `approved=false` → Approve API با نقش Reviewer (در AS-IS `control.manage`) → بررسی Audit → PATCH Rationale → بررسی Reset Approved.  
**Expected AS-IS:** POST approve=200 و approved=true؛ PATCH approved=false با Audit.  
**Expected TO-BE:** Self-approval رد، `reviewed_by`, `approved_at`, Source Version ثبت و stale after changes.  
**شاهد کد:** `test_common_control_mapping_requires_explicit_audited_approval`.  
**وضعیت:** NOT-RUN روی پایلوت؛ بخش استقلال Reviewer هنوز Gap است.

### CTL-TC-005 — ایجاد Implementation هم‌Scope
**نیازمندی/AC:** FR-CTL-002، CTL-AC-05/06.  
**مراحل:** Control موجود، Unit A1، Owner فعال → Create `planned/not_assessed` → Refresh → Detail → دریافت شناسه Implementation.  
**Expected:** 201، `unique(tenant,control,unit)`، عدم ادعای اثربخشی یا انطباق؛ Owner/Unit صحیح.  
**وضعیت:** NOT-RUN روی پایلوت.

### CTL-TC-006 — تعریف ControlTest
**نیازمندی/AC:** FR-CTL-003، CTL-AC-07.  
**مراحل:** با `control.test.manage` → ایجاد Test برای Implementation A1 با Method/Expected/Frequency/Owner و Active → List و Retrieve.  
**Expected AS-IS:** API 201 و Persist؛ UI `/control-tests` فعلاً فقط List دارد.  
**Expected TO-BE:** فرم Create/Edit و اتصال به Control Detail با راهنمای روش آزمون.  
**وضعیت:** NOT-RUN / UI Full Flow BLOCKED.

### CTL-TC-007 — Run و تاریخچه
**نیازمندی/AC:** FR-CTL-003، CTL-AC-08.  
**مراحل:** POST `/control-tests/{id}/run/` با `result=partial`، Conclusion، JSON result_value و زمان اجرای معتبر → GET `/control-test-runs/` → Reload → Run دوم.  
**Expected AS-IS:** 201، `executed_by` از User، نتایج تاریخ‌دار مستقل؛ implementation.effectiveness به `partial` تغییر می‌کند.  
**Expected TO-BE:** Reviewer مستقل اعتبار Run را تأیید و Snapshot روش را حفظ کند؛ UI تاریخچه کامل.  
**وضعیت:** NOT-RUN روی پایلوت.

### CTL-TC-008 — Evidence و ارتباط به پیاده‌سازی و TestRun
**نیازمندی/AC:** FR-EVD-001/002، CTL-AC-10.  
**مراحل:** فایل ساختگی امن Upload → مشاهده SHA-256 و `pending` → Scanner مجاز → `clean` → ایجاد EvidenceLink به `control_implementation` و `control_test_run` → مشاهده Links.  
**Expected:** Scope/Classification مجاز، شمارنده Link، Download فقط طبق Clean Gate مصوب، هیچ Compliance Auto-Approved.  
**وضعیت:** NOT-RUN؛ به Scanner واقعی/محیط امن وابسته است.

### CTL-TC-009 — کنترل ↔ ریسک
**نیازمندی/AC:** FR-RSK-001/004، CTL-AC-12.  
**مراحل:** Risk A1 → RiskControl به CI A1 → مشاهده دوطرفه → Risk Treatment/Action → ارزیابی Residual مستقل بعد از کنترل.  
**Expected:** Unit و Tenant یکسان، بدون تغییر خودکار RiskEvaluation در زمان TestRun؛ گراف قابل ردیابی.  
**وضعیت:** NOT-RUN؛ Risk Methodology در پایلوت جاری HTTP 400 دارد (#161).

### CTL-TC-010 — Finding/Action از شکست آزمون
**نیازمندی/AC:** FR-FND-001/FR-ACT-001، CTL-AC-11.  
**مراحل:** ثبت Run `fail` + Evidence → Finding با Source Run/Implementation و Severity → Action با Owner/Due → Review Closure.  
**Expected:** مستقل از Run، Finding/Action با تصمیم انسان ثبت و گزارش شود؛ پایان Action به‌تنهایی Control Effective نشود.  
**وضعیت:** NOT-RUN؛ UI ترکیبی نیازمند تکمیل.

### CTL-TC-011 — داشبورد و گزارش کنترل
**نیازمندی/AC:** FR-RPT-001، CTL-AC-13.  
**مراحل:** داده Mixed (Draft/Implemented/NotAssessed/PassedUnreviewed/Fail/ExpiredEvidence) → فیلتر Unit/Framework → Preview/Export.  
**Expected TO-BE:** تفکیک تمام وضعیت‌ها، Timestamp/Scope/Source، هیچ Implied Compliance Score؛ PDF/DOCX/XLSX معتبر فقط پس از ساخت Template واقعی.  
**وضعیت:** NOT-RUN / گزارش‌های تخصصی هدف هنوز اثبات نشده‌اند.

### CTL-TC-012 — تقویم و خروجی فارسی
**نیازمندی/AC:** FR-LOC-001، CTL-AC-14.  
**مراحل:** تاریخ Implementation/Review/NextTest را به جلالی وارد، Save، GET Gregorian ISO و Refresh/Export بررسی کن.  
**Expected:** بدون یک روز drift؛ RTL و رشته‌های فنی LTR کنترل‌شده.  
**وضعیت:** GAP مشترک #182؛ NOT-RUN برای این ماژول.

### CTL-TC-013 — AI Mapping Advisory
**نیازمندی/AC:** FR-AI-001/002/003، CTL-AC-15.  
**مراحل:** Provider مجاز و Context دو Requirement → AI Mapping → Source IDs validation → رد/ویرایش/پذیرش پیشنهاد در مسیر مجاز → بررسی Mapping و Audit.  
**Expected:** AI به‌تنهایی `ControlRequirement.approved` یا Effectiveness را تغییر ندهد و اطلاعات غیرمجاز را بازیابی نکند.  
**وضعیت:** NOT-RUN؛ AI نصب محلی فعلاً خاموش است.

## ۳. سناریوهای منفی و حاکمیتی

| Test ID | ورودی/شرایط | Expected/Policy |
|---|---|---|
| CTL-NEG-01 | Control Code تکراری در یک Tenant | 4xx/Constraint؛ بدون Duplicate |
| CTL-NEG-02 | ویرایش Global Reference توسط Tenant | 403 و هیچ Side Effect |
| CTL-NEG-03 | Control Category متعلق به Tenant دیگر | 4xx بدون افشای داده |
| CTL-NEG-04 | Cycle در ساختار Category | 400 Validation |
| CTL-NEG-05 | نگاشت به Requirement خارج Tenant یا غیرقابل رؤیت | رد، بدون Link |
| CTL-NEG-06 | `coverage=-1` یا `101` | 400 Validation |
| CTL-NEG-07 | POST Mapping با `approved=true` | `approved=false` در AS-IS |
| CTL-NEG-08 | PATCH Mapping پس از Approve | Approval باید false شود |
| CTL-NEG-09 | Self-Approval نگاشت توسط Creator | **TO-BE** باید رد شود؛ AS-IS تضمین ندارد |
| CTL-NEG-10 | Implementation Unit متعلق به Tenant B | 4xx |
| CTL-NEG-11 | Owner یا Operator غیرفعال | 4xx |
| CTL-NEG-12 | تغییر Control یا Unit در Implementation موجود | 4xx؛ ساخت Implementation جدید |
| CTL-NEG-13 | Duplicate Implementation با (tenant,control,unit) | 4xx/Integrity بدون Row دوم |
| CTL-NEG-14 | کنترل Global غیرفعال برای Implementation | 4xx |
| CTL-NEG-15 | ایجاد Implementation با `effectiveness=effective` و بدون Test | **TO-BE** باید verified=false/رد شود؛ AS-IS ممکن است 201 باشد |
| CTL-NEG-16 | `TestRun pass` بدون Evidence/Reviewer | **TO-BE** نباید Verified Effective شود؛ AS-IS Effectiveness مستقیم تغییر می‌کند |
| CTL-NEG-17 | TestRun `error/not_applicable` | نباید `pass` تلقی شود؛ در AS-IS مقدار قبلی Effectiveness باقی می‌ماند |
| CTL-NEG-18 | Test متعلق به Unit/Tenant دیگر برای Run | 403/404 و بدون Run جدید |
| CTL-NEG-19 | EvidenceLink خارج Scope/Target نامعتبر | 4xx و بدون Link |
| CTL-NEG-20 | دانلود Evidence `pending/infected` در Production Profile | 409 `EVIDENCE_NOT_CLEARED`؛ هیچ Presigned URL صادر نشود |

**افزوده‌های امنیتی برای تست مستقل:** دسترسی User بدون `control.view`، خروجی Cross-Scope، URL/Blob مخرب، MIME خطرناک، اجرای Connector دارای Redirect ناامن و Prompt Injection با متن Evidence. آنها باید به تست‌های کلان Security و AI نیز پیوند داده شوند.

## ۴. پروتکل آزمون اثربخشی معتبر
- نقش Executor و Reviewer تفکیک؛ در آزمون‌های رسمی برای TestRun محتوای روش، دامنه، نمونه و Expected Result حفظ شود.
- نتیجه PASS صرفاً «نتیجه اجرای آزمون» است؛ قبول نهایی در مدل TO-BE پس از Evidence Review با Actor و Time انجام شود.
- اجرای Fail، Partial، NA و Error همگی در تاریخچه ذخیره شوند و علت روشن داشته باشند؛ هیچ داده‌ای نباید به‌صورت مخفی overwrite شود.
- `effective` در Dashboard تنها وقتی `review_state=approved`, `evidence_fresh=true`, `test_valid=true` و Scope/Version معتبر است نمایش «تأیید شده» بگیرد؛ نبود هر عنصر → `unknown/unverified/stale`.
- Source `ConnectorRun` و Hash برای Evidence خودکار مشخص باشد؛ وضعیت `clean` به معنای انطباق نیست.

## ۵. ثبت شواهد و اجرای تست

قالب استاندارد (همه فیلدها لازم برای PASS):
```yaml
test_id: CTL-TC-007
requirement_ids: [FR-CTL-003]
source_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
release: pilot-20261013-r1
environment: local-wsl2-test
tenant_fixture: synthetic-A
operator: test-operator
execution_date: null
status: NOT-RUN
preconditions: "Test and Implementation exist in authorized scope"
expected: "201 with historical TestRun; no fabricated approval"
observed: null
evidence_url: null
defect_issue: null
retest_release: null
```

برای هر تست: HTTP status/Response فقط سانسورشده؛ نام فایل، Hash و Source، تصویر مجاز، Actor، Audit Event و منبع تصمیم ثبت شود. هیچ Cookie، Token، رمز، IP حساس مشتری یا متن دارای حق نشر در GitHub عمومی قرار نگیرد.

## ۶. وضعیت آزمون‌های فعلی و Gapهای شناخته‌شده

- در `backend/apps/controls/tests.py` چهار تابع تست اصلی برای نگاشت چند استاندارد، Approval ممیزی‌شده Mapping، جداسازی Tenant در Implementation و کنترل Global وجود دارد. **نتیجه اجرای فعلی این تست‌ها در محیط پایلوت این گفتگو بررسی نشده است.**
- ControlTest و ControlTestRun API در کد هستند؛ UI `/control-tests` فقط فهرست نمایش می‌دهد.
- Mapping UI Create دارد اما Approval Button در Detail در مرور کد دیده نشد.
- مدل Implementation مقدار `effective` از مسیر write می‌پذیرد؛ `ControlTest.run` مستقیماً مقدار Effectiveness را تغییر می‌دهد. این دو مورد را باید با Rule و Gate روشن کرد.
- Evidence Malware Scanner در محیط آزمایش ممکن است غیرفعال باشد؛ Download Gate تابع Config است. برای پذیرش مشتری Production، اسکن واقعی و Fail-closed باید بررسی شوند.
- **هیچ‌یک از CTL-TC-001..013 در پایلوت جاری به‌عنوان PASS ادعا نمی‌شود**؛ RTM باید تا اجرای واقعی `NOT-RUN` بماند.

## ۷. گیت‌های پذیرش

### CTL-GATE-PILOT
- CTL-TC-001..008 با داده ساختگی و Backend/Frontend قابل انجام؛ فایل Evidence با Scanner مناسب و TestRun واقعی ثبت شود.
- آزمون‌های منفی Cross-Tenant، Global ReadOnly، Scope، Duplicate، Approval و File Gate به نتیجه روشن برسند.
- Reportها/صفحات فقط آنچه ساخته و آزمایش شده به‌عنوان کارا معرفی شوند.
- خلأ `Effective` بدون Review به‌صراحت در تصمیم Release/UX/Reportها محدود شود؛ هیچ KPI گمراه‌کننده نمایش داده نشود.

### CTL-GATE-CUSTOMER
- Workflow تصویب نگاشت و اثربخشی با سیاست سازمان و Reviewer مستقل.
- Scanner حقیقی/Retention/Access/Export و آزمون بازیابی سالم.
- داده واقعی و محتوای استاندارد با حقوق استفاده معتبر.
- تست نفوذ/محدودیت Tenant/Scope و UAT با نقش‌های مشتری.
- گزارش‌های رسمی، صحت شاخص‌ها و فرمت چاپ تاییدشده.
- توافق مستند در مورد Control Frequency، Test Interval، Reviewer Independence و Source Rights.

**پذیرش رسمی این ماژول تا زمان شواهد اجرای نسخه مشخص و امضاهای لازم باز است.**
