# مشخصات نیازمندی‌های نرم‌افزار (SRS/FRD) — GRC Platform

> **شناسه:** GRC-SRS-002 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT · **زبان:** فارسی  
> **مرجع:** [GRC-PRD-001](GRC-PRD-001_FA.md) · **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`  
> **مرز:** رفتارهای «باید» در این سند قرارداد هدف طراحی‌اند؛ با وجود کد و PASS آزمون اشتباه نشوند.

## ۱. قواعد مشترک تمام نیازمندی‌ها
- هر تغییر دامنه‌ای از API احراز هویت‌شده، کنترل `Tenant + OrganizationUnit + Permission` و ثبت Audit لازم عبور کند.
- شناسه‌ها UUID یا کلید پایدار مدل کنونی باشند؛ شماره کد کاربرپسند در محدوده Tenant یکتا باشد.
- در API تاریخ تنها ISO/Gregorian باشد؛ در UI ایران تاریخ شمسی، با تبدیل معتبر و بدون جابه‌جایی روز.
- `created_at`/`updated_at` و شناسه Actor از کلاینت قابل جعل نباشد.
- در ایجاد/ویرایش، اعتبارسنجی دامنه و مالکیت منابع مرتبط در سرور انجام شود.
- حذف موجودیت‌های مرجع تا جای ممکن Soft Delete/Archive باشد؛ پیوندها، تاریخچه و شواهد تصویب محفوظ بمانند.
- خطاهای 400/401/403/404/409/429/5xx از یکدیگر تفکیک و متن راه‌حل کاربرپسند و فاقد Secret داشته باشند.
- همه لیست‌ها Search/Sort/Filter/Pagination، Loading/Empty/Error و خروجی مجاز داشته باشند.
- عملیات چندمرحله‌ای از Double Submit محافظت شود؛ برای عملیات حساس سازگاری تراکنشی لازم است.
- AI، Connector و Import مجوز مضاعف یا مسیر دورزدن سرویس دامنه ایجاد نکنند.
- Permissions باید در خود Backend کنترل شوند، نه فقط با مخفی‌کردن Button.
- وضعیت `Draft`، `AI Suggested`، `Collected`، `Pending Review`، `Approved`، `Rejected` تفکیک داشته باشد.

## ۲. قرارداد قابلیت‌های عملکردی

### SRS-ORG-001 — راه‌اندازی Tenant (FR-ORG-001)
**ورودی:** نام، کد یکتا، نوع، زبان، timezone، Admin اولیه.  
**پیش‌شرط:** مجوز Operator برای Bootstrap؛ Code تکراری نباشد.  
**پس‌شرط:** ایجاد Tenant، عضویت مدیر، Scope پیش‌فرض و Audit.  
**خطا:** کد تکراری (400/409)، رمز ضعیف (پیام کنترل‌شده نه Python Traceback)، صلاحیت ناکافی (403).  
**پذیرش:** صفحه ورود، ورود امن مدیر، نمایش Tenant و عدم دسترسی به Tenant دیگر.

### SRS-ORG-002 — واحد سازمانی (FR-ORG-002)
**فیلدها:** `code, name, parent, unit_type, manager, status, metadata`.  
**قواعد:** والد همان Tenant؛ دور سلسله‌مراتبی ممنوع؛ حذف واحد دارای داده بدون استراتژی آرشیو ممنوع؛ تغییر Scope باید روی مجوزها لحاظ شود.  
**پذیرش:** ایجاد واحد و زیروحد، فیلتر دارایی/ریسک، جلوگیری از انتخاب والد دوری و واحد سازمان دیگر.

### SRS-IAM-001 — RBAC و MFA (FR-IAM-001/002/003)
- عضویت کاربر، نقش، Permission و `UserRoleScope` با زمان شروع/پایان و `organization_unit` پشتیبانی شود.
- درخواست ناشناس به داده محافظت‌شده 401/403 بدهد؛ ریشه `/` برای کاربر ناشناس به Login هدایت شود.
- نشست، MFA، CSRF، logout، مدیریت دسترسی و رویدادهای Login/Logout در UI روشن باشند.
- API با UUID حدسی نباید امکان IDOR، Cross-Tenant و Cross-Scope بدهد.
- صفحه و خروجی گرفتن، مجوز یکسان Backend داشته باشند.
**پذیرش:** تست سه نقش متفاوت، دو Tenant و دو واحد؛ درخواست خارج Scope رد و هیچ داده‌ای نشت نکند.

### SRS-FWK-001 — Framework و نسخه الزام (FR-FWK-001/002/003)
**موجودیت‌ها:** Framework، FrameworkVersion، Requirement، RequirementTranslation، RequirementMapping.  
**فیلدها:** ناشر، نوع، حقوق محتوا، نسخه، تاریخ مؤثر، وضعیت، Checksum، کد بند، عنوان، شرح، Parent، Guidance، Weight، Mandatory، Source.  
**قواعد:** Requirement فقط متعلق به نسخه مشخص؛ نسخه قفل‌شده بدون مهاجرت/فرآیند مصوب تغییر نکند؛ Import پیش‌نمایش و Dry Run و گزارش تعارض بدهد؛ Crosswalk AI فقط پیشنهاد باشد.
**پذیرش:** واردکردن بسته داخلیِ فاقد محتوای محدود، قفل و بررسی Checksum، ایجاد Assessment Snapshot و مشاهده بدون دستکاری تاریخچه.

### SRS-CTL-001 — Control/Implementation/Test (FR-CTL-001/002/003)
**کنترل:** `code, title, description, objective, category, control_type, nature, frequency, automation_level, status`.  
**نگاشت:** `requirement_id, coverage, mapping_type, rationale, approved`.  
**پیاده‌سازی:** `control_id, organization_unit, owner, operator, implementation_description, implementation_status, effectiveness, implementation_date, review_date`.  
**آزمون:** `control_implementation, title, frequency, owner, automation_type, executed_at, result`.  
**قواعد:** یک Control مستقل از استاندارد است؛ اجرای کنترل و نتیجه اثربخشی یکسان نیستند؛ TestRun تاریخی است؛ Evidence در دامنه و تاریخ معتبر باشد.
**پذیرش:** یک کنترل به دو Requirement نگاشت شود؛ پیاده‌سازی یک واحد، Evidence و TestRun مستقل ایجاد شوند؛ خطاهای RBAC رد شوند.

### SRS-AST-001 — Asset/Context (FR-AST-001/FR-CTX-001)
**دارایی:** `code, title, asset_type, organization_unit, owner, custodian, confidentiality, integrity, availability, criticality, status, description`.  
**وابستگی:** `parent_asset, child_asset, dependency_type, critical`.  
**قواعد:** Owner عضو فعال Tenant، Unit متعلق به Tenant، CIA در بازه مجاز؛ وابستگی دارایی به خود ممنوع؛ ارتباط با فرآیند/هدف و ریسک باید قابل پیگیری باشد.
**پذیرش:** ایجاد، Refresh و بازیابی دارایی؛ ثبت Risk مرتبط و تأیید FK/Scope؛ امکان ویرایش مجاز بدون حذف ارتباط‌ها.

### SRS-RSK-001 — شناسنامه و ویرایش ریسک (FR-RSK-001)
**فیلدها:** `code, title, organization_unit, asset, category, scenario, cause, consequence, owner, status, review_date, metadata`.  
**قواعد:** Code یکتا در Tenant؛ ریسک و دارایی از Tenant و Unit سازگار؛ Owner فعال؛ ویرایش از UI با `PATCH` مجاز و Audit؛ وضعیت ارزیابی‌های قدیمی با تغییر Title به‌روز/بازنویسی نشود.  
**پذیرش:** ایجاد، لیست، جزئیات، ویرایش، Refresh و تأیید ارتباط Asset؛ Cross-Tenant/Scope و Asset مغایر 4xx.  
**Gap واقعی:** صفحه ویرایش ریسک در پایلوت وجود ندارد؛ Issue #183.

### SRS-RSK-002 — روش ارزیابی و محاسبه (FR-RSK-002/003)
**روش:** `name, methodology_type, likelihood_scale[], impact_scale[], thresholds[], formula, is_default, status`.  
**ارزیابی:** `risk, methodology, evaluation_type, likelihood, impact, rationale, score, level, evaluated_by, evaluated_at`.  
**قواعد:** مقادیر احتمال/اثر باید در مقیاس مجاز روش باشند؛ امتیاز/سطح باید سمت سرور تولید شوند؛ نوع ذاتی/جاری/باقیمانده/هدف مجزا و تاریخی ذخیره شود؛ Methodology متعلق به همان Tenant باشد.  
**پذیرش:** ایجاد روش 5x5، انتخاب، درج 3×4، نتیجه 12/high با Threshold فرضی 10..16، Refresh، ثبت ارزیابی دوم بدون overwrite قبلی.  
**Gap واقعی:** در پایلوت `POST /risk-methodologies/` با 400 شکست خورد؛ علت باید از Response مشخص شود؛ عدد 12 هنوز توسط نصب زنده اثبات نشده است.

### SRS-RSK-003 — Treatment/Acceptance/RTP (FR-RSK-004/005)
**Treatment:** `risk, strategy, owner, description, target_date, target_score, approval_status, status`.  
**Acceptance:** `risk, evaluation, appetite, requested_by, decided_by, rationale, decision_note, expires_on, review_on, score_snapshot, exceeds_tolerance`.  
**قواعد:** پذیرش ریسک و درمان یکی نیستند؛ پذیرش خارج Tolerance نیاز به اختیار/استثنا دارد؛ مسئول تصویب و متقاضی مطابق سیاست تفکیک وظایف کنترل شوند؛ RTP از Risk/Evaluation/Treatment/Action معتبر استخراج شود.
**پذیرش:** Draft→Review→Decision، عدم دسترسی متقاضی غیرمجاز به Approval، خروجی DOCX معتبر.

### SRS-ASM-001 — Compliance Assessment (FR-ASM-001/002)
**ارزیابی:** `framework_version, organization_unit, title, assessment_type, owner, start_date, due_date, status, overall_score, progress_percent`.  
**Item:** Snapshot کد/عنوان/متن بند، وزن، `status, score, maturity_level, applicability, assessor_comment, reviewer_comment, assigned_to, reviewed_by`.  
**قواعد:** نسخه قفل‌شده منبع؛ پاسخ `N/A` با دلیل؛ Score و Progress جدا؛ تکمیل بدون بررسی/شواهد موردنیاز ممنوع؛ Generic Templates وابسته اجباری به Framework نباشند.
**پذیرش:** دو بند با وضعیت متفاوت، نمره و توضیح، Evidence مجاز، Review و تاریخچه Snapshot.

### SRS-EVD-001 — Evidence (FR-EVD-001/002)
**فیلدها:** `title, evidence_type, source, collected_at, valid_until, classification, filename, size, sha256, storage_key, organization_unit, owner`.  
**قواعد:** Upload باید قرنطینه شود؛ دانلود پیش از Clean gate ممنوع؛ Hash و MIME بررسی؛ Evidence reusable فقط در Scope مجاز؛ داده Connector شامل run/provenance باشد.
**پذیرش:** Upload فایل تست، Hash، اسکن تمیز/نامعتبر، لینک به کنترل/ارزیابی، رد دانلود خطرناک.

### SRS-FND-001 — Finding و CAPA (FR-FND-001/FR-ACT-001)
**Finding:** `type, title, description, severity, root_cause, owner, due_date, status, source_ids`.  
**Action:** `title, description, owner, reviewer, priority, start_date, due_date, progress, status, source_type, source_id`.  
**قواعد:** Source واقعی قابل مشاهده؛ مسئولیت و Review مستقل؛ 100% Progress باعث بستن خودکار Finding نشود؛ Overdue براساس زمان/منطقه سازمان.
**پذیرش:** Finding→Action→Evidence of Closure→Review، سناریوی رد تأیید و مورد معوق.

### SRS-AUD-001 — ممیزی (FR-AUD-001)
**Plan:** دوره، دامنه، Owner، Status، ApprovedBy.  
**Engagement:** هدف، نوع، Lead Auditor، FrameworkVersion، StartDate، Scope، Conclusion.  
**Workpaper:** Requirement/ControlImplementation، عنوان، Tester، Result، Conclusion، Reviewer.  
**قواعد:** ممیز در محدوده مجاز؛ یافته مرتبط ایجاد شود؛ Report منبع و محدودیت داده را نشان دهد.
**پذیرش:** ایجاد برنامه و پرونده، کاربرگ، یافته، Export ممیزی PDF/DOCX.

### SRS-DOC-001 — اسناد و SoA (FR-DOC-001/FR-SOA-001)
- سند و نسخه سند و Approval جدا باشند؛ اصلاح نسخه منتشرشده فقط با نسخه جدید.
- SoA فعلی فقط Draft و Human Feedback دارد؛ هیچ `approved` یا تأیید رسمی بدون مرحله حقوق/بررسی مستقل/امضا ایجاد نشود.
- تغییر محتوای Snapshot ارسال‌شده برای Review، درخواست قبلی را stale کند؛ پاسخ روی نسخه قدیمی با Conflict رد شود.
**پذیرش:** تاریخچه نسخه و تأیید سند، SoA draft معتبر و واضح، رد Approve جعلی.

### SRS-WFL-001 — Workflow/Notifications (FR-WFL-001)
**فیلدها:** Definition/Version، States، Transitions، RequiredPermission، Actor، AssignedTo، Due، Events.  
**قواعد:** Transition خارج Workflow و بدون مجوز ممنوع؛ Inbox از داده مرجع مشتق شود؛ Notification status جدا از Business State باشد.
**پذیرش:** تخصیص، تأیید/رد، تاریخچه انتقال، اعلان و Inbox بدون ایجاد Task تکراری.

### SRS-RPT-001 — Reporting (FR-RPT-001)
**گزارش‌ها:** draft SoA، RTP، Audit، Findings، Actions، Executive.  
**فرمت موجود در Catalog:** PDF/DOCX/XLSX/CSV بر حسب گزارش.  
**قواعد:** Export و Preview دارای Scope واحد؛ زمان/فیلتر/منبع/وضعیت Draft در فایل؛ فارسی/RTL و تاریخ شمسی در خروجی رسمی بدون تغییر داده API؛ ثبت رویداد export.  
**پذیرش:** Preview و چند قالب خروجی واقعی، بازشدن فایل‌ها و کنترل دسترسی cross-scope.

### SRS-AI-001 — AI Gateway/RAG/Review (FR-AI-001/002/003)
**ورودی هدف:** `task, subject, authorized_sources, classification, provider_id, schema_version, language` و Policy استخراج‌شده از سرور.  
**خروجی:** `interaction_id, suggestion_id, proposed_value, source_ids, unknowns, review_status`.  
**قواعد:** اجازه قبل از Retrieval، RAG محدود به Scope، عدم Prompt Injection/Secret، `AISuggestion` تنها Proposal، اعمال از Domain Service مجاز، AI Disabled موجب ازکارافتادن CRUD نشود.
**پذیرش:** مدل واقعی/تستی با داده مصنوعی، مجوز دو Tenant، provider unavailable، پیشنهاد رد و تأیید انسانی با Audit.

### SRS-CON-001 — Connector (FR-CON-001)
- چهار Connector اولیه: AD/LDAP، FortiGate، Veeam، Tenable/Nessus.
- `config, secret_env_var, TLS verify, run started/finished, status, error, normalized evidence`.
- Read-only و Evidence-centric؛ اعتبارسنجی Target و SSRF، عدم نمایش Credential.
**پذیرش:** Target واقعی مجاز، دسترسی حداقلی، Sync موفق و شکست قابل عیب‌یابی؛ هیچ Status سبز انطباق صرفاً از Sync.

### SRS-OPS-001 — عملیات/استقرار (FR-OPS-001)
- نصب Imageهای immutable امضاشده؛ Manifest و Digest معتبر.
- `preflight, install, bootstrap, verify, backup, recovery-preflight, restore, rollback` با Runbook.
- TLS و Secrets معتبر، مخازن DB/Object جدا، Health/Queue/Beat/Backup با Freshness.
**پذیرش:** نصب Host مستقل و بازیابی تخریبی مجاز، RPO/RTO اندازه‌گیری‌شده؛ Test Key/Cert تولیدی معتبر محسوب نشود.

## ۳. نیازمندی‌های غیرعملکردی و روش اندازه‌گیری

| NFR | معیار موردنیاز | نحوه اثبات |
|---|---|---|
| NFR-SEC-001/002 | عدم نشت Cross-Tenant/Scope، احراز هویت و Audit سالم | Negative API matrix + review |
| NFR-SEC-003 | File Quarantine و Scan fail closed | آزمون واقعی scanner و فایل تست |
| NFR-DEP-001/002 | نصب Signed Airgap و عدم egress ناخواسته | Host مستقل + Network observation |
| NFR-REL-001/002 | Backup/Restore و rollback صحیح | مانور بازیابی؛ RPO/RTO ثبت واقعی |
| NFR-UX-001 | شمسی در UI، ISO در API و چاپ RTL | Browser + PDF/DOCX rendering test |
| NFR-PERF-001 | بار/Latency/Error تحت Load هدف | Budget توافقی؛ p50/p95/error/throughput |
| NFR-OBS-001 | Beat/Worker heartbeat، Queue، Backup freshness | پایش عملی پس از Startup |
| NFR-LEGAL-001 | منبع/حقوق استفاده محتوا قابل حسابرسی | legal owner approval |
| NFR-AI-001 | ایمن‌بودن RAG و Provider Routing | Tenant leak/prompt-injection tests |

**هیچ عدد ثابت برای SLO، RTO/RPO و ظرفیت بدون مبنای پذیرش مشتری نهایی محسوب نمی‌شود.**

## ۴. پیام‌های خطا و قرارداد UX
- `400`: فیلد و علت دقیق (بدون Stacktrace)، متن قابل اصلاح در فرم؛ 400 فعلی روش ارزیابی باید تحلیل شود.
- `401`: نشست منقضی/ورود لازم؛ یک تلاش معتبر Refresh و سپس هدایت به Login.
- `403`: مجوز عملیات یا Scope کافی نیست؛ به جای صفحه خالی.
- `404`: منبع مجاز موجود نیست یا نباید آشکار شود.
- `409`: Conflict نسخه/Review stale/تغییر هم‌زمان.
- `429`: محدودیت نرخ با درخواست مجدد طبق سیاست.
- `5xx`: شناسه درخواست برای پشتیبانی؛ بدون اطلاعات حساس داخلی.

## ۵. قیود تغییر و مهاجرت
- تغییر در Frozen Signed Release ممنوع؛ قابلیت جدید در Branch/PR، تست، Merge و بسته جدید.
- Migration افزایشی و سازگار باشد؛ اسناد تصویب‌شده و ارزیابی‌ها به‌صورت خام اصلاح نشوند.
- هر FR دارای Issue، Test Case، Owner و نتیجه UAT شود. جدول پیگیری در `GRC-RTM-003_FA.md`.
- قالب استانداردها و اسناد واقعی مشتری تنها با حق استفاده معتبر وارد شوند.

## ۶. سناریوی طلایی پذیرش
```
Bootstrap Tenant/Admin -> Login/MFA -> Organization Unit
-> Asset -> Risk -> Risk Methodology -> Inherent Evaluation
-> Common Control -> Control Implementation -> Evidence -> Test Run
-> Residual Evaluation -> Treatment -> Action -> Finding (if applicable)
-> Framework Assessment -> Audit Workpaper -> Report/RTP/SoA Draft
-> RBAC Negative Tests -> Backup/Restore Proof -> Acceptance Report
```

**حالت فعلی این سناریو:** در پایلوت محلی تا ایجاد Asset و Risk و تأیید FK پیش رفته‌ایم؛ Methodology creation در UI با HTTP 400 مانع ادامه است. سایر حلقه‌ها با مشاهده صرف کد «PASS» تلقی نمی‌شوند.

---
**بازبینی لازم:** Product Owner، Tech Lead، Security Lead، QA Lead و مسئول محتوا/حقوق.
