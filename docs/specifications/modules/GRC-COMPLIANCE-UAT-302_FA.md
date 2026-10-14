# برنامه آزمون پذیرش تفصیلی استانداردها و انطباق — GRC Platform

> **شناسه:** GRC-COMPLIANCE-UAT-302 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT / NOT EXECUTED  
> **مبنای کد:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691` · **پایلوت:** `pilot-20261013-r1`  
> **وابستگی:** [Compliance Specification-301](GRC-COMPLIANCE-301_FA.md)، [Control-201](GRC-CONTROL-201_FA.md)، [Master UAT](../GRC-UAT-007_FA.md)، [RTM](../GRC-RTM-006_FA.md).
>
> **قاعده حیاتی:** این سند سناریوی پیشنهادی QA است، نه گزارش اجرای QA. هر `PASS` باید Build SHA/Environment/Actor/Request Sanitized/Evidence واقعی داشته باشد. Source Review، Unit Test موجود و Mock به معنی آزمون نصب زنده یا تأیید استاندارد نیست.

## ۱. پیش‌شرط و داده Fixture

- Tenant A و Tenant B ساختگی؛ Unit A1 و A2، مالک فعال، ارزیاب A، بازبین B، Content/Legal Reviewer، خواننده محدود.
- چارچوب داخلی ساختگی با دو بند: `1` (weight=1) و `1.1` (weight=2)، یک نسخه Draft محلی A، یک نسخه Global Active آزمایشی مشترک و یک نسخه Tenant B.
- کنترل مرجع Global فعال، کنترل محلی A و **کنترل محلی B با نگاشت به Requirement global** برای آزمون isolation.
- بسته Import JSON و XLSX با Content Rights آزمایشی قانونی و یک بسته دارای Code تکراری، Parent گمشده، Cycle و Template خالی.
- Assessment A1 دارای دو AssessmentItem و Reviewer مستقل؛ Evidence نمونه داخلی با تاریخ/اعتبار/Hash/مالور Clean در محیط Scanner واقعی.
- Generic Template شامل Boolean، Number، Choice و Text، یک Version منتشرشده و Profile متصل به FrameworkVersion.
- هیچ سند واقعی مشتری، Credential، متن دارای حق نشر استاندارد یا نشانی حساس در Issue عمومی منتشر نشود.
- برای آزمون اسکن، مشتری باید Scanner و Policy مجاز را آماده کند؛ در محیط Local با Scanner disabled ادعای Passed Security صادر نشود.
- هر تست با `PASS/FAIL/BLOCKED/NOT-RUN/N/A(reason)` ثبت شود.

## ۲. سناریوهای مثبت/پذیرش

### CMP-TC-001 — Framework local/global
**FR:** FR-FWK-001؛ **AC:** CMP-AC-01.  
**Steps:** مشاهده `/frameworks` از Tenant A؛ ایجاد Framework local دارای حقوق داخلی آزمایشی؛ مشاهده Global active؛ تغییر Global توسط Tenant A.  
**Expected:** List فقط local A و global active، Local Create=201، Global PATCH=403، Audit و ماندگاری.  
**Baseline:** تست مشابه در `frameworks/tests.py` موجود؛ **UAT نصب زنده NOT-RUN**.

### CMP-TC-002 — Version/Requirement/Translation و Lock
**FR:** FR-FWK-001؛ **AC:** CMP-AC-02.  
**Steps:** FrameworkVersion Draft → Requirement والد/فرزند با ترجمه fa، Weight → Lock → GET Checksum → تلاش PATCH.  
**Expected:** checksum SHA256 length=64، Locked، Requirement ثابت و تغییر PATCH با 4xx.  
**Baseline:** Unit Tests موجود؛ UAT NOT-RUN.

### CMP-TC-003 — Import Dry-run JSON/XLSX
**FR:** FR-FWK-002؛ **AC:** CMP-AC-03.  
**Steps:** dry-run=true با بسته مصنوعی معتبر، ثبت File SHA و Response؛ dry-run=false با همان فایل؛ بررسی Requirement/Translation/Parent؛ Export JSON/XLSX.  
**Expected:** Preview فقط Read، Commit=201، Version Draft، Tree صحیح، Export حقیقی قابل بازشدن، Copyright rights_only_test.  
**Baseline:** تست Import JSON موجود، XLSX و Browser UAT NOT-RUN.

### CMP-TC-004 — Crosswalk بین استانداردها
**FR:** FR-FWK-003؛ **AC:** CMP-AC-04.  
**Steps:** Source/Target دو Requirement مجاز → Mapping با Type/Rationale/Strength/Confidence → Review مستقل → Update ربط.  
**Expected AS-IS:** Create/Approve/API works under permissions. **Expected TO-BE:** Update بعد از تصویب، Approval قبلی را stale کند و نیازمند Reviewer مستقل باشد.  
**Baseline:** Current code lacks invalidation; **TO-BE BLOCKED**.

### CMP-TC-005 — نگاشت کنترل با Scope
**FR:** FR-CTL-001؛ **AC:** CMP-AC-05.  
**Steps:** Control A → Requirement A یا Global → ControlRequirement Draft/Approve → AssessmentItem A GET.  
**Expected:** فقط Mappingهای مجاز Tenant A/approved visible در نمای معتبر و Info Approval روشن؛ مخلوط با Tenant B نشود.  
**Baseline:** static review shows potential missing Tenant filter in serializer; **SECURITY REVIEW #186; NOT-RUN**.

### CMP-TC-006 — ساخت Legacy Assessment و Snapshot
**FR:** FR-ASM-001؛ **AC:** CMP-AC-06.  
**Steps:** FrameworkVersion Active → Assessment A1 با Owner و Unit → GET Items و FrameworkVersion → تلاش PATCH FrameworkVersion/Unit.  
**Expected:** 201، Version local Locked، فقط `assessable=true` Snapshot شده، Version/Scope تغییر نکند.  
**Baseline:** Unit Test موجود؛ UAT NOT-RUN.

### CMP-TC-007 — Score و Progress مستقل
**FR:** FR-ASM-001؛ **AC:** CMP-AC-07.  
**Steps:** دو Item با weight=1/2، اول `compliant=100`، دوم `partial=50` → Summary.  
**Expected AS-IS:** progress=100.000، overall=66.667؛ None برای بدون نمره؛ روش Score در Report ذکر شود.  
**Baseline:** Unit Test برای 66.667 موجود؛ UAT NOT-RUN.

### CMP-TC-008 — N/A با دلیل و بازبینی
**FR:** FR-ASM-001/002؛ **AC:** CMP-AC-08.  
**Steps:** Item `not_applicable` با Justification و Proposal → بازبینی توسط User دیگر → Recalc Score/Progress و Approval History.  
**Expected TO-BE Legacy:** NA بدون Rationale/Review معتبر Complete نشود؛ Snapshot ثابت. **AS-IS Generic ApplicabilityDecision مستقل موجود، Legacy Complete gate کامل نیست.**  
**Baseline:** TO-BE Legacy BLOCKED، Generic مسیر برنامه‌ریزی تست نشده.

### CMP-TC-009 — بازبینی آیتم و ختم Assessment
**FR:** FR-ASM-001؛ **AC:** CMP-AC-09.  
**Steps:** Assessor Item و Evidence ثبت، Reviewer مستقل Review و در پایان Complete.  
**Expected TO-BE:** بدون مرور مستقل/شواهد موردنیاز، Complete رد؛ با شروط صحیح Completed و Snapshot قطعی.  
**Baseline:** کد Legacy Complete فقط نبود NotAssessed را کنترل می‌کند؛ **TO-BE BLOCKED**.

### CMP-TC-010 — Generic Template/Criteria/Publish
**FR:** FR-ASM-002؛ **AC:** CMP-AC-10.  
**Steps:** Template Draft → Version Draft با Criteria → Owner تلاش Publish → Reviewer دیگر Publish → تلاش Edit Criterion.  
**Expected:** self-publish رد، Reviewer publish=200، Criteria Published immutable.  
**Baseline:** Unit Tests موجود؛ UAT NOT-RUN.

### CMP-TC-011 — Generic Typed Answers و Partial Score
**FR:** FR-ASM-002؛ **AC:** CMP-AC-11.  
**Steps:** پاسخ Boolean/Number/Choice/Text، یک Number=75.5، Summary و Missing Review.  
**Expected:** Number 0..100، Choice فقط لیست، Text بدون امتیاز، `is_partial_score` و تعداد Scored مشخص؛ No-data≠0.  
**Baseline:** Unit Tests موجود؛ UAT NOT-RUN.

### CMP-TC-012 — Generic Applicability و History
**FR:** FR-ASM-002؛ **AC:** CMP-AC-12.  
**Steps:** AppDecision با Reason → Reviewer مستقل → Complete → تلاش Answer بعد از Complete؛ Legacy Completed قبل/بعد مقایسه شود.  
**Expected:** تاریخچه Immutable، Self Review رد، Required/Applicability Gate اجرا، Legacy score/status بدون تغییر.  
**Baseline:** Unit Tests موجود؛ UAT NOT-RUN.

### CMP-TC-013 — Evidence/Finding/Action
**FR:** FR-EVD-001/FR-FND-001/FR-ACT-001؛ **AC:** CMP-AC-13.  
**Steps:** AssessmentItem A1، Evidence A1 مجاز را آگاهانه انتخاب و لینک؛ Finding با Owner انتخاب‌شده و Action بساز؛ Refresh/Detail.  
**Expected:** Scoped FK/Typed EvidenceLink، Audit، بدون `evidence[0]` و `users[0]` غیرقابل اتکا در UI هدف.  
**Baseline:** APIها وجود دارند؛ UX نیازمند اصلاح؛ UAT NOT-RUN.

### CMP-TC-014 — حقوق محتوا و Export/AI
**FR:** FR-FWK-002/FR-AI-002؛ **AC:** CMP-AC-14.  
**Steps:** چارچوب دارای مجوز محدود Fixture؛ Export و AI Provider داخلی/خارجی با سیاست متفاوت؛ تلاش مصرف نامجاز.  
**Expected TO-BE:** بدون مجوز قانونی و Policy صریح نه Export/Send؛ Redacted Result و Audit.  
**Baseline:** حقوق معمولاً Metadata/فرآیند هستند؛ GATE حقوق/AI NOT-RUN.

### CMP-TC-015 — UX امن و تاریخ شمسی
**FR:** FR-UX-001/FR-LOC-001؛ **AC:** CMP-AC-15.  
**Steps:** Workspace انتخاب صریح Owner/Evidence، Search و Save/Cancel، گردش تاریخ به جلالی و بازگشت API ISO.  
**Expected:** هیچ Auto-first Selection/Browser Prompt، خطای فیلدی و عدم drift.  
**Baseline:** انتخاب `users[0]/evidence[0]` و Prompt فعلاً در Source؛ شمسی #182؛ **TO-BE BLOCKED**.

### CMP-TC-016 — گزارش رسمی Gap
**FR:** FR-RPT-001؛ **AC:** CMP-AC-16.  
**Steps:** گزارش Gap بر اساس Assessment/Version/Scope/Score/Evidence/Review با Preview و PDF/DOCX/XLSX طبق Catalog واقعی.  
**Expected:** فایل واقعاً بازشدنی، RTL و Header/Source، Export Authorization، وضعیت Draft/Reviewed واضح.  
**Baseline:** گزارش Gap تخصصی هدف است؛ **NOT-RUN/TO-BE**.

### CMP-TC-017 — AI تحلیل شکافِ پیشنهادی
**FR:** FR-AI-001/002/003؛ **AC:** CMP-AC-17.  
**Steps:** AI Provider مجاز و مجوز Tenant، Context محدود، پیشنهاد Gap با Citation، Reject/Review.  
**Expected:** فقط AISuggestion، Source IDs واقعی، بدون تغییر مستقیم Compliance Decision، Prompt Injection محافظت‌شده.  
**Baseline:** AI پایلوت disabled؛ Endpoint Gap تخصصی هدف است؛ **NOT-RUN**.

### CMP-TC-018 — API امنیتی چندسازمانی و Audit
**FR:** FR-IAM-003، NFR-SEC-001؛ **AC:** CMP-AC-18.  
**Steps:** دو Tenant، Global Requirement مشترک، Mapping B به Control B؛ Tenant A Assessment و GET `mapped_controls`؛ Export/List/Detail/AI مجوزهای مختلف، Audit.  
**Expected:** Control ID/Title/Tenant B **هرگز** در Response A ظاهر نشود؛ A منابع مجاز خودش را ببیند؛ 401/403/404 و Audit درست.  
**Baseline:** نیازمند تست بازتولید مستقل #186؛ **P0 REVIEW / NOT-RUN**.

## ۳. تست‌های منفی

| Case ID | ورودی/تهدید | انتظار |
|---|---|---|
| CMP-NEG-01 | Framework Global PATCH با Tenant User | 403 و عدم تغییر |
| CMP-NEG-02 | Requirement Version قفل‌شده PATCH | 400/403، Checksum ثابت |
| CMP-NEG-03 | Parent از FrameworkVersion دیگر | 400 |
| CMP-NEG-04 | درخت Requirement با Cycle | 400 |
| CMP-NEG-05 | Duplicate Requirement Code | 4xx و rollback |
| CMP-NEG-06 | Import خالی/Meta-only | 400 و هیچ رکورد ساخته نشود |
| CMP-NEG-07 | Import JSON malformed یا XLSX فاقد requirements | 400 قابل اقدام |
| CMP-NEG-08 | فایل Import دارای Parent مفقود | 400 + Row Error |
| CMP-NEG-09 | Content حقوق محدود با خروجی/Provider غیرمجاز | رد TO-BE و Audit |
| CMP-NEG-10 | Mapping Source=Target | 4xx |
| CMP-NEG-11 | Mapping Source/Target از Tenant غیرمجاز | رد |
| CMP-NEG-12 | تغییر Mapping تأییدشده بدون Stale | **TO-BE باید Approval باطل شود**؛ GAP فعلی |
| CMP-NEG-13 | Assessor Item با FK/Scope خارج Tenant | 403/404 |
| CMP-NEG-14 | `AssessmentItem.mapped_controls` روی Global Requirement با Control متعلق Tenant B | **هیچ اطلاعات Tenant B**؛ #186 |
| CMP-NEG-15 | Legacy Completed با N/A بدون Review/Evidence | **TO-BE رد**؛ GAP موجود |
| CMP-NEG-16 | Legacy Item `compliant=score0` بدون توضیح/Policy | **TO-BE reject** یا Flag Conflict |
| CMP-NEG-17 | Generic Template Owner Self Publish | 400 |
| CMP-NEG-18 | Generic Choice خارج options/Number 101 | 400 |
| CMP-NEG-19 | Applicability Proposer تلاش Self Review | 403/4xx |
| CMP-NEG-20 | Generic Completed Attempt Update | 400/403، Snapshot بدون تغییر |

### موارد امنیتی اضافی
- خارج Scope روی List/Detail/Export/AI/RAG، No IDOR و حداقل‌سازی Error Response.
- پیکربندی سرور متکی به Rights/Classification، نه `license_type` ادعایی Payload.
- Code، Weight، Status Scores، `metadata` و Translation payload نباید امکان تغییر Score گذشته یا دورزدن Lock بدهند.
- Preview و Commit متفاوت از نظر فایل/Hash باید هشدار/نیاز به تأیید جدید داشته باشند (TO-BE).
- گزارش کنترل‌های مرتبط در Assessment حتماً Tenant/Global status و approval را رعایت کند.

## ۴. دستورالعمل محاسبات مرجع برای QA

**Legacy Example**
```text
Requirement #1: weight = 1.000, compliant -> 100
Requirement #1.1: weight = 2.000, partial -> 50
progress = 2/2*100 = 100.000
overall_score = (1*100 + 2*50)/(1*100+2*100)*100 = 66.667
```

**N/A**
```text
Completed includes status=not_applicable in Progress,
but excludes it from Score numerator and denominator.
If no scored/applicable item exists, overall_score = null.
```

**Generic**
```text
boolean true = 100, false = 0
number 0..100 = itself
choice/text = no numeric score without approved rubric
weighted average uses only scored and applicable criteria
required unanswered and pending applicability review prevent completion
```
**نکته:** این‌ها رفتار محاسبات موجودند. هیچ نتیجه عددی بدون Assessment Version، Method/Weights، Completeness، Reviewer/Evidence به معنی Certification نیست.

## ۵. قالب ثبت شواهد اجرای هر Test
```yaml
test_case_id: CMP-TC-018
requirement_ids: [FR-IAM-003, FR-ASM-001]
environment: local-isolated-synthetic-test
release: pilot-20261013-r1
source_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
tester: null
date_time: null
result: NOT-RUN
preconditions: "Tenant A/B fixtures + shared global version/requirement"
steps_executed: []
expected: "A's mapped_controls exclude all B-only identifiers and data"
observed: null
evidence_url: null
issue: "https://github.com/esfahanit2-coder/grc-platform/issues/186"
```

**هر ادعای PASS نیازمند:** داده مصنوعی قابل بازتولید، HTTP Method/Status، Request/Response بدون Credential، DB Assertion خواندنی، Actor/Time، نسخه، لینک Issue/PR، خروجی فایل/Hash در صورت لزوم و نتیجه Retest.

## ۶. وضعیت کد و تفکیک شواهد
- Unit/Integration Testهای موجود در `frameworks/tests.py`، `assessments/tests.py` و `generic_assessments/tests.py` مسیرهای مهمی را تعریف می‌کنند؛ **در این نوبت Test Runner روی محیط نصب‌شده اجرا نشده است.**
- Source Code برای Lock/Import/Typed Answers/Independent Generic Applicability Review وجود دارد؛ این‌ها اثبات نصب عملی کامل نیستند.
- ریسک `AssessmentItem.mapped_controls` با Tenant مشترک در Issue #186 ثبت شده و تا Test/Fix بسته نشود.
- `legacy-complete` فعلاً تمام Review/Evidence Gates هدف را اعمال نمی‌کند؛ P1 حکمرانی.
- AI روی نصب فعلی غیرفعال و بسته استاندارد رسمیِ دارای حق نشر برای UAT مشتری به‌صورت مستقل نیازمند Rights Review است.
- فارسی‌سازی تقویم #182 و UAT فهرست ماژول‌ها باز است.

## ۷. گیت‌های پذیرش

### CMP-GATE-PILOT
- سناریوهای واردسازی آزمایشی، قفل نسخه، Assessment Snapshot/Score/Progress و Generic typed+review بر Build دقیق PASS.
- **P0 CMP-TC-018/CMP-NEG-14** با داده دو Tenant پیش از استفاده تجاری PASS و بازبینی امنیتی شود.
- Source Rights Fixture، Cross-Tenant/Scope و Negative Tests با شواهد جداگانه.
- امکانات گزارش و AI تنها در صورت فعال‌سازی و آزمون واقعی همان قابلیت نمایش/ادعا شوند.
- هیچ متن استاندارد محدود در Repo عمومی یا AI خارجی غیرمجاز استفاده نشود.

### CMP-GATE-CUSTOMER
- مجوز حقوق متن، ترجمه، واردسازی/صادرات به نام مشتری/ارائه‌دهنده روشن و تأییدشده.
- ScoringPolicy، Applicability و Review/SoD طبق متد مصوب سازمان.
- تمام داده‌های تولید گزارش با Evidence/Actor/Approval/Version مستند و قابل حسابرسی.
- آزمون کاربری نقش‌های واقعی و خروجی Word/PDF چاپ‌شده با تاریخ شمسی.
- بررسی امنیت و پذیرش مستقل؛ هیچ ادعای صدور ISO/افتا یا SoA رسمی از داده خام.

---
**نتیجه فعلی:** سناریوهای سند نوشته شده‌اند، نه اجرا شده؛ وضعیتشان جز برای Source-Observed Gaps، `NOT-RUN/BLOCKED` است.
