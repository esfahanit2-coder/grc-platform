# پلتفرم GRC — مغز محصول (فارسی)

## ۱. هدف محصول

پلتفرم GRC یک سامانه بومی، ماژولار، مستقل از چارچوب و مناسب استفاده سازمانی فارسی/انگلیسی است که برای مدیریت یکپارچه Governance, Risk & Compliance طراحی شده است. هدف این است که هم الزامات و چارچوب‌های داخلی ایران و هم استانداردهای بین‌المللی در یک هسته مشترک پوشش داده شوند، بدون اینکه منطق برنامه برای هر استاندارد جداگانه hard-code شود.

چارچوب‌ها و Content Packهای هدف که برای محصول در نظر گرفته شده‌اند شامل محتوای مجاز افتا، ISMS/ISO/IEC 27001، COBIT، ISO 9001، ISO 31000، مدل‌های بلوغ تحول دیجیتال، NIST، CIS، BCM و در آینده چارچوب‌های حاکمیت هوش مصنوعی مانند ISO 42001 در صورت داشتن مجوز مناسب هستند.

هدف انتشار پروژه ابتدا `v0.9.0-pilot` و سپس `v1.0.0-rc1` است و GitHub منبع اصلی و رسمی پروژه محسوب می‌شود.

## ۲. اصول بنیادین محصول

### Frameworkها داده هستند، نه کد
هر Framework باید به‌صورت داده نسخه‌دار شامل metadata، Requirements، ترجمه، Mapping و اطلاعات حقوقی/منبع نگهداری شود. اضافه‌کردن یک استاندارد یا مقرره جدید نباید نیازمند شاخه‌های اختصاصی در backend باشد.

### Implement once, comply many
یک Common Control باید بتواند به چندین Requirement از چند Framework مختلف متصل شود. سازمان کنترل را یک‌بار در قالب Control Implementation پیاده می‌کند و Evidence و Testهای آن در ارزیابی‌های مجاز مختلف دوباره استفاده می‌شوند.

### تعریف، پیاده‌سازی و نتیجه ارزیابی از هم جدا هستند
- `Requirement` بیان می‌کند چارچوب چه چیزی می‌خواهد.
- `Control` تعریف عمومی یک کنترل قابل‌استفاده مجدد است.
- `ControlImplementation` بیان می‌کند یک واحد واقعی سازمان آن کنترل را چگونه اجرا کرده است.
- `AssessmentItem` نتیجه یک ارزیابی را نگه می‌دارد؛ نتیجه ارزیابی نباید روی خود Requirement ذخیره شود.

### تاریخچه ریسک باید حفظ شود
Risk هویت و سناریوی ریسک را نگه می‌دارد. امتیازهای inherent/current/residual/target باید در رکوردهای تاریخی `RiskEvaluation` ذخیره شوند و با overwrite کردن یک فیلد روی Risk از بین نروند.

### Evidence یک موجودیت مستقل و قابل‌استفاده مجدد است
Evidence باید منبع، محدوده، زمان جمع‌آوری، provenance، metadata تمامیت و لینک به اشیای کسب‌وکار را داشته باشد. یک Evidence معتبر در صورت سازگاری Scope و مجوز می‌تواند در چند Test یا Assessment استفاده شود.

### AI کمک می‌کند، انسان تصمیم می‌گیرد
خروجی AI پیشنهاد است. تصمیم‌هایی مثل effective بودن کنترل، compliant بودن Requirement، پذیرش ریسک یا بستن Finding نباید مستقیماً توسط AI انجام شوند. نتایج مهم باید از مسیر Human Review و `AISuggestion` یا Workflow معادل عبور کنند.

### On-Prem و Air-Gapped یک حالت اصلی محصول است
استقرار داخلی و بدون اینترنت جزو طراحی اصلی است، نه قابلیت فرعی. معماری باید Docker، PostgreSQL/pgvector، Redis/Celery، Object Storage سازگار با S3 و AI محلی مانند Ollama/vLLM-compatible را پشتیبانی کند.

## ۳. معماری اصلی

- Backend: Python + Django 5.2 LTS + Django REST Framework
- Frontend: React + Next.js + TypeScript
- Database: PostgreSQL 18
- Semantic Retrieval: pgvector با Permission-safe retrieval
- Queue/Cache: Redis + Celery
- File Storage: abstraction سازگار با S3
- AI Gateway: مستقل از Provider با OpenAI-compatible، Ollama، vLLM و Endpoint خصوصی
- سبک معماری: Modular Monolith

## ۴. زنجیره‌های اصلی دامنه

```text
Framework -> Version -> Requirement <-> Common Control
Common Control -> Control Implementation -> Evidence -> Control Test
Asset / Process -> Risk -> Risk Evaluation -> Treatment -> Action -> RTP
Framework Version -> Assessment -> Assessment Item -> Evidence -> Finding -> CAPA
Internal Audit -> Workpaper -> Finding -> Action -> Audit Report
Authorized GRC Data -> Permission-safe RAG -> AI -> AISuggestion -> Human Review
```

## ۵. ماژول‌های محصول

### سازمان، Tenant و Identity
مدیریت چند Tenant، ساختار واحدهای سازمانی، Membership، Role، Permission و Organization-scoped RBAC. اعمال Scope باید در backend انجام شود و صرفاً فیلتر UI کافی نیست. MFA و Security Policy نیز در همین لایه قرار می‌گیرند.

### Framework و Content Pack
مدیریت Framework، FrameworkVersion، Requirementهای سلسله‌مراتبی، ترجمه، import/export، provenance، licensing metadata و crosswalk. هر Content Pack باید تاریخچه نسخه و وضعیت حقوقی مشخص داشته باشد.

### Common Controls
کتابخانه کنترل‌های قابل‌استفاده مجدد که به یک استاندارد خاص وابسته نیست. کنترل می‌تواند به چند Requirement متصل شود و نسخه/پیاده‌سازی محلی داشته باشد.

### Control Implementation و Testing
ثبت وضعیت واقعی پیاده‌سازی کنترل در سازمان، Owner/Operator، توضیحات اجرا، تاریخ بازبینی، Effectiveness، Control Test و Test Runهای تاریخی.

### Asset و Process
زمینه مشترک برای Risk، Control، Evidence و Assurance. Asset/Process باید در چند ماژول قابل‌استفاده مجدد باشند.

### Risk Management
Risk Register، Methodology، مقیاس Likelihood/Impact، ارزیابی‌های تاریخی inherent/current/residual/target، Treatment، Action، Appetite/Tolerance و خروجی Risk Treatment Plan. قابلیت‌های Quantitative/FAIR/Monte Carlo برای Post-v1 در نظر گرفته شده‌اند.

### Compliance Assessment
ساخت Assessment از Framework Version قفل‌شده و نسخه‌دار. Assessment Item باید Snapshot از Requirement را نگه دارد و Status، Score، Maturity، Applicability، Comment، Reviewer، Control، Evidence و Finding را ثبت کند.

### Evidence Management
نگهداری metadata و مرجع Object Storage برای Evidence. Evidence می‌تواند از کاربر، سند، Connector یا فرآیند اتوماسیون مجاز ایجاد شود. Evidence خودکار همچنان نیازمند Human Review است.

### Findings / NCR / CAPA / Actions
مدیریت Finding یا Non-Conformity، Severity، Status، Owner، Root Cause، Due Date، Remediation، Verification و Action/CAPA مرتبط.

### Internal Audit و Workpaper
Audit Engagement، Scope، Workpaper، Finding، Action و تولید Audit Report. تا جای ممکن از همان Evidence و Assurance Objectهای مشترک استفاده می‌شود.

### Documents، Policy و Report Factory
Versioning و Approval اسناد و تولید خروجی‌های رسمی. خروجی‌های اصلی شامل SoA، Risk Treatment Plan، Audit Report و گزارش‌های Management/Compliance/Risk هستند. تولید Policy/Procedure با AI می‌تواند انجام شود، اما Approval نهایی انسانی است.

### Workflow، Task و Notification
مکانیزم عمومی Assignment، Due Date، Approval و Notification که Assessment، Risk، Finding، Audit، Document و ماژول‌های آینده از آن استفاده می‌کنند.

### AI و RAG
AI برای Draft، خلاصه‌سازی، Mapping Suggestion، Remediation Suggestion، Document/Report Assistance و جست‌وجو روی داده مجاز استفاده می‌شود. Permission Filtering باید قبل از Retrieval انجام شود. Context بازیابی‌شده untrusted محسوب می‌شود و نباید Instruction داخلی آن اجرا شود.

### Connectors
Connectorهای Pilot فعلی شامل AD/LDAP، FortiGate، Veeam و Tenable/Nessus هستند. ماهیت آن‌ها read-oriented و Evidence-focused است و فقط Fact/Evidence جمع می‌کنند؛ حق اعلام Compliance یا Effectiveness ندارند.

### Dashboard و Reporting
Dashboard باید داده واقعی Tenant را نشان دهد و نباید KPI یا Risk ساختگی در مسیر production داشته باشد. Connector Operations شامل Health، Sync History و خطاهای redacted است و بعداً نماهای عملیاتی Risk/Compliance/Audit گسترش پیدا می‌کنند.

## ۶. الزامات تجربه کاربری

- تجربه سازمانی فارسی‌محور با RTL واقعی و پشتیبانی کامل انگلیسی.
- مستندات اصلی محصول و Developer Handover به فارسی و انگلیسی.
- نمایش داده و عملیات بر اساس Role و Organization Scope.
- تفاوت واضح بین داده قطعی، پیشنهاد AI، Evidence خودکار و Approval انسانی.
- Loading/Empty/Error State واقعی به‌جای داده نمونه ساختگی.
- اولویت Traceability، Auditability و Explainability بر پیچیدگی تزئینی UI.

## ۷. قواعد حقوقی Content

متن کامل ISO/COBIT/AFTA یا هر محتوای محدودشده نباید بدون مجوز مناسب در Repo یا Built-in Pack محصول قرار گیرد. محتوای Customer-provided یا Licensed باید Tenant-scoped باشد و provenance/licensing metadata آن حفظ شود. Classification عمومی یک سند به‌تنهایی مجوز بازتوزیع نیست.

## ۸. تمایزهای محصول که از تحقیق رقبا حفظ شده‌اند

- ساخت یک Framework/Common Control Engine مشترک به‌جای نرم‌افزار جداگانه برای هر استاندارد.
- استفاده مجدد از Control Implementation و Evidence در چند Assessment.
- اتصال Governance، Risk، Compliance، Audit، Document و Action در یک مدل قابل‌ردیابی.
- پشتیبانی واقعی On-Prem/Air-Gapped و Local AI به‌جای SaaS-only.
- فارسی/انگلیسی/RTL به‌عنوان نیاز اصلی محصول.
- Connectorهای Read-only و Evidence-focused.
- استفاده از AI برای شتاب‌دهی، نه تصمیم‌گیری مستقل درباره Compliance.

## ۹. وضعیت فعلی

هسته‌های Multi-tenancy/RBAC/MFA، Framework Engine، Common Control، Asset، Risk، Assessment، Evidence، Finding/Action، Internal Audit/Workpaper، Control Test، Document/Report، Workflow/Notification، AI Gateway/RAG، Connectorهای Read-only، Operational Dashboard، Connector Operations UI، CI/Security/Release Gates و Pilot Deployment Foundation پیاده‌سازی شده‌اند.

Validation واقعی هنوز برای Connectorهای داخلی، Clean Host و Restore/RPO/RTO، Local AI بدون Egress، Pentest مستقل و Security Sign-off و Content/Crosswalk مجاز نهایی باقی مانده است.

کار Pre-RC نیز شامل Performance/Load Validation، HA/DR و Upgrade/Rollback، Offline Release Bundle و Support Handbook است.

## ۱۰. جهت Post-v1

TPRM/Vendor Portal، BCM/BIA، Incident Management، Continuous Control Monitoring، Connector Packهای بیشتر، Quantitative Risk/FAIR/Monte Carlo، Document Generation پیشرفته، AI Governance/ISO 42001، Digital Transformation Maturity و Mobile/PWA Approval Experience از اولویت‌های Post-v1 هستند.
