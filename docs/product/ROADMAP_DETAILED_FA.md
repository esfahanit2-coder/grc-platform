# پلتفرم GRC — رودمپ تفصیلی (فارسی)

این رودمپ فقط فهرست کارها نیست؛ برای هر Gate توضیح می‌دهد چرا وجود دارد، چه چیزی باید اثبات شود و چه زمانی واقعاً Complete محسوب می‌شود.

## اهداف انتشار

- `v0.9.0-pilot`: نسخه Pilot قابل استفاده End-to-End با Workflowهای واقعی GRC و اثبات عملیاتی کنترل‌شده.
- `v1.0.0-rc1`: Release Candidate بعد از تکمیل Hardening مهندسی، امنیت و عملیات قبل از v1.

## Gate 0 — نرمال‌سازی Repo و CI — کامل

**هدف:** قبل از سرعت‌دادن به Feature Development، GitHub باید منبع قابل‌تکرار و قابل‌اعتماد پروژه باشد.

موارد انجام‌شده شامل Repo خصوصی Canonical، package-lock واقعی، CI Backend/Frontend، Migration از DB خالی روی PostgreSQL 18 + pgvector، Full Django Test، Next.js Production Build، SAST، Secret Scan، Container Scan، SBOM و Release Gate است.

**Done یعنی:** Commit یا Release در صورت Failure شدن Gateهای اصلی Build/Security/Runtime نباید عبور کند.

## Gate 1 — Foundation پایلوت داخلی — نرم‌افزار کامل، اثبات Host واقعی باقی مانده (#7)

**هدف:** اثبات اینکه محصول واقعاً می‌تواند On-Prem و Sovereign اجرا شود، نه فقط در محیط Development/CI.

نرم‌افزار فعلی شامل Pilot Compose، TLS Gateway، S3-compatible Local Storage، Local AI اختیاری، Readiness Check، Backup/Restore و Runbook عملیاتی است.

موارد باقی‌مانده:
- استقرار روی Clean Pilot Host؛
- اجرای واقعی و Destructive Backup/Restore Drill؛
- اندازه‌گیری واقعی RPO/RTO؛
- تست Cookie/CSRF روی TLS واقعی؛
- اجرای Ollama/vLLM در شرایط بدون Internet Egress.

**Done یعنی:** یک Operator دیگر بتواند فقط با Artifact و Runbookهای رسمی محصول را Deploy، Restore و Operate کند و Evidence اندازه‌گیری‌شده بازیابی داشته باشیم.

## Gate 2 — Content Pilot — Foundation کامل، Content مجاز باقی مانده (#5)

**هدف:** اثبات مدل Framework-as-Content با محتوای واقعی و قابل استفاده از نظر حقوقی.

انجام‌شده:
- Content Pack نسخه‌دار و Import Model؛
- Licensing/Provenance Metadata؛
- مسیر Tenant-scoped برای Restricted Content؛
- Foundation تبدیل AFTA Customer-provided؛
- مسیر Human Approval برای Mapping/Crosswalk؛
- Internal Example Control Baseline؛
- SoA/RTP/Audit/Report Outputs.

باقی‌مانده:
- منبع مجاز ISMS/ISO 27001؛
- مستندسازی حق استفاده نرم‌افزاری/بازتوزیع در صورت نیاز؛
- حداقل یک Mapping واقعی AFTA ↔ ISMS ↔ Internal/Common-Control با Human Approval.

**Done یعنی:** محصول Multi-framework Reuse را با Content واقعی و بدون نقض حقوق محتوا اثبات کند.

## Gate 3 — Connector Pilot — Implementation و UI کامل، Live Proof باقی مانده (#6)

**هدف:** اثبات اینکه Factهای Infrastructure می‌توانند تبدیل به Evidence قابل Audit و Reusable شوند، بدون اینکه Human Judgment دور زده شود.

Providerهای پیاده‌سازی‌شده:
- AD/LDAP
- FortiGate
- Veeam
- Tenable/Nessus

Boundaryهای پیاده‌سازی‌شده شامل Read-only Collection، Secret Reference، SSRF Restriction، Target Validation، Normalized Dataset، Evidence Provenance/Hash، Failure Diagnostics، Human-review Metadata و Connector Operations UI با Health/Sync/Run History هستند.

باقی‌مانده:
- اجرای Health/Sync واقعی روی سیستم‌های داخلی مجاز؛
- ساخت Evidence واقعی از حداقل سه Connector؛
- ثبت Failure نماینده و اثبات Diagnosability.

**Done یعنی:** سیستم‌های واقعی داخلی همان Contractهایی را اثبات کنند که الان با Offline/Synthetic Testها پوشش داده شده‌اند.

## Gate 4 — Hardening برای v1.0 Release Candidate

### #19 Operational UI — کامل

داده Demo تولیدی از Dashboard حذف شده، Management Metricها Tenant-scoped و واقعی هستند و Connector Operations UI با Loading/Empty/Error State مناسب وجود دارد.

### #20 Performance/Load Readiness — در حال انجام

**هدف:** قبل از Scale واقعی Pilot، Budget مهندسی قابل تکرار داشته باشیم و N+1/Query Amplificationهای قابل پیشگیری حذف شوند.

کارها:
- حذف N+1های شناخته‌شده در List Serializerها؛
- Regression Test برای اینکه Query Count با تعداد Row به‌صورت خطی رشد نکند؛
- HTTP Load Harness سبک برای p50/p95/max/error-rate/status distribution؛
- Runbook اجرای امن Read-only Load روی Pilot Tenant؛
- اندازه‌گیری روی Host واقعی در آینده بدون اینکه GitHub Runner به‌عنوان Production Capacity معرفی شود.

### #21 HA/DR و Upgrade/Rollback — برنامه‌ریزی‌شده قبل از v1

**هدف:** مشخص‌کردن رفتار Enterprise Deployment هنگام Failure و Software Upgrade.

خروجی لازم:
- Reference Topology و Failure Domainها؛
- Recovery Expectation برای DB/Object Store/Redis/Application؛
- Upgrade Sequence؛
- Migration Safety Rules؛
- Backup/Rollback Prerequisite؛
- Rehearsal Checklist و Evidence Template.

### #22 Offline Release Bundle و Support — برنامه‌ریزی‌شده قبل از v1

**هدف:** نصب، Update و Support در محیط Disconnect باید deterministic باشد.

خروجی لازم:
- Image/Package/Manifest نسخه‌قفل‌شده؛
- Checksum و Verification؛
- SBOM و Security Artifact همراه Release؛
- روش Offline Installation/Update؛
- Operator/Support Handbook؛
- Troubleshooting و Escalation Boundary.

### #8 Security Validation مستقل — Automated Hardening کامل، External Proof باقی مانده

پوشش فعلی شامل Auth Throttling، TOTP Anti-replay، CSRF Negative Path، Cross-tenant IDOR، Evidence Quarantine و Fail-closed Download، Export Audit، SSRF/Local-file Protection برای Report Renderer، RAG Untrusted-context Guardrail، SAST، Secret Scan، Container Scan و SBOM است.

باقی‌مانده:
- Pentest مستقل؛
- Malware Scanner واقعی یا Substitute عملیاتی رسمی و پذیرفته‌شده؛
- Adversarial Test روی AI Provider واقعی؛
- Security Sign-off و Closure یافته‌ها.

## توسعه Post-v1

اولویت‌های ثبت‌شده برای بعد از v1:
- TPRM/Vendor Portal؛
- BCM/BIA و Continuity Workflow؛
- Incident Management؛
- Continuous Control Monitoring؛
- Connector Packهای بیشتر؛
- FAIR/Quantitative Risk/Monte Carlo؛
- Report/Document Templateهای پیشرفته و regulated؛
- AI Governance مثل ISO 42001 در صورت مجوز؛
- Digital Transformation Maturity Pack؛
- Mobile/PWA Approval.

## انضباط رودمپ

صرف وجود کد باعث Complete شدن Gate نمی‌شود. اگر Acceptance به Host واقعی، Connector واقعی، Content مجاز یا Validation مستقل وابسته است، Issue باید باز بماند تا Evidence واقعی وجود داشته باشد. در مقابل، نبود دسترسی فعلی به زیرساخت مشتری نباید کارهای نرم‌افزاری مستقل و قابل تست آفلاین را متوقف کند.
