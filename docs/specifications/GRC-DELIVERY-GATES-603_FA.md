# ارزیابی تجمیعی معماری و گیت‌های تحویل عملیاتی GRC Platform

> **شناسه:** GRC-DELIVERY-GATES-603 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT / Product + Security + QA + DevOps sign-off pending  
> **مبنا:** بررسی Source نسخه `main@e7a745c47919f6ec028e429c210bbdfd4589c691` و گزارش‌های قبلی تست پایلوت امضاشده `pilot-20261013-r1`. تاریخ: 2026-10-14.  
> **هدف:** فاصله **مشخصات کامل محصول** با **Release قابل نصب، آزمون و استفاده در مرکز داده مشتری** را به تصمیم‌های قابل اجرا و گیت‌های قابل اثبات تبدیل کند.
>
> این سند گزارش اثبات Production Readiness نیست. کد اجرایی، Containerهای مشتری و ابزار تست زنده در این مرحله اجرا نشده‌اند. مسیر GitHub PR #184 مستنداتی و DRAFT است. هیچ Issue باز به معنی Patch اعمال‌شده نیست.

## ۱. جمع‌بندی وضعیت واقعی
- هسته Risk, Assets, Controls, Frameworks, Assessments, Evidence, Findings, Actions, Documents, Audit/Reporting و SoA Draft در Repository فایل‌های مدل/API/UI دارند؛ سطح تکمیل UX و گیت‌های صحت آنها برابر نیست.
- AI/RAG و چهار Connector وجود دارند ولی AI نصب پایلوت خاموش است و تست Vendor/Provider واقعی در این نوبت انجام نشده.
- نصب آزمایشی محلی WSL/Docker توسط اپراتور با ۸ سرویس و HTTPS `grc.pilot.internal` گزارش شده است؛ **معادل مرکز داده واقعی نیست**. گواهی TLS داخلی Self-signed bypass برای Pilot، به‌هیچ‌وجه مبنای اعتماد Production نباشد.
- Smoke Health `live/ready` HTTP 200 گزارش شده اما در برهه‌ای Global Health برابر `critical` به علت نبود Backup و مدارک Worker/Beat بوده؛ باید با اجرای جدید و شواهد تعیین تکلیف شود.
- Asset/Risk Test در DB وجود داشته و ارتباط FK تأیید شده؛ فرم Risk UI Link و Edit نقص UX دارد (#183)؛ Risk Methodology Create در Browser/API `400` و منوی ارزیابی خالی گزارش شده (#161). این‌ها Blocker سناریوی End-to-End ارزیابی ریسک‌اند.
- تقویم جلالی/RTL چاپ نیازمند UAT و تغییرات (#182). صدور رسمی SoA در کد حاضر **وجود ندارد**؛ Draft/Review Feedback آن سند رسمی نیست.
- تست‌های UAT در شش بسته تفصیلی (Risk, Control, Compliance, Evidence, Documents, AI/Connectors) **طراحی شده‌اند، نه اجرا**؛ تغییر آن‌ها به PASS فقط با شواهد Build/Actor/Time ممکن است.

## ۲. خطرهای انتشار با اولویت الزام‌آور

| دروازه | Issue | علت | اقدام لازم و شاهد |
|---|---|---|---|
| P0-S1 | [#186](https://github.com/esfahanit2-coder/grc-platform/issues/186) | احتمال اختلاط `AssessmentItem.mapped_controls` بین Tenantها روی Framework Global | Test دو Tenant؛ فیلتر منبع/Approval/Scope؛ Regression List/Detail/Export |
| P0-S2 | [#188](https://github.com/esfahanit2-coder/grc-platform/issues/188) | AuditTeamMember Tenant/User Validation و EvidenceLink PATCH مجوز مقصد | Repro دو Tenant و Unit؛ Fix Service/Serializer + Audit |
| P0-S3 | [#190](https://github.com/esfahanit2-coder/grc-platform/issues/190) | احتمال PATCH/DELETE ReportTemplate local/global با `report.view` | Repro GET/PATCH/DELETE؛ Global ReadOnly، Auth Manage و Negative Tests |
| P0-S4 | [#192](https://github.com/esfahanit2-coder/grc-platform/issues/192) | AI Endpoint Egress و RAG Classification و Knowledge collision | Fake Network+Source Tests؛ قبل از فعال‌کردن AI باید رفع/رد مستند |
| P0-Q1 | [#161](https://github.com/esfahanit2-coder/grc-platform/issues/161) | UAT پایلوت و Error ثبت Risk Methodology، گیت‌های آزمون | Body خطای 400، API/DB Test، Repair در PR جدید و Browser retest |
| P0-O1 | — | Health Critical، Backup/Restore/Worker/Beat Evidence نامعلوم در انتهای نصب | Preflight، backup restore drill، Queue smoke، Health Evidence با Digest و Timestamp |
| P1-D1 | [#185](https://github.com/esfahanit2-coder/grc-platform/issues/185) | Control Effectiveness قابل اعلام بدون Independent Review | تفکیک Implementation/Test/Verified + Histories/Migrations |
| P1-D2 | [#187](https://github.com/esfahanit2-coder/grc-platform/issues/187) | Crosswalk Approved پس از Edit stale نمی‌شود؛ Legacy Assessment Review/Score | Versioned Scoring/Applicability/SoD/Approval invalidation |
| P1-D3 | [#189](https://github.com/esfahanit2-coder/grc-platform/issues/189) | Workpaper/Action/Closure بدون اثبات Effectiveness مستقل | Reviewer/Verification lifecycle و استثنای Force Close قابل Audit |
| P1-D4 | [#191](https://github.com/esfahanit2-coder/grc-platform/issues/191) | Independent Document Approval و Publication/Attachment Trust | Controlled Publish/Approver Policy و Hash/Blob |
| P1-I1 | [#193](https://github.com/esfahanit2-coder/grc-platform/issues/193) | Connector AD TLS، Secret Config، Unit Reassignment، Classification | Sandbox Negative+Positive و اتصال واقعی Vendor فقط بعد از مجوز |
| P1-UX1 | [#182](https://github.com/esfahanit2-coder/grc-platform/issues/182)، [#183](https://github.com/esfahanit2-coder/grc-platform/issues/183) | Jalali/RTL و Risk Edit UI | Browser/Print regression، عدم تغییر داده‌های قدیمی |

**توضیح رتبه:** P0 شماره‌های 186/188/190/192 **Source-level security review hypotheses** هستند، نه Incident اثبات‌شده. تعیین نهایی شدت پس از Repro و تحلیل دسترسی ممکن است تغییر کند. تا زمان Test و تصمیم امنیتی مستند، نباید Release چندسازمانی مشتری را «تأییدشده» معرفی کرد.

## ۳. دامنه انتشار حداقلی قابل دفاع

### Release Candidate R1 (فقط پس از گیت‌ها)
- ورود با نقش سازمانی و Audit صحیح؛ Asset/Risk CRUD و RiskEvaluation Methodology فعال با Test مثبت/منفی.
- Framework/Requirement و Assessment روی داده مشتری **با حق قانونی استفاده**، Score و Source Snapshot روشن؛ Preview/Export با Scope.
- Control/Implementation و Evidence/Link/Finding/Action؛ UI و Report با برچسب `collected/unverified/verified` صادقانه.
- Document Version/Approval داخلی و DOCX ساده یا قالب بهبود‌یافته‌ای که واقعا Print QA پاس کرده؛ SoA Draft **با برچسب آشکار عدم تأیید**.
- Backup/Restore، TLS CA معتبر، Secrets، Tenant Boundaries، Health، Operations، Upgrade/Rollback واقعی روی ماشین آزمون.
- **AI Optional Disabled و Connector Optional Disabled**؛ نبود آنها مانع بهره‌برداری انسانی GRC نباشد، مشروط به اینکه نقش فروش/قرارداد آن‌ها را در R1 وعده ندهد.

### R1+ پس از گیت‌های مستقل
- AI Local/Cloud با Policy/Egress و Human-reviewed model-security evaluation؛ Vendor Integrations با سازگاری نسخه/طبقه‌بندی و Credentials read-only؛ Advanced Reports/AI Evidence.
- SoA **رسمی** فقط پس از Legal Source Approval، فهرست کنترل‌های ضروری، شواهد معتبر، انسانی مستقل و Signature/Immutable Snapshot.
- تحلیل کمی و ماژول‌های Incident/BCM/TPRM/Continuous Monitoring در PRD هدف‌اند نه تعهد R1.

## ۴. ترتیب اجرای مهندسی (در هر گام با PR و تست)
1. **Source freeze/CI baseline:** main SHA، image digests، migrations، test runner، OpenAPI snapshot و وضعیت مستند test در GitHub تثبیت شود. Release signed Pilot بدون hot-edit.
2. **Security reproduction P0:** هر مسئله #186/#188/#190/#192 در DB و FakeNetwork ایزوله Repro/Disprove، Root Cause و Patch+Negative Tests. در صورت AI Disabled هم #192 پیش از Enable شرط است.
3. **End-to-end golden path:** خطای Risk Methodology 400 #161 با Response body بدون Secret بررسی و اصلاح؛ Risk→Evaluation→Treatment→Control→Evidence→Finding→Action→Report قابل تکرار شود.
4. **Assurance semantics:** #185/#187/#189 با Migration-safe Historical States، ناهمگنی Legacy و Generic، No Auto Compliant؛ #191 برای چرخه انتشار اسناد رسمی.
5. **Deployment readiness:** شبکه/Volume/Backup/PITR یا Restorable Snapshots، Seed/Migrations، Health Worker/Beat، TLS chain معتبر، رصد Egress، secrets/rotation، نصب تازه/Upgrade/Rollback و Restore از Backup آزمایش شود.
6. **UX و خروجی:** فیلدهای فارسی، تاریخ شمسی بدون Drift، A4 RTL چاپ، فرم‌های واقعی Owner/Evidence/Methodology، Error UX و Accessibility.
7. **Integration/AI acceptance:** #192/#193، Provider محلی، Red-team انسانی، ۴ Vendor Sandbox tests؛ باید بتوان بدون این مرحله R1 core را به مشتری نصب کرد اگر قرارداد محدود باشد.
8. **Product sign-off و Customer UAT:** هر Module Gate، User Roles، Scopes، Traceability، Runbook، Acceptance Record و Owner Sign-off.

## ۵. Exit Gates با معیار اثبات

| Gate | Minimum evidence | وضعیت این نوبت |
|---|---|---|
| SOURCE-GATE | Main SHA، Tagged Signed Bundle، Image Digest، SBOM/Build Log | Pilot signature قبلاً گزارش شده؛ Review live این نوبت NOT-RUN |
| TEST-GATE | Automated Suite + DB Migration + Negative Security + Browser Golden Journeys | NOT-RUN در این نوبت |
| TENANT-GATE | Cross-Tenant/Unit/ACL P0 tests روی Release Candidate | P0 investigation OPEN |
| ASSURANCE-GATE | Score/Approval/Evidence semantic regression و حفظ تاریخچه | P1 OPEN |
| EGRESS-GATE | AI/Connector Destination, TLS, Classification, Captures | AI Disabled local؛ EXTERNAL-PROOF |
| BACKUP-GATE | Backup recorded، restore verified، recovery RPO/RTO stated and measured | Health historically critical؛ NOT-RUN currently |
| RENDER-GATE | DOCX/PDF/XLSX opened + RTL/A4/Jalali + Rights/Source | NOT-RUN |
| DEPLOY-GATE | New clean host install، CA، 8-service roles، monitor، rollback | WSL pilot only; Customer DC NOT-RUN |
| CUSTOMER-GATE | Authorized deployment scope + human UAT sign-off | NOT-RUN |

**قانون:** هیچ `PASS` با «فایل وجود دارد» یا «Docker container started» صادر نشود. `blocked` و `not-run` در گزارش فروش واضح بمانند.

## ۶. قرارداد تحویل نصب‌پذیری در مرکز داده مشتری

بسته R1 باید این اقلام را داشته باشد: `release-manifest` امضاشده و Hashها، `install/upgrade/rollback` Runbook، Container Offline Images یا Registry مصوب، Seed/Migration Plan، نمونه `env` **بدون secrets**، فهرست Port/DNS/TLS/Volumes/Firewall/Egress، Resource Sizing با Benchmark، دسترسی Admin اولیه قابل تغییر و MFA Policy، Backup & Restore Tested، Health/Monitoring، Data Retention/Export/Deletion Policy و گزارش کامل UAT/Pentest و Limitations.

**حداقل در پایلوت بدون سرور مستقل:** تست Docker WSL به کشف خطای UI/API کمک می‌کند ولی Backup/PITR، HA، DNS/TLS و عملکرد مرکز داده واقعی را اثبات نمی‌کند. باید محیط موقت دوم یا Host مشتری/CI Runner مطابق قرارداد برای آزمون مستقل فراهم شود؛ بدون آن ادعای Production Ready معتبر نیست.

## ۷. کارهای مستندسازی باقی‌مانده پس از شش بسته

- **ERD physical/migration matrix** با Foreign Keys/Indexes/Constraints تمام ماژول‌ها؛ صرف ERD منطقی کافی نیست.
- **OpenAPI executable contract** و Snapshot Diff بعد از هر PR، Error Codes و ACL Contract.
- **Threat Model STRIDE** و Product Security Test Matrix برای Tenant/Evidence/AI/Connector.
- **Operational Runbook** واقعی Tenant provisioning، secret rotation، backup/restore، TLS و disconnected update.
- **Data dictionary/report semantics** برای شاخص‌های Nullable/Partial/Unverified و مقایسه Scoreهای ناهمگن.
- **Legal rights matrix** برای متن استانداردها و AI/Export/Distribution در ایران و مشتری خارجی.
- **Localization Print Spec** و Golden Word/PDF templates.
- **Issue-to-test matrix**: برای هر P0/P1 مشخص باشد PR/SHA/Test Evidence/Retest چه زمانی و توسط چه نقش مورد تأیید است.

## ۸. نتیجه تصمیم Release
از نظر مستندات، تصویر محصول و مهندسی ماژول‌ها اکنون قابل تبدیل به برنامه کار توسعه‌دهنده است. از نظر اجرا، **داده‌ها و کدها هنوز مجموعه شواهد کافی برای تأیید نسخه قابل تحویل به دیتاسنتر مشتری ندارند**؛ اولویت بعدی نباید افزودن قابلیت جدید به Frontend باشد. ابتدا مشکلات مجوز/امنیت و Golden Journey، سپس نصب تمیز+Restore+UAT در محیط مستقل و در نهایت قابلیت‌های اختیاری AI/Connector باید تعیین تکلیف شوند.

**این سند DRAFT است و باید پیش از Merge توسط Product Owner، Dev Lead، Security Lead و QA مرور شود.**
