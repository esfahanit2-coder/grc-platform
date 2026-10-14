# آزمون پذیرش تفصیلی شواهد، ممیزی، یافته‌ها و اقدامات — GRC Platform

> **شناسه:** GRC-EVIDENCE-AUDIT-UAT-402 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT / آزمون‌ها اجرا نشده‌اند  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691` · **پایلوت:** `pilot-20261013-r1`  
> **مراجع:** [مشخصات تفصیلی 401](GRC-EVIDENCE-AUDIT-401_FA.md)، [UAT مادر](../GRC-UAT-007_FA.md)، [RTM](../GRC-RTM-006_FA.md)  
> **اصل:** طرح آزمون صرفاً روش اجرا و انتظار را تعریف می‌کند؛ بدون اجرا و Evidence هیچ موردی PASS نیست. کد/Mock/Unit Test یا Screenshot فقط بخشی از شواهد‌اند.

## ۱. محیط و Fixtureهای مستقل

- دو Tenant ساختگی A و B؛ A1/A2 در A؛ مدیر کل A، Evidence Officer A1، ممیز A1، Reviewer A1 مستقل، کارشناس CAPA A1، Viewer محدود، مدیر B.
- Audit Engagement B با `organization_unit=null` و User B برای Cross-Tenant Team Member.
- Audit Plan A1، Engagement A1 با FrameworkVersion مجاز و دو Workpaper: WP-01 روی Requirement، WP-02 روی ControlImplementation.
- Evidence متنی داخلی، URL ساختگی مجاز و فایل کوچک فاقد داده مشتری؛ Hash/Size، فایل EICAR فقط در آزمایشگاه Scanner مجاز، Pending/Error/Infected.
- Evidence A1 قابل لینک به AssessmentItem/Workpaper A1، Evidence A2 برای سناریوی ممنوع.
- Finding `TEST-FINDING-EAU-001` از Workpaper با Root Cause؛ Action `TEST-CAPA-EAU-001` با DueDate و Reviewer متفاوت.
- همه منابع با کد TEST و بدون Secret در Issue عمومی. برای تست‌های مخرب/فایل آلوده از محیط ایزوله و مجوز واقعی استفاده شود.
- پروفایل `APP_ENV=production` با `EVIDENCE_REQUIRE_CLEAN_DOWNLOAD=true` و Scanner Clamd معتبر نیازمند Host واقعی برای Customer Gate است؛ UAT لوکال با Scanner disabled کافی نیست.
- Gate Test: `test_id, requirement_id, release_sha, runtime_digest, environment, user_role, date, request/response redacted, expected/observed, result, evidence_path_or_url, defect`.

## ۲. سناریوهای مثبت

### EAU-TC-001 — ثبت Evidence متنی و نشانی
**AC:** EAU-AC-01. **مراحل:** Login User مجاز در A1 → `/evidence` → Text Title/Owner/Unit/Classification/CollectedAt → Save → Reload → URL Evidence مجاز. **انتظار:** 201، فیلدهای انتخاب‌شده پایدار و Tenant صحیح؛ عدم نیاز به StorageKey برای Text/URL. **وضعیت:** NOT-RUN.

### EAU-TC-002 — Upload محدود و Metadata سالم
**AC:** EAU-AC-01/02. **مراحل:** فایل کوچک ساختگی PDF/TXT مجاز → Upload multipart → GET Entity → بررسی SHA256/Size/StorageKey و Scan pending → تلاش Client PATCH `malware_scan_status=clean`. **انتظار:** Upload متناسب Config موفق، Scan pending، جعل Meta با 400 رد و مقدار Server-managed حفظ شود. **وضعیت:** NOT-RUN؛ Unit Test مشابه موجود.

### EAU-TC-003 — Scanner واقعی و Download Gate
**AC:** EAU-AC-03. **مراحل:** Scanner معتبر → Clean scan → GET Download → Presigned URL و Audit؛ پرونده Pending/Infected/Error → GET Download. **انتظار:** برای Clean موفق (با Role)، برای غیرclean HTTP 409 و عدم URL؛ Scanner status واقعی؛ Config Production تأیید. **وضعیت:** BLOCKED تا Scanner/Host عملی آماده شود.

### EAU-TC-004 — Hash و Queue Integrity
**AC:** EAU-AC-04. **مراحل:** اسکن فایل، تغییر Blob/Hash حین اسکن و شکست Broker را فقط در محیط تست Mock + Real Queue Failure Controlled شبیه‌سازی کن. **انتظار:** `error` با `object_changed_during_scan` / `object_integrity_mismatch` / `scan_queue_unavailable`، نه clean. **وضعیت:** NOT-RUN؛ برخی Unit Tests در repo وجود دارد.

### EAU-TC-005 — بازاستفاده Evidence در چند هدف
**AC:** EAU-AC-05. **مراحل:** یک Evidence A1 را به AssessmentItem A1 و Workpaper A1 با RelationType مجاز وصل، Count بررسی، Refresh و تلاش Duplicate. **انتظار:** هر Link مجاز 201، Object یک‌بار ذخیره، رابطه تکراری رد، Scope معتبر؛ Evidence status اصالت‌سنجی مستقل لازم دارد. **وضعیت:** NOT-RUN.

### EAU-TC-006 — برنامه ممیزی
**AC:** EAU-AC-06. **مراحل:** ساخت AuditPlan با Date/Owner/Unit → Review مستقل و Approve → Refresh و Audit. **AS-IS انتظار:** API approval ثبت status/by/at. **TO-BE:** Self-Approve و تغییر محتوای مصوب رد. **وضعیت:** NOT-RUN؛ Gate استقلال هنوز GAP.

### EAU-TC-007 — مأموریت/اعضای تیم
**AC:** EAU-AC-07. **مراحل:** ساخت Engagement A1 با Plan/FrameworkVersion/Lead/Requirement/Control → افزودن User A عضو فعال → GET. **انتظار:** M2M/FK هم-Tenant/Unit، Viewer مجاز فهرست را ببیند، Audit، Member یکتا. **وضعیت:** NOT-RUN؛ Cross-Tenant Gap #188 جدا.

### EAU-TC-008 — کاربرگ و بازبینی
**AC:** EAU-AC-08. **مراحل:** Workpaper A1 با Requirement/Control/Tester/Procedure/Sample/Result/Conclusion → Evidence Link → Submit for Review → Reviewer مستقل Approve → Check Freeze. **AS-IS:** CRUD و Review Action موجود. **TO-BE:** Ready/Evidence/Independent Review Gate و Immutable Reviewed. **وضعیت:** NOT-RUN/TO-BE BLOCKED.

### EAU-TC-009 — ایجاد Finding از Workpaper
**AC:** EAU-AC-09. **مراحل:** POST `/audit-workpapers/{id}/findings/` با Title/Owner/Severity، سپس GET Finding و روابط. **انتظار:** Workpaper/Requirement/Control/Unit ردیابی شود، Tenant همان A و گزارش count سازگار. **وضعیت:** NOT-RUN.

### EAU-TC-010 — Finding از AssessmentItem
**AC:** EAU-AC-09. **مراحل:** Item A1 با Partial/NonCompliant → POST `/findings/` با `assessment_item` → GET. **انتظار:** Scope/Requirement به‌صورت معتبر ارث برسد، Cross-Tenant Reject، Audit. **وضعیت:** NOT-RUN؛ Unit Test مشابه موجود.

### EAU-TC-011 — ایجاد CAPA/Action
**AC:** EAU-AC-10. **مراحل:** `POST /findings/{id}/actions/` با Owner/Priority/Due → GET Actions و Finding؛ تغییر Owner → Notification. **انتظار:** Source=finding و ID صحیح، Status Finding به in_remediation و Notification در Scope؛ انتخاب Owner صریح باشد. **وضعیت:** NOT-RUN.

### EAU-TC-012 — انجام، بازبینی و بازگشایی Action
**AC:** EAU-AC-11. **مراحل:** Action Status=done → تحقق `progress=100/completed_at`، سپس reopen با Role مجاز و شواهد → Review. **AS-IS:** PATCH done داده Progress/Time را تنظیم می‌کند. **TO-BE:** بازبینی مستقل و زمان/Progress Reopen سازگار. **وضعیت:** NOT-RUN/TO-BE BLOCKED.

### EAU-TC-013 — Closure Finding با اقدام کامل
**AC:** EAU-AC-12. **مراحل:** یک Action باز → `POST /findings/{id}/close/` رد؛ Action done → تلاش Close با Evidence و Reviewer → Verify. **AS-IS:** اگر Action باز ندارد، Close ممکن است موفق شود. **TO-BE:** بدون Test اثربخشی و Comment/Reviewer مستقل نباید نهایی شود. **وضعیت:** NOT-RUN؛ Unit Test مربوط به Action باز موجود است.

### EAU-TC-014 — استثنای Force Close
**AC:** EAU-AC-12. **مراحل:** Finding دارای Action باز؛ User فقط Scoped finding.close تلاش `force=true`، سپس Whole Tenant با Reason/Approver. **AS-IS:** Scoped رد، Whole Tenant می‌تواند Force کند. **TO-BE:** Justification/Independent Approval/Exception Report اجباری. **وضعیت:** NOT-RUN.

### EAU-TC-015 — گزارش ممیزی و دفاتر
**AC:** EAU-AC-13. **مراحل:** `GET /audits/{id}/report/` DOCX، `/reports/catalog/` برای `audit/findings/actions` سپس Preview/Export؛ فایل‌ها را باز و Scope/Content بررسی کن. **انتظار:** داده واقعی Scope، فایل بازشدنی و Audit Export، Draft/Final Label؛ RTL/Jalali در TO-BE. **وضعیت:** NOT-RUN.

### EAU-TC-016 — زنجیره AuditEvent
**AC:** EAU-AC-14. **مراحل:** دو رویداد مثبت Create/Update در A، یک Denied Download، Verify Integrity، صادرات SIEM با after_sequence و JSONL، تلاش ویرایش AuditEvent. **انتظار:** Integrity verify PASS روی Chain داده مصنوعی، UPDATE/DELETE معمول رد، SIEM حق `audit.view` whole Tenant و بدون payload حساس. **وضعیت:** NOT-RUN؛ Source کد و Unit Tests غیرمعادل UAT.

### EAU-TC-017 — UI فارسی و زمان
**AC:** EAU-AC-16. **مراحل:** تاریخ مدرک/ممیزی/اقدام را شمسی وارد → API ISO → Reload/Report؛ کنترل متن فارسی، IP/UUID LTR، موبایل/کیبورد. **انتظار:** Zero date drift، Field Error؛ انتخاب User/Evidence آگاهانه نه اول فهرست. **وضعیت:** GAP #182 / NOT-RUN.

### EAU-TC-018 — AI پیشنهاد حسابرسی
**AC:** EAU-AC-17. **مراحل:** AI Provider مجاز، Context محدود Workpaper/Finding/Evidence؛ پیشنهاد RootCause/Action؛ بررسی Citation/Redaction؛ Reject؛ تست Prompt Injection. **انتظار:** فقط AISuggestion، نه Workpaper Reviewed/Finding Closed/Action Done، بدون داده Tenant دیگر/محتوای حساس. **وضعیت:** NOT-RUN؛ مدل پایلوت فعلاً خاموش است.

### EAU-TC-019 — مسیر کامل GRC
**AC:** EAU-AC-18. **مراحل:** FrameworkVersion/Requirement → ControlImplementation → AssessmentItem → EvidenceLink → AuditWorkpaper → Finding → Action → Verification → Report. **انتظار:** Domain Refs و Scope/Version/Actor/Source معتبر در تمام صفحات/خروجی‌ها و هیچ تصمیم تأییدشده ساختگی. **وضعیت:** NOT-RUN؛ به اصلاح Methodology/Compliance و UX ممکن است وابسته باشد.

## ۳. سناریوهای منفی امنیتی/حاکمیتی

| ID | درخواست یا وضعیت نامعتبر | نتیجه مورد انتظار |
|---|---|---|
| EAU-NEG-01 | Evidence از Tenant B در Session A | 403/404 بدون داده |
| EAU-NEG-02 | Owner غیرفعال یا Unit از Tenant دیگر | 400 |
| EAU-NEG-03 | Upload `.exe/.html/.svg` یا MIME فعال | 400، بدون Object |
| EAU-NEG-04 | File Size بیشتر از Limit | 400، بدون ذخیره |
| EAU-NEG-05 | Client set `malware_scan_status=clean` | 400؛ مقدار قبلی حفظ |
| EAU-NEG-06 | Download Pending/Infected/Error در Production Profile | 409، بدون URL، Audit Denied |
| EAU-NEG-07 | Scanner/Broker fail یا Object mismatch | Status Error/Pending، نه Clean |
| EAU-NEG-08 | EvidenceLink به Target unsupported/uuid خارجی | 400/404 و بدون Link |
| EAU-NEG-09 | Evidence A1 و Target A2 برای Scoped Create | 400/403 |
| EAU-NEG-10 | EvidenceLink PATCH توسط User مجاز A1 به Target A2 | **باید رد شود**؛ P0 Review #188 |
| EAU-NEG-11 | EvidenceLink PATCH تغییر Evidence به A2 خارج مجوز | **باید رد شود**؛ P0 Review #188 |
| EAU-NEG-12 | AuditTeamMember به Engagement Tenant B با User A و Unit B Null | **باید رد شود**؛ P0 Review #188 |
| EAU-NEG-13 | AuditTeamMember A با User غیرعضو یا غیرفعال B | **باید رد شود**؛ P0 Review #188 |
| EAU-NEG-14 | AuditPlan Owner خودش Approve کند | TO-BE رد (AS-IS Gate ندارد) |
| EAU-NEG-15 | Workpaper Tester خودش Review کند | TO-BE رد (AS-IS Gate ندارد) |
| EAU-NEG-16 | Workpaper Reviewed بدون Evidence و Ready | TO-BE رد |
| EAU-NEG-17 | Finding Closed با Action باز بدون Force | 400 |
| EAU-NEG-18 | Force Close با فقط Unit-scoped finding.close | 4xx |
| EAU-NEG-19 | Finding Close با Action Done اما بدون Verification Evidence | TO-BE رد (AS-IS Gap) |
| EAU-NEG-20 | Action Done با مالک تنها و بدون Reviewer مستقل | TO-BE Unverified، نه Verified Done |
| EAU-NEG-21 | Action reopen ولی `completed_at` قدیمی بماند | TO-BE Reject/Clear با Audit |
| EAU-NEG-22 | Audit Export یا Evidence File از Scope خارج | 403/404 بدون URL/Blob |
| EAU-NEG-23 | Secret یا Raw Evidence payload در SIEM Export | هیچ Raw Payload و Token |
| EAU-NEG-24 | LLM Prompt Injection با متن ساختگی Evidence | هیچ ابزار/Approval/خروج غیرمجاز |

**تست تمایز:** `Malware clean` نه `Evidence reviewed`؛ `Action done` نه `Finding verified`؛ `Workpaper pass` نه `Report signed`. Dashboard/Report باید این تفکیک را نشان دهد.

## ۴. مدل Trace/Evidence پرونده تست

```yaml
test_case_id: EAU-NEG-12
related_requirement: [FR-AUD-001, NFR-SEC-001]
release_source_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
runtime_release: pilot-20261013-r1
environment: isolated-two-tenant-synthetic
tester: null
execution_time: null
status: NOT-RUN
steps_executed: []
expected: "POST audit-team-members with foreign engagement is rejected; no row mutated"
observed: null
request_response_redacted: null
db_assertion: null
issue: "https://github.com/esfahanit2-coder/grc-platform/issues/188"
retest_build: null
```

**برای PASS:** Capture Browser/HTTP و DB Assertion خواندنی، User/Unit/Release، Actual Response و Side Effect، Audit Event، فایل/Hash گزارش، تست Restore در صورت لزوم. **هرگز Credential، Cookie، توکن یا داده حساس را در Issue عمومی قرار ندهید.**

## ۵. وضعیت اولیه قابل اتکا
- `backend/apps/evidence/tests.py` برای Reuse Evidence، Scope Link، Malware Metadata و Download Gate آزمون‌هایی دارد؛ `test_malware.py` برای Hash/Clamd/Broker/Integrity نمونه دارد.
- `backend/apps/findings/tests.py` آزمون جلوگیری از Closure هنگام Action باز را پوشش می‌دهد؛ `backend/apps/actions/tests.py` Done→Progress100 و Source Tenant را پوشش می‌دهد.
- `backend/apps/internal_audits/tests.py` در Baseline فقط Smoke Test import دارد؛ Workflow کامل AuditPlan/Engagement/Team/Workpaper در UAT واقعی اثبات نشده است.
- `frontend/app/audits/[id]/page.tsx` Detail بسیار محدود دارد؛ نتیجه اجرای TestRunner یا مرورگر در این نوبت جمع‌آوری نشده است.
- خطرهای بالقوه Scope/Review با Issue #188 و GAPهای 401 ثبت شده‌اند؛ **هیچ Exploit/Incident واقعی تأیید نشده**.
- scanner و مشتری مستقل، ارتباط AI، تاریخ شمسی و گزارش رسمی متکی به UAT بعدی‌اند؛ حتی Unit Testهای موجود هم در این نوبت اجرا نشده‌اند.

## ۶. گیت‌های پذیرش

### EAU-GATE-PILOT
- TC-001,002,005,007,009..013 با داده مصنوعی UI/API و Refresh PASS.
- `EAU-NEG-10..13` Cross-Tenant/Unit و Issue #188 **P0** قبل از اتکا به مجوزها تعیین تکلیف و روی Build جدید PASS.
- Download Gate با تنظیمات حقیقی Production در محیط کنترل‌شده و Scanner واقعی یا `BLOCKED` صریح.
- Report فقط نوع ساخته‌شده و تست‌شده نمایش داده شود؛ هیچ «Approved Audit Opinion» بدون Gate.
- شواهد/رویدادهای Audit با Chain و Actor مطابق نسخه ثبت شوند.

### EAU-GATE-CUSTOMER
- Test Environment مستقل در مرکز داده مشتری، Approval عملی امنیت/Malware/Storage/Backup و برگه حقوقی دسترسی Evidence.
- Workpaper/Plan/Action/Finding با Reviewer مستقل و Evidence sufficiency Policy مصوب.
- Formal Audit Report DOCX/PDF فارسی و پرینت با مهر/امضا در صورت تعهد قرارداد.
- Log Retention/Integrity Key Backup/Rotation با آزمون و ردیابی.
- امنیت RBAC Tenant/Unit/Classification، دسترسی Blob و AI Context تأیید شده باشد.

---
**وضعیت کلی:** این سناریوها تعریف شده‌اند و باید بعد از برنامه‌نویسی/Release/Environment آماده اجرا شوند؛ به‌هیچ‌وجه به‌صورت پیش‌فرض PASS نیستند.
