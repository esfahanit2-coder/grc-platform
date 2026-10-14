# برنامه آزمون تفصیلی اسناد، قالب‌ها، گزارش و SoA — GRC Platform

> **شناسه:** GRC-DOCUMENT-SOA-UAT-502 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT — آزمون‌های این سند NOT-RUN  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`، `pilot-20261013-r1`  
> **ارجاع:** [GRC-DOCUMENT-SOA-501](GRC-DOCUMENT-SOA-501_FA.md)، [Master UAT](../GRC-UAT-007_FA.md)، [RTM](../GRC-RTM-006_FA.md).  
> **اصل شواهد:** تعریف Test و وجود Backend/UnitTest، اثبات کارکرد نصب‌شده نیست؛ هر PASS نیازمند داده مصنوعی، HTTP/Browser/DB Evidence، نسخه دقیق و Actor است.

## ۱. محیط و Fixtures

- Tenant A/B ساختگی، Units A1/A2، User Owner A1، Document Editor A1، مستقل Reviewer A1 و Stage-2 Reviewer A1، فقط Document Viewer A1، Report Viewer (بدون Report Generate) A1، Admin Tenant A، Platform Admin فقط برای کنترل Global Reference.
- Document `TEST-POL-DOC-501` با Owner و Scope A1 و Version `0.1` Draft؛ Version `0.2` بعد از Reject؛ دو Approval مرحله‌ای و در صورت نیاز دو User مستقل.
- ReportTemplate local A و B و Global برای Negative Tests؛ قالب HTML/PDF دارای داده‌های ساختگی و متن فارسی.
- FrameworkVersion **Tenant-owned و Locked** با Content مصنوعی و Rights قانونی؛ Requirement و Control A1، Implementation A1، Treatment A1، Evidence A1 با Hash/Source و SoARegister Revision 1.
- SoAControlDecision `annex_a` و `additional`، Included/Excluded/Undecided، یک Decision EvidenceLink، Reviewers independent و یک تصمیم تغییرکرده بعد از Review Request.
- هیچ PDF واقعیِ محدود، متن دارای حق نشر استاندارد، Secret/Token یا داده مشتری در Test Public Repo قرار نگیرد.
- Client اجرای API دارای Session مجاز؛ User B حق دیدن A ندارد؛ تست Template Renderer در محیط ایزوله با Limit CPU/Memory و No Egress.
- تمامی Test Results: `PASS/FAIL/BLOCKED/NOT-RUN/N/A(reason)`.

## ۲. سناریوهای مثبت

### DOC-TC-001 — Create Document و Reload
**AC:** DOC-AC-01؛ **Steps:** `/documents` → Create سند نوع Policy با Code/Title/Owner/Unit → Save → Reload و GET. **Expected:** 201، Tenant server-derived، `status=draft`، Persistence و Audit Create. **Baseline:** Backend/Frontend Source موجود؛ UAT NOT-RUN.

### DOC-TC-002 — ایجاد نسخه و Edit Draft
**AC:** DOC-AC-01/02؛ **Steps:** Version 0.1 با Content/ChangeSummary → PATCH متن تا Draft جاری است → Reload → بررسی `current_version`. **Expected:** متن جدید فقط در Draft Current، created_by Server-managed؛ Version Code یکتا. **Baseline:** Unit tests وجود دارند؛ UAT NOT-RUN.

### DOC-TC-003 — تعیین Approver و Submit
**AC:** DOC-AC-03؛ **Steps:** دو Approver در Order 1 و 2 → `POST /document-versions/{id}/submit/` → GET Version/Approvals → تلاش PATCH متن. **Expected:** Submit=200، Version=review، متن قفل، اعلان مرحله اول و Audit. **Baseline:** کد/تست Source موجود؛ UAT NOT-RUN.

### DOC-TC-004 — تصویب مرحله‌ای و Replay
**AC:** DOC-AC-03؛ **Steps:** Stage2 زودتر Approve → Reject؛ Stage1 Approve → Stage2 Approve؛ Replay تصمیم. **Expected:** رأی زودهنگام و Replay رد، Version=approved، Document=approved، Stage Order ثابت؛ User اشتباه حق تصمیم نداشته باشد. **Baseline:** Source tests موجود؛ UAT NOT-RUN.

### DOC-TC-005 — درخواست اصلاح/رد و تاریخچه
**AC:** DOC-AC-05؛ **Steps:** Version در Review → `changes_requested` با Comment → Version superseded و سند Draft → ایجاد Version 0.2 → آرشیو/سوابق 0.1. **Expected:** Content و Decision قبلی بدون overwrite، New Draft مستقل، داده نسخه ردشده قابل مشاهده در History. **Baseline:** Unit Test دارد؛ UAT NOT-RUN.

### DOC-TC-006 — استقلال بازبین سند رسمی
**AC:** DOC-AC-04؛ **Steps:** Owner/Creator با `document.approve` در همان Tenant تلاش Assignment به خود و Decide؛ Reviewer مستقل در همان Scope تصمیم بگیرد. **Expected TO-BE:** Self-Approve مطابق سیاست اسناد رسمی رد، Reviewer مستقل مجاز؛ Snapshot Content Version کنترل شود. **Baseline:** شرط صریح استقلال در View بررسی‌شده دیده نشد؛ NOT-RUN / TO-BE GAP.

### DOC-TC-007 — DocumentLink Traceability
**AC:** DOC-AC-06؛ **Steps:** Document local → Risk/ControlImplementation/AssessmentItem/Workpaper مجاز → Create Link، List/Remove، UI Detail. **Expected TO-BE:** تمام Targetهای Domain Registry با Tenant/Unit مجاز و Audit، Foreign UUID رد. **Baseline:** مدل و Serializer دارند، Router/UX کامل ندارند؛ BLOCKED.

### DOC-TC-008 — ReportTemplate محلی و Global
**AC:** DOC-AC-07؛ **Steps:** ایجاد Local Template با Admin دارای `report.generate` → Viewer `report.view` List → تلاش Viewer PATCH Local و PATCH Global. **Expected:** Viewer فقط Read، Global برای Tenant هم ReadOnly و بدون SideEffect. **Baseline:** P0 Source Concern #190؛ NOT-RUN.

### DOC-TC-009 — HTML/PDF Template Render
**AC:** DOC-AC-08؛ **Steps:** Template با `configuration.html_template` و Context ساختگی، `POST /reports/render-template/` برای `html` و `pdf`، بررسی پاسخ فایل. **Expected:** PDF واقعی بازشدنی، HTML Escaped، No HTTP/File URL Fetch، Audit Export. **Baseline:** Source renderer موجود؛ UAT NOT-RUN.

### DOC-TC-010 — Export DOCX سند
**AC:** DOC-AC-09؛ **Steps:** `GET /document-versions/{id}/export/` → ذخیره DOCX و بازکردن در Word/LibreOffice فقط برای بررسی مستقل Document (نه Spreadsheet)؛ نمایش فارسی/Content/Version. **Expected AS-IS:** DOCX با عنوان و متن، Audit؛ **TO-BE:** Header/Footer/RTL/Classification/Watermark. **Baseline:** Source موجود، چاپ فارسی آزمون نشده.

### DOC-TC-011 — Report Catalog و Dataset Scoped
**AC:** DOC-AC-09/16؛ **Steps:** `/reports/catalog/`, `preview/?type=...`, `export/` برای `rtp,findings,actions,executive,audit,soa` طبق Catalog. **Expected:** فقط Formatهای اعلام‌شده، Scope مجاز، صفر نادرست برای No-Data ایجاد نشود و SoA Worksheet Draft بماند. **Baseline:** Code موجود، E2E NOT-RUN.

### DOC-TC-012 — SoA Register معتبر و قفل‌شده
**AC:** DOC-AC-10؛ **Steps:** Tenant-owned FrameworkVersion Locked + Unit A1 → `POST /soa/registers/` با Title/Revision → Detail. **Expected:** 201، status=draft، is_formal=false و `approval_status=not_available`، Unique Revision. **Baseline:** Unit Tests متعدد در repo؛ UAT NOT-RUN.

### DOC-TC-013 — SoA Decision و روابط
**AC:** DOC-AC-11؛ **Steps:** ایجاد Included با Rationale/Control/Impl/Treatment هم‌Scope و RiskControl موجود، Excluded با Rationale بدون Implementation، Undecided، Additional. **Expected:** 201 برای انواع معتبر، Duplicate/Foreign رد، Edit فقط فیلدهای مجاز و LastEditedBy ثبت. **Baseline:** Source tests دارند؛ UAT NOT-RUN.

### DOC-TC-014 — SoA Readiness تشخیصی
**AC:** DOC-AC-13؛ **Steps:** Draft با Included ناقص و Evidence منقضی → `GET readiness` → مشاهده Finding Codes. **Expected:** `formal_attestation_allowed=false`، `evidence_sufficiency=requires_human_review`، هیچ Approval State ثبت نشود. **Baseline:** Source tests موجود؛ UAT NOT-RUN.

### DOC-TC-015 — مقایسه عددی Annex A
**AC:** DOC-AC-13؛ **Steps:** درخواست بدون Reference (رد) و با `reference=iso-iec-27001-2022-annex-a-structure-only` → Compare با شناسه نمونه/Additional. **Expected:** Reference 93 Numeric IDs، Unknown/Missing/Undecided جدا، بدون ادعای پوشش ISO یا گواهی؛ هیچ متن استاندارد بازنشر نشود. **Baseline:** Source Tests موجود؛ UAT NOT-RUN.

### DOC-TC-016 — بازخورد انسانی Draft SoA
**AC:** DOC-AC-12؛ **Steps:** Request Reviewer مستقل → Digest → Feedback Recorded با Note → Replay Response → تغییر Decision/Implementation و تلاش پاسخ به Request قدیمی. **Expected:** یک Response در Round، Replay رد، تغییر محتوا Stale/409، SoA همچنان Draft/Not Approved. **Baseline:** Unit Tests وجود دارند؛ Browser UAT NOT-RUN.

### DOC-TC-017 — تلاش تصویب رسمی SoA
**AC:** DOC-AC-14؛ **Steps:** سعی Client POST `status=approved` هنگام Create، PATCH تصمیم با `approval_status`، Review Feedback با عبارت «تأیید» در Note. **Expected:** API هیچ Formal Approval نپذیرد، Notice Draft و is_formal=false ثابت بماند. **Baseline:** Source Guards وجود دارند؛ UAT NOT-RUN.

### DOC-TC-018 — AI Document Draft
**AC:** DOC-AC-15؛ **Steps:** AI Provider مجاز + Prompt ساختگی Title/Purpose → `POST /ai/assist/document-draft/` → دریافت Interaction/Suggestion → Reject/Review → GET Documents/Versions. **Expected:** فقط Suggestion، بدون Document created یا approved/published. **Baseline:** AI محلی خاموش است؛ NOT-RUN.

### DOC-TC-019 — RTL، تاریخ و قالب برند
**AC:** DOC-AC-17؛ **Steps:** تاریخ بازنگری جلالی؛ RTL Word/PDF، Header/Footer، watermark Draft، صفحات/امضاکننده و متن لاتین/فارسی بررسی. **Expected TO-BE:** تاریخ بدون Drift، Content Rights، Print A4 و ساختار سالم. **Baseline:** #182 و DOCX ساده؛ TO-BE/BLOCKED.

### DOC-TC-020 — مسیر انتهابه‌انتها
**AC:** DOC-AC-18؛ **Steps:** Framework/Requirement → Risk/Control/Evidence → Document Draft AI یا دستی → Approval ordered → DOCX → Report Preview/Export → SoA Draft/Readiness/Feedback. **Expected:** Source/Permission/Audit و Version/Status واضح، Formal SoA نه؛ همه فایل‌ها بازشدنی و داده مجاز. **Baseline:** Golden Journey کامل هنوز UAT ندارد؛ NOT-RUN.

## ۳. تست‌های منفی حیاتی

| Negative ID | سناریو | Expected |
|---|---|---|
| DOC-NEG-01 | Document با Code تکراری در Tenant | 4xx، بدون Duplicate |
| DOC-NEG-02 | Owner غیرفعال/بدون `document.view` در Unit | 400 |
| DOC-NEG-03 | Tenant A GET/PATCH Document متعلق B | 403/404 بدون Data |
| DOC-NEG-04 | PATCH Document.status=approved یا Version.status=published | فیلدهای server-managed تغییر نکنند |
| DOC-NEG-05 | PATCH نسخه بعد از Submit Review | 4xx و Hash/Content ثابت |
| DOC-NEG-06 | Submit بدون Approver یا Approver غیرفعال | 4xx |
| DOC-NEG-07 | Approver مرحله دوم زودتر تصمیم بگیرد | 4xx بدون تغییر |
| DOC-NEG-08 | Same Approval دوباره Decide | 4xx، Decision دوم ایجاد نشود |
| DOC-NEG-09 | Non-assigned User با Permission approve رأی دهد | 4xx |
| DOC-NEG-10 | Owner/Creator سند رسمی خودش Approve کند | TO-BE reject، Source GAP |
| DOC-NEG-11 | Archive سند Current Review | 4xx |
| DOC-NEG-12 | DocumentVersion با `storage_key` کنترل‌شده توسط Client و Path نامعتبر | TO-BE reject / Server-owned Blob |
| DOC-NEG-13 | DocumentLink foreign Target یا foreign Tenant | 4xx؛ Route TO-BE |
| DOC-NEG-14 | Report Viewer PATCH/DELETE ReportTemplate محلی | **403/404، P0 #190** |
| DOC-NEG-15 | Tenant Admin PATCH/DELETE Global ReportTemplate | **403/404، P0 #190** |
| DOC-NEG-16 | Tenant A GET/PATCH قالب خصوصی Tenant B | 403/404، no side effects |
| DOC-NEG-17 | ReportTemplate HTML/CSS با HTTP/File URL | No fetch, 4xx/blocked |
| DOC-NEG-18 | Template Render با Context بسیار بزرگ یا Recursion/Heavy Expression | Resource bounded و خطای Sanitized |
| DOC-NEG-19 | SoARegister با Global Framework یا Version Unlocked | 400 |
| DOC-NEG-20 | SoARegister دارای `status=approved` | 400، status همچنان Draft |
| DOC-NEG-21 | SoA Include/Exclude بدون Rationale یا Cross-Unit Impl | 400 |
| DOC-NEG-22 | SoA Feedback بدون Reviewer مستقل یا Stale Digest | 4xx/409، no formal approval |
| DOC-NEG-23 | SoA Numeric Diff بدون صراحت Reference | 400، No implicit ISO edition claim |
| DOC-NEG-24 | AI Prompt Injection/External Provider با Restricted Evidence | No disclosure/tool approval؛ untrusted Content |

**بخش منفی تکمیلی:** Snapshot/History corruption، هم‌زمانی Submit/Decide، غیرفعال‌شدن Approver هنگام Review، Owner Scope change، Tenant-level export و تزریق CSV/HTML. این‌ها باید در Suites Security/Performance نیز گنجانده شوند.

## ۴. ماتریس ردیابی سریع

| AC | Test مثبت | منفی مهم |
|---|---|---|
| DOC-AC-01/02 | DOC-TC-001/002 | NEG-01..05 |
| DOC-AC-03/04/05 | DOC-TC-003..006 | NEG-06..11 |
| DOC-AC-06 | DOC-TC-007 | NEG-13 |
| DOC-AC-07 | DOC-TC-008 | NEG-14..16 |
| DOC-AC-08/09 | DOC-TC-009..011 | NEG-17/18 |
| DOC-AC-10/11/12/13/14 | DOC-TC-012..017 | NEG-19..23 |
| DOC-AC-15 | DOC-TC-018 | NEG-24 |
| DOC-AC-16/17 | DOC-TC-011/019 | NEG-03/16..18 |
| DOC-AC-18 | DOC-TC-020 | تمام مرزهای فوق |

## ۵. ثبت نتیجه هر سناریو

```yaml
test_case_id: DOC-NEG-15
requirement_ids: [FR-DOC-001, FR-RPT-001, NFR-SEC-001]
baseline_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
release: pilot-20261013-r1
environment: isolated_synthetic_two_tenant
executor: null
time_utc: null
status: NOT-RUN
preconditions: "TenantA admin, shared global ReportTemplate, ReportTemplate API available"
executed_steps: []
expected: "TenantA PATCH global template rejected; global row hash unchanged"
observed: null
http_status: null
sanitized_response_evidence: null
db_side_effect_assertion: null
audit_event: null
issue: "https://github.com/esfahanit2-coder/grc-platform/issues/190"
retest_release: null
```

**لازم برای PASS:** Build/Image Digest، مسیر و مجوز User، Snapshot Source، HTTP Response بدون Cookie/Authorization، Screenshot مجاز، Hash فایل DOCX/PDF، اثبات گیت منفیِ بدون Side Effect، Audit Actor/Time/Request ID و Issue/PR Retest.

## ۶. Source-reviewed baseline؛ نه Test Report

- `backend/apps/documents/tests.py` آزمون Submit، Approval stage/order، Replay، Scope و نسخه را **تعریف کرده است**. اجرای همین تست‌ها در این نوبت انجام نشده.
- `backend/apps/reporting/test_soa_drafts.py` برای Draft/Readiness/Digest/Stale/Numeric Reference مجموعه تست دارد؛ اجرای روی Server مشتری یا Browser نشده.
- `ReportTemplateViewSet` در Source نیازمند بازبینی P0 Write Permission #190 است؛ هیچ سوءاستفاده مشتری اثبات نشده.
- `DocumentLink` در Model/Serializer هست، در Router ماژول Docs Route برای آن بررسی نشده؛ UI لینک‌سازی هدف است.
- `SoARegister` فقط `draft` دارد. هیچ رسمی/امضا/Certification موجود محسوب نشود، حتی وقتی `readiness` بدون یافته داخلی برگردد.
- `document_docx` Title/Content ساده تولید می‌کند؛ ساخت Word حرفه‌ای RTL امضاشده باید در Product Scope جدا توسعه/تست شود.
- AI Provider در نصب پایلوت خاموش است؛ هیچ خروجی AI در این نوبت آزمون نشده.
- تاریخ شمسی و بسته چاپی مشتری هنوز مستند به PASS واقعی نیستند (#182).

## ۷. گیت‌های پذیرش

### DOC-GATE-PILOT
- `DOC-TC-001..005` و `DOC-TC-008..017` با داده مصنوعی و Build جدید در UI/API و فایل‌های خروجی PASS یا Limitations صریح (نه PASS کاذب).
- **P0 #190** (ReportTemplate read-only / permission) پیش از اتکا به tenant isolation بازتولید، Fix و Retest.
- Negative tests Scope/Replay/Stale/Invalid SoA تأیید شوند.
- ظاهر UI باید SoA Draft را مستقل از Document Approved نشان دهد؛ Review feedback ≠ approval.
- هیچ محتوای استاندارد محدود بدون Rights Review وارد Repo عمومی یا Provider خارجی نشود.

### DOC-GATE-CUSTOMER
- نسخه رسمی اسناد با Approval Policy مورد قبول مشتری، استقلال Reviewer، حق محتوا و Report source snapshot.
- پرینت واقعی Word/PDF فارسی/RTL، تاریخ جلالی، Template branding و Watermark/شماره نسخه.
- رسمی‌کردن SoA **تنها در صورت ساخت مدل و Workflow امضای مستقل، تایید Content/Control Inventory و UAT مشتری**.
- Export/AI بر مبنای Classification، Cross-Tenant Security و Data Residency.
- Signature Key/Backup/Restore/Retention و تاریخچه تأییدها مطابق تعهد قراردادی.

**تا تکمیل گیت، این ماژول Draft/Controlled Document Candidate است؛ SoA رسمی یا صدور گواهی ادعا نشود.**
