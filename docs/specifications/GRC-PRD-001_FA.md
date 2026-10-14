# سند نیازمندی‌های محصول (PRD) — GRC Platform

> **شناسه:** GRC-PRD-001 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT / برای بازبینی · **تاریخ:** ۱۴۰۵/۰۷/۲۱ (2026-10-13)  
> **مبنای کد بررسی‌شده:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691` · **بسته آزمایشی نصب‌شده:** `pilot-20261013-r1`  
> **نوع سند:** مشخصات «محصول هدف» همراه با وضعیت اجرای واقعی؛ **نه گواهی انطباق، تعهد قراردادی یا تأیید آماده‌بودن Production**.
>
> مالک بازبینی: Product Owner / تیم GRC · تأیید محصول: **هنوز انجام نشده**.

## ۱. خلاصه اجرایی

GRC Platform یک نرم‌افزار فارسی/انگلیسی، چندسازمانی، مستقل از چارچوب و مناسب استقرار داخلی/آفلاین برای مدیریت **حاکمیت، ریسک، انطباق، کنترل، دارایی، ارزیابی، شواهد، ممیزی، اقدام اصلاحی، مستندات، گزارش و هوش مصنوعی با بازبینی انسانی** است.

**ارزش اصلی:** یک کنترل مشترک می‌تواند به چند الزام استاندارد مرتبط شود؛ یک پیاده‌سازی کنترل می‌تواند در چند ارزیابی استفاده شود؛ Evidence به‌صورت مستقل، نسخه‌دار و دارای منشأ نگهداری می‌شود؛ تصمیم و سابقه با یکدیگر خلط نمی‌شوند. فعالیت‌های هوش مصنوعی پیشنهاد هستند و به جای تصمیم مسئول سازمان نمی‌نشینند.

**تمایز بازار:** پشتیبانی واقعی از نیازهای ایران (افتـا/ISMS و تاریخ شمسی، سند فارسی و RTL)، داده در اختیار مشتری، نصب آفلاین، Connectorهای شواهد‌محور، گزارش قابل استناد، ردگیری سرتاسری و عدم وابستگی به یک ارائه‌دهنده AI.

## ۲. مسئله مشتری و نتایج مورد انتظار

### ۲.۱ دردهای مشتری
- اطلاعات دارایی، ریسک، کنترل، ممیزی و انطباق در فایل‌ها و سامانه‌های جداگانه پراکنده است.
- تهیه سند و ارزیابی برای هر استاندارد به‌شکل تکراری انجام می‌شود و وضعیت‌ها با هم تناقض پیدا می‌کنند.
- نسبت «ادعای انطباق» با شواهد، آزمون اثربخشی و مسئول تصمیم به‌خوبی قابل ردیابی نیست.
- اقدامات اصلاحی و موعدها گم می‌شوند یا مسئول و بازبین روشن ندارند.
- سازمان به دلایل امنیتی/حاکمیتی نمی‌تواند اطلاعات را به سرویس ابری خارجی ارسال کند.
- ابزارهای عمومی به فرآیندهای رسمی، تقویم و خروجی فارسی ایران پاسخ کامل نمی‌دهند.

### ۲.۲ نتایج قابل اندازه‌گیری هدف (فرضیه محصول، نه KPI اثبات‌شده)
- کاهش ورود دوباره Evidence و کنترل تکراری در ارزیابی‌های هم‌دامنه.
- امکان ردگیری از الزام یا ریسک تا کنترل، مدرک، آزمون، یافته و اقدام از طریق رابط کاربری.
- تعیین مالک و موعد برای هر اقدام مهم و مشاهده موارد معوق در کارتابل.
- تولید گزارش‌های مدیریتی و ساختاریافته از اطلاعات تأییدشده، بدون اعداد ساختگی.
- نصب، بازیابی و ارتقای قابل مستندسازی روی زیرساخت مجاز مشتری.
- ثبت تصمیم، شخص تأییدکننده، مبنا و نسخه داده مربوطه برای عملیات حساس.

## ۳. کاربران و سناریوهای کلیدی

| شناسه | شخصیت کاربر | هدف اصلی | عملیات مجاز نمونه |
|---|---|---|---|
| PER-01 | مدیرعامل/هیئت‌مدیره | تصویر وضعیت ریسک و انطباق | خواندن خلاصه و روند، دریافت خروجی مجاز |
| PER-02 | مدیر GRC / ISMS | هدایت ارزیابی‌ها و پاسخ‌گویی | پیکربندی ارزیابی، تخصیص، پایش و گزارش |
| PER-03 | مالک ریسک/کنترل | اجرای پاسخ و نگهداری Evidence | پیشنهاد درمان، اعلام اجرا، بارگذاری شاهد |
| PER-04 | ارزیاب و ممیز | آزمون و اظهارنظر مستند | مشاهده داده مجاز، کاربرگ، ثبت یافته |
| PER-05 | بازبین/تصویب‌کننده | اعمال اختیار رسمی | قبول/رد تصمیم تحت Workflow و Scope مجاز |
| PER-06 | مدیر سیستم و امنیت | نگهداری کنترل‌های سامانه | کاربران، MFA، استقرار، اتصال، ممیزی دسترسی |
| PER-07 | مشاور/پیمانکار پیاده‌سازی | استقرار در چند مشتری | دسترسی صریح و محدود به Tenantهای تخصیص‌داده‌شده |
| PER-08 | مسئول اقدامات | اجرای وظایف روزانه | کارتابل، شواهد انجام، درخواست تأیید |

**داستان‌های کلیدی کاربر:**
1. مدیر ISMS نسخه دارای مجوز ISO 27001 را وارد کرده، کنترل‌های مشترک را به الزامات نگاشت و ارزیابی واحدها را تعریف می‌کند.
2. مالک ریسک، دارایی/فرآیند را به ریسک متصل می‌کند؛ امتیاز ذاتی/باقیمانده را با روش مصوب ثبت و برای درمان اقدام تعریف می‌کند.
3. ممیز، Evidence مربوط به کنترل را مشاهده و نتیجه آزمون، یافته و اقدام اصلاحی ایجاد می‌کند.
4. مدیر، گزارش اقدامات معوق و ریسک‌های مهم را تا رکوردهای مبدأ دنبال می‌کند.
5. کارشناس، از AI برای تهیه **پیشنویس** کنترل یا سند کمک می‌گیرد؛ شخص دارای اختیار پس از بررسی آن را ثبت/رد می‌کند.
6. اپراتور سامانه، نسخه آفلاین امضاشده را نصب و بازیابی را با شواهد عملی آزمون می‌کند.

## ۴. دامنه انتشار و مرزها

### ۴.۱ واژگان وضعیت الزام
- **CORE-IMPLEMENTED:** در کد/مدل یا API merged وجود دارد؛ آزمون عملی مشتری ممکن است باقی باشد.
- **PILOT-OBSERVED:** رفتار مشخصی روی پایلوت محلی با خروجی کاربر مشاهده/گزارش شده؛ تعمیم به Production مجاز نیست.
- **GAP:** نقص مشخص در مسیر موجود یا مانع UAT.
- **RELEASE-REQUIRED:** برای وعده نسخه محصول/پایلوت قابل تحویل باید تکمیل یا با محدودیت رسمی مستند شود.
- **POST-V1:** عمداً خارج از نسخه نخست تجاری؛ در طراحی مدل دامنه لحاظ می‌شود.
- **RIGHTS-DEPENDENT:** به محتوای دارای حق استفاده/مجوز و تأیید منبع وابسته است.

### ۴.۲ فازها
- **R0 — پایلوت فنی و اثبات هسته:** نصب آفلاین، Bootstrap، ورود، CRUD طلایی، API مجوز، گزارش، Backup/Restore در محیط مجاز.
- **R1 — کاندید انتشار مشتری:** تکمیل UX حیاتی، تست مستقل، تاریخ شمسی، محتوای مجاز، اسناد نصب، گزارش‌های تأییدشده و شواهد بازیابی.
- **R2 — توسعه سازمانی:** Connectorهای بیشتر، پایش مستمر، BIA/BCM/TPRM/Incident، تحلیل کمی پیشرفته و طراح قالب کامل.

### ۴.۳ خارج از دامنه R0/R1 مگر با قرارداد جدا
- خود نرم‌افزار اسکنر نفوذ/آسیب‌پذیری یا جایگزین SIEM/CMDB/ERP نیست.
- صدور گواهی ISO یا تأیید خودکار انطباق توسط AI ممنوع است.
- ادعای SoA رسمی تا تحقق چرخه تصویب، محتوای معتبر و اختیار قانونی ممنوع است.
- Open-Internet SaaS، SSO سازمانی، HA واقعی یا Mobile App بدون پذیرش سناریوی خاص مشتری تعهد پیش‌فرض نیست.

## ۵. نیازمندی‌های عملکردی — شناسه پایدار

**قانون:** شناسه‌ها در SRS، UX، API Contract، RTM و UAT یکسان باقی می‌مانند. درج در جدول، تضمین پیاده‌سازی نیست.

| ID | موضوع / رفتار الزامی | اولویت هدف | وضعیت مبنا |
|---|---|---|---|
| FR-ORG-001 | ایجاد Tenant و تعیین زبان/زمان/تنظیمات | P0 | CORE-IMPLEMENTED / PILOT-OBSERVED |
| FR-ORG-002 | ساختار سلسله‌مراتبی واحدها، مالک/مدیر | P0 | CORE-IMPLEMENTED |
| FR-IAM-001 | کاربران، عضویت، نقش و مجوز سازمان‌محور | P0 | CORE-IMPLEMENTED |
| FR-IAM-002 | ورود امن، MFA، نشست، خروج و مسیر ورود اجباری | P0 | CORE-IMPLEMENTED / GAP UI |
| FR-IAM-003 | ممنوعیت داده بین Tenant/Scope در تمام APIها | P0 | CORE-IMPLEMENTED؛ UAT مستقل لازم |
| FR-FWK-001 | Framework/Version/Requirement نسخه‌دار و سلسله‌مراتبی | P0 | CORE-IMPLEMENTED |
| FR-FWK-002 | واردکردن محتوای مجاز همراه provenance/licensing | P0 | CORE-IMPLEMENTED / RIGHTS-DEPENDENT |
| FR-FWK-003 | نگاشت Crosswalk با بازبینی انسانی | P1 | CORE-IMPLEMENTED / نیازمند تأیید محتوا |
| FR-CTL-001 | تعریف کنترل مشترک و ارتباط با الزامات مختلف | P0 | CORE-IMPLEMENTED |
| FR-CTL-002 | پیاده‌سازی کنترل به تفکیک Scope/مالک/وضعیت | P0 | CORE-IMPLEMENTED |
| FR-CTL-003 | آزمون کنترل با نتایج و سوابق تاریخی | P0 | CORE-IMPLEMENTED / UAT باقی |
| FR-AST-001 | ثبت دارایی، مالک، واحد، CIA، وابستگی | P0 | PILOT-OBSERVED بخشی |
| FR-CTX-001 | مدیریت فرآیند/هدف و رابطه با ریسک | P1 | CORE-IMPLEMENTED foundation |
| FR-RSK-001 | ایجاد/مشاهده/ویرایش ریسک و حفظ ارتباط با دارایی | P0 | ایجاد/لینک PILOT-OBSERVED؛ ویرایش GAP #183 |
| FR-RSK-002 | تعریف و نسخه‌بندی روش ارزیابی با آستانه/مقیاس | P0 | CORE-IMPLEMENTED؛ ایجاد UI FAIL در پایلوت |
| FR-RSK-003 | ثبت تاریخی ذاتی/جاری/باقیمانده/هدف | P0 | CORE-IMPLEMENTED؛ UAT مسدود |
| FR-RSK-004 | درمان، اقدام، پذیرش مشروط، RTP | P0 | CORE-IMPLEMENTED؛ UAT باقی |
| FR-RSK-005 | اشتهای ریسک، تحمل و استثنا | P1 | CORE-IMPLEMENTED foundation |
| FR-ASM-001 | ارزیابی الزام با Snapshot، نمره/بلوغ/اظهارنظر | P0 | CORE-IMPLEMENTED |
| FR-ASM-002 | موتور قالب/معیار ارزیابی عمومی | P1 | CORE-IMPLEMENTED foundation |
| FR-EVD-001 | Evidence دارای منشأ/Scope/Hash/اعتبار و پیوند | P0 | CORE-IMPLEMENTED |
| FR-EVD-002 | قرنطینه و کنترل امنیتی قبل از دریافت فایل | P0 | CORE-IMPLEMENTED؛ اسکنر واقعی/UAT باقی |
| FR-FND-001 | یافته و عدم انطباق با علت/شدت/مسئول | P0 | CORE-IMPLEMENTED |
| FR-ACT-001 | اقدام اصلاحی، موعد، مسئول، بازبین و شواهد | P0 | CORE-IMPLEMENTED |
| FR-AUD-001 | برنامه ممیزی، Engagement، Workpaper، Findings | P0 | CORE-IMPLEMENTED |
| FR-DOC-001 | سند نسخه‌دار، تصویب، آرشیو و ردیابی | P0 | CORE-IMPLEMENTED |
| FR-SOA-001 | دفتر پیش‌نویس کاربردپذیری با بازبینی/آمادگی | P1 | CORE-IMPLEMENTED؛ رسمی بودن **ممنوع** |
| FR-WFL-001 | Workflow/Task/Inbox/Notification بر اساس مجوز | P0 | CORE-IMPLEMENTED foundation |
| FR-RPT-001 | گزارش‌های مدیریتی/ریسک/ممیزی/اقدام و خروجی | P0 | CORE-IMPLEMENTED؛ آزمون فایل باقی |
| FR-AI-001 | AI Gateway محلی/خصوصی/سازگار با API | P1 | CORE-IMPLEMENTED؛ نصب فعلی AI خاموش |
| FR-AI-002 | RAG با مجوز قبل از Retrieval + ارجاع منبع | P1 | CORE-IMPLEMENTED foundation |
| FR-AI-003 | پیشنهاد AI با Human Review، بدون تأیید خودکار | P1 | CORE-IMPLEMENTED foundation |
| FR-CON-001 | AD/FortiGate/Veeam/Tenable خواندنی و شواهد‌محور | P1 | CORE-IMPLEMENTED؛ Live Proof باقی |
| FR-OPS-001 | سلامت سامانه، Backup، Restore، Upgrade و Logs | P0 | CORE-IMPLEMENTED؛ Recovery اثبات نشده |
| FR-LOC-001 | تقویم جلالی UI و ISO در API/DB؛ RTL دو‌زبانه | P0 برای ایران | GAP #182 |
| FR-UX-001 | CRUD کامل، خطای معنادار، ناوبری و مشخصات نشست | P0 | GAP چند مورد مشاهده‌شده |
| FR-BCM-001 | BIA/BCP/DRP و مانور | P2 | POST-V1 |
| FR-TPRM-001 | ارزیابی و ریسک تأمین‌کنندگان | P2 | POST-V1 |
| FR-INC-001 | ثبت رخداد/بحران و Lesson Learned | P2 | POST-V1 |
| FR-CCM-001 | پایش پیوسته کنترل‌ها با قواعد مستند | P2 | POST-V1 |
| FR-RPT-002 | Report/Template Designer قابل تنظیم | P2 | POST-V1 |
| FR-RSK-006 | ریسک کمی FAIR/Monte Carlo | P2 | POST-V1 |

## ۶. تجربه کاربری و نقشه اطلاعات

### ۶.۱ منوهای هدف
1. داشبورد و شاخص‌ها
2. سازمان، کاربران، اهداف، فرآیندها و دارایی‌ها
3. چارچوب‌ها، الزامات، نگاشت و ارزیابی انطباق
4. کنترل‌ها، پیاده‌سازی، آزمون و Evidence
5. ریسک، روش ارزیابی، ارزیابی تاریخی، درمان، پذیرش و RTP
6. ممیزی، یافته، CAPA و اقدامات
7. اسناد، SoA و گزارش‌ها
8. کارتابل، Workflow و اعلان‌ها
9. هوش مصنوعی، پیشنهادها و دانش سازمان
10. Connector و عملیات/تنظیمات سامانه

### ۶.۲ استاندارد همه صفحات
- فهرست: Search، Filter، Pagination، Scope، Owner، Status، Empty/Error/Loading، عملیات مجاز و Export.
- جزئیات: Header، وضعیت، مالک، تاریخچه، روابط، شواهد، اقدام بعدی، لینک به رکورد مبدأ.
- ویرایش: فرم prefilled، validation، Cancel، پاسخ سرور، Audit Trail، حفظ داده هنگام خطا.
- مسیر عمومی: احراز هویت پیش از نمایش داده محافظت‌شده؛ نمایش نام کاربر/سازمان فعال/خروج.
- فارسی/RTL واقعی؛ تاریخ قابل ورود/نمایش به شمسی با نگهداری ISO در قراردادهای فنی.
- دسترس‌پذیری با صفحه‌کلید، label معنادار، نشان‌دادن خطا بدون افشای داده، عدم اتکا صرف به رنگ.
- وضعیت AI Suggestion و Draft هرگز با Approved/Authoritative یکسان نمایش داده نشود.

**شکاف پایلوت مشاهده‌شده:** صفحه Root قبل از ورود پوسته داشبورد را نشان می‌دهد، هرچند GET ناشناس `/api/v1/dashboard/management/` با HTTP 401 رد شد؛ منو دارایی‌ها را نمایش نمی‌دهد؛ در صفحه ریسک گزینه ویرایش وجود ندارد؛ تاریخ‌ها میلادی‌اند؛ POST روش ارزیابی HTTP 400 برگردانده و UI دلیل را پنهان می‌کند.

## ۷. مدل داده و قواعد یکپارچگی

### ۷.۱ رابطه‌های بنیادین
```text
Tenant -> OrganizationUnit -> Asset / Process / Objective
Framework -> FrameworkVersion -> Requirement <-> Control
Control -> ControlImplementation -> ControlTest -> TestRun
Asset / Process -> Risk -> RiskEvaluation (historical)
Risk -> RiskTreatment -> Action; Risk <-> ControlImplementation
FrameworkVersion -> Assessment -> AssessmentItem -> Evidence
AssessmentItem / Workpaper / Control -> Finding -> Action
AuditEngagement -> Workpaper -> Finding
Document -> DocumentVersion -> DocumentApproval
SoARegister -> SoAControlDecision -> ReviewEvent
Connector -> ConnectorRun -> Evidence
Authorized Context -> AIInteraction -> AISuggestion -> Human Review
```

### ۷.۲ قواعد اجباری
- Requirement ≠ Control ≠ ControlImplementation ≠ AssessmentItem.
- Risk ≠ RiskEvaluation؛ ارزیابی‌های گذشته overwrite نمی‌شوند.
- Evidence ≠ Test ≠ Compliance Decision.
- Finding ≠ Action؛ تکمیل Action به‌تنهایی Finding را نمی‌بندد.
- Document ≠ DocumentVersion؛ تأیید ناظر بر نسخه مشخص است.
- AISuggestion ≠ Human Approval؛ مدل اجازه پذیرش خودکار ریسک ندارد.
- ConnectorFact ≠ نتیجه معتبر انطباق.
- داده بین Tenantها و Scopeها باید در Backend جدا شود.
- نسخه قفل‌شده چارچوب/ارزیابی یا Snapshot مورد تأیید نباید پنهانی تغییر کند.
- پیوند دارایی/ریسک باید Tenant و واحد سازمانی سازگار داشته باشد.

## ۸. گزارش‌ها و خروجی‌ها

**در نسخه فعلی کاتالوگ Backend وجود دارد:** SoA `draft`، RTP، Audit، Findings، Actions، Executive؛ قالب‌های اعلام‌شده بسته به گزارش PDF/DOCX/XLSX/CSV هستند، نه الزاماً همه قالب‌ها برای همه گزارش‌ها.

**مجموعه هدف:** Risk Register، Risk Heatmap، تحلیل روند، Risk Acceptance، RTP، Compliance Gap، ارزیابی بلوغ، Control Coverage/Effectiveness، Evidence Freshness، SoA Draft/Official only when authorized، Audit Plan/Report، Findings/CAPA، Action Aging، Executive/KPI، Asset/CIA، BIA/BCP/DRP (R2)، TPRM (R2)، AI Activity، Audit Trail، سلامت و Backup.

**فیلتر و سربرگ الزامی:** Tenant/Scope، Framework Version، بازه زمانی، Status، Owner، Classification؛ شماره نسخه گزارش، زمان استخراج، مرجع داده، نسخه/وضعیت تصویب، صفحه‌آرایی RTL A4 و قابلیت ردیابی به منبع. Export باید تابع همان RBAC نمای روی صفحه باشد.

## ۹. هوش مصنوعی و داده ارسالی/دریافتی

### ۹.۱ سیاست
- Authentication -> Scope Authorization -> Source Retrieval -> Classification/Minimization -> Provider Policy -> AI.
- ارسال داده حساس به بیرون فقط با Policy و مجوز صریح مشتری.
- Secret/Password/API Key هرگز بخشی از prompt یا متن Log نمی‌شود.
- Context بازیابی‌شده untrusted است؛ Prompt Injection نباید به تغییر اختیار منجر شود.
- خروجی مدل `draft/suggestion` است و برای اعمال باید مجوز و بازبینی انسانی داشته باشد.

### ۹.۲ قرارداد موجود APIها (نمونه)
- `POST /api/v1/ai/assist/risk/`: `risk_id` یا `text`، `provider_id` و `classification`.
- `POST /api/v1/ai/assist/control-mapping/`: `control_id`, `requirement_ids`.
- `POST /api/v1/ai/assist/document-draft/`: `title`, `purpose`.
- `POST /api/v1/ai/assist/rag/`: `query`؛ خروجی answer، sources و interaction.
- `AIInteraction` و `AISuggestion` منشأ، provider/model، نتیجه و وضعیت بازبینی را ثبت می‌کنند.

### ۹.۳ قرارداد هدف بعدی (نیازمند نسخه‌بندی)
`task, subject{type,id}, organization_scope, authorized_source_ids, language, output_schema_version, classification, provider_policy`؛ پاسخ `status, summary, findings[], recommendations[], source_ids[], unknowns[], review_required, model_metadata`. سرور باید schema و تمام source IDها را اعتبارسنجی کند و AI خودبه‌خود رکورد مرجع را تغییر ندهد.

## ۱۰. یکپارچه‌سازی

- **موجود به‌صورت Software Foundation:** AD/LDAP، FortiGate، Veeam، Tenable/Nessus؛ Read-only و Fact/Evidence-centric.
- **آینده:** VMware/Hyper-V، SIEM، CMDB/ITSM، Entra/M365، Zabbix، ERP/HR.
- الزامات همه Connectorها: Secret Reference، TLS Verify، جلوگیری از SSRF، Permission، زمان/Run History، Scope، Dataset Schema، Hash/Provenance، مدیریت خطا، عدم ادعای خودکار Compliance.
- GRC قرار نیست Scanner/Vulnerability Engine، SIEM یا ERP را از صفر بازسازی کند.

## ۱۱. نیازمندی‌های غیرعملکردی (NFR)

| ID | الزام | روش اثبات / مرز ادعا |
|---|---|---|
| NFR-SEC-001 | Tenant و Scope isolation، MFA، Session/CSRF، Least Privilege | تست منفی API، مرور کد، UAT مستقل |
| NFR-SEC-002 | Audit Event قابل ردیابی، Hash Chain و کنترل دسترسی به تاریخچه | آزمون تمامیت و ذخیره‌سازی |
| NFR-SEC-003 | File Quarantine و Malware Scan fail-closed | آزمون با Scanner واقعی و فایل مجاز تست |
| NFR-DEP-001 | Docker on-prem و بسته آفلاین امضاشده | نصب و verify روی Host مجاز مستقل |
| NFR-DEP-002 | بدون خروج داده در سناریوی Air-gapped/AI محلی | آزمون واقعی Egress و Network |
| NFR-REL-001 | Backup/Restore پایگاه داده، فایل‌ها و تنظیمات | مانور تخریبی روی محیط بازیابی |
| NFR-REL-002 | Upgrade/Rollback با حفظ داده و نسخه | rehearsal با صورتجلسه |
| NFR-UX-001 | فارسی RTL، تاریخ جلالی UI، ISO API و i18n | آزمون Windows/Chrome و فرم/گزارش |
| NFR-PERF-001 | سنجش p50/p95، خطا، Throughput، N+1 روی بار نماینده | بودجه کارایی باید برای هر مشتری تعیین و اندازه‌گیری شود؛ فعلاً SLO ثابت ادعا نشود |
| NFR-OBS-001 | Health، Queue/Worker/Beat، Backup Freshness و Diagnosability | پایش چندساعته و Status قابل استناد |
| NFR-DATA-001 | مهاجرت نسخه‌دار، تاریخچه محفوظ و Restore سازگار | migration/rollback test |
| NFR-LEGAL-001 | Content Rights/Provenance و جلوگیری از انتشار محتوای محدود | مجوز و تأیید منبع |
| NFR-AI-001 | Permission-safe RAG، حفاظت Prompt Injection، خطای Provider | آزمون مدل واقعی و سناریوهای خصمانه |
| NFR-OPS-001 | Secrets خارج از Repo/Issue/Log، پیکربندی امن | بررسی بسته و عملیات پشتیبانی |

**موارد غیرکمّی نیازمند تصمیم:** مقیاس بار، تعداد هم‌زمان کاربران، SLO، RPO/RTO، ظرفیت Object Storage، مدت نگهداری داده، سیاست‌های رمزنگاری، ساعات پشتیبانی و الزامات پدافند/افتا باید برای مشتری هدف عددگذاری و به قرارداد و UAT متصل شوند؛ مقادیر حدسی به‌عنوان واقعیت محصول درج نشود.

## ۱۲. معیارهای پذیرش و Golden Journeys

| ID | آزمون پذیرش حداقلی | PASS هنگامی که |
|---|---|---|
| UAT-001 | نصب آفلاین امضاشده و verify | بسته معتبر؛ همه سرویس‌ها راه‌اندازی و HTTPS API پاسخ دهد |
| UAT-002 | Bootstrap، ورود، MFA و Logout | کاربر اولیه ساخته و نشست امن/خروج و احراز هویت درست عمل کند |
| UAT-003 | سناریوی دارایی → ریسک | ارتباط صحیح، ثبت و بازیابی پس از Reload/Restart |
| UAT-004 | Methodology → Inherent/Residual Evaluation | مقیاس معتبر و امتیاز تاریخی با سطح صحیح ثبت شود |
| UAT-005 | کنترل → پیاده‌سازی → Evidence → Test | روابط مجاز و نتیجه آزمون قابل ردیابی باشد |
| UAT-006 | Framework → Assessment → Finding → CAPA | بند نسخه‌دار، شواهد و اقدام مرتبط و حفظ History |
| UAT-007 | Audit → Workpaper → Finding → Report | خروجی پرونده ممیزی و منشأ ادعا مشخص |
| UAT-008 | Draft SoA و Review | «پیش‌نویس» به‌صراحت نمایش داده شده و تصویب رسمی کاذب ممکن نباشد |
| UAT-009 | Reports/Exports | فایل‌های واقعی باز، صحیح، منطبق با مجوز و RTL قابل چاپ باشند |
| UAT-010 | Isolation/Audit | درخواست بی‌مجوز رد و تغییرات ثبت شوند |
| UAT-011 | Backup و Restore | بازگردانی جداگانه DB/Object و سنجش واقعی بازیابی |
| UAT-012 | AI/Connector در صورت فعال‌سازی | بدون نشت، با Provider/Target واقعی، پیشنهاد انسانی |
| UAT-013 | تقویم شمسی و RTL | ورود، نمایش، چاپ و تبدیل تاریخ بدون جابه‌جایی روز |

## ۱۳. شواهد وضعیت پایلوت ۲۰۲۶-۱۰-۱۳

**تأییدشده فقط در دامنه پایلوت محلی و بر اساس خروجی اپراتور:**
- بسته آفلاین تستی امضاشده از Source SHA دقیق نصب شد؛ Compose و خدمات اصلی اجرا شدند.
- `datacenterctl install` خروجی 0 و `https/live`, `https/ready` وضعیت HTTP 200 داشتند.
- نخستین Tenant و کاربر آزمایشی `pilotadmin` ساخته شد؛ صفحه `/login` و ورود موفقیت‌آمیز بود.
- درخواست ناشناس `GET /api/v1/dashboard/management/` با HTTP 401 رد شد.
- داشبورد فارسی در مرورگر دیده شد؛ دارایی `TEST-ASSET-001` بعد از Refresh باقی ماند؛ ریسک `TEST-RISK-001` ایجاد شد.
- بررسی مستقیم read-only DB تأیید کرد `risk.asset.code == TEST-ASSET-001` و سازمان/واحد یکسان است.

**موارد باز/FAIL:**
- روش ارزیابی اولیه از UI ایجاد نشد: `POST /api/v1/risk-methodologies/` با HTTP 400؛ خروجی پاسخ/علت هنوز استخراج نشده و هیچ RiskEvaluation موفق گزارش نشده است.
- ویرایش ریسک در UI غایب است (#183)؛ تقویم میلادی است (#182)؛ وضعیت نشست/منو نیازمند اصلاح.
- Operational status اولیه `critical` به‌دلیل نبود Record برای backup و Beat→Worker heartbeat؛ دو هشدار Django deploy.
- کلید امضای Release و TLS تستی‌اند؛ نصب Host مستقل، Restore مخرب، محتوای مجاز/اتصالات واقعی/AI واقعی، نفوذ مستقل و UAT مشتری هنوز قبول نشده‌اند.

## ۱۴. اولویت‌های اجرایی، ریسک‌ها و تصمیم‌های باز

### P0 فوری — برای رفع انسداد UAT و ایمنی
1. عیب‌یابی قطعی HTTP 400 روش ارزیابی، نمایش خطای معتبر سرور و آزمون RiskEvaluation.
2. بررسی Login Redirect، Session Refresh/CSRF، Tenant selection و RBAC مسیرهای حساس.
3. تولید گزارش RTP/Executive و بررسی کیفیت واقعی فایل‌های خروجی.
4. رفع هشدارهای deploy و ثبت Heartbeat/Backup؛ اجرای Recovery Drill کنترل‌شده.
5. ثبت و مدیریت Failure/Blockerها بدون دست‌کاری داده یا اعلام PASS کاذب.

### P1 برای تجربه قابل عرضه در ایران
- ویرایش امن ریسک و سایر CRUDهای ناقص؛ منو، نام کاربر/سازمان و Logout.
- شمسی‌سازی جامع (#182)، RTL و قالب گزارش فارسی.
- اولین اجرای onboarding استاندارد/روش ارزیابی/کنترل؛ پیام‌های خطای شفاف.
- تأمین و بازبینی حقوق محتوای واقعی و UAT سناریوی استاندارد.

### P2 Post-v1
BCM/BIA/DRP، Incident، TPRM، CCM، کمّی‌سازی پیشرفته ریسک، Report/Template Designer، Mobile/PWA، AI Agentهای محدود.

### تصمیم‌های باز (DEC)
- DEC-001: آیا اولین مشتری SSO/IdP مشخص دارد؟ در غیر این صورت Password+MFA کافی است.
- DEC-002: سطح تعهد RTO/RPO و تعداد کاربر/حجم شواهد چیست؟
- DEC-003: چه محتواهای دارای حق استفاده برای ISO/AFTA به‌طور قانونی قابل ارائه هستند؟
- DEC-004: کدام گزارش رسمی به تأیید/امضا نیاز دارد و مرجع تصویب آن کیست؟
- DEC-005: سیاست انتقال داده به Provider ابری و سطح محرمانگی چگونه است؟
- DEC-006: مدل Licensing و بسته‌بندی تجاری با چه محدودیت‌هایی عرضه می‌شود؟

## ۱۵. وابستگی‌های اسناد

- **PRD (این سند):** چرا/چه چیزی/دامنه و اولویت.
- **SRS/FRD:** نیازمندی عملیاتی ریز و رفتار خطا/مجوز/عملیات.
- **Data Dictionary + ERD:** مدل موجودیت، فیلد، کلید، قید، رابطه و مهاجرت.
- **API/AI Contract:** درخواست و پاسخ، امنیت و نسخه‌بندی.
- **UX/Screen Specification:** منو، صفحه، فیلد، فرم، رفتار و جریان کار.
- **RTM:** ارتباط هر FR/NFR با پیاده‌سازی، تست و شاهد.
- **UAT/Test Plan:** سناریو، پیش‌شرط، مراحل، انتظار، PASS/FAIL، شواهد.
- **Deployment/Support:** نصب، امضا، Backup/Restore، Recovery، امنیت.

منبع اجرای واقعی همچنان **کد و Migrationهای merged روی `main`** است؛ این PRD قرار نیست بر رفتار فعلی کد یا مستندات حقوقی اولویت غیرواقعی پیدا کند.

## ۱۶. معیار تأیید PRD

پیش از `APPROVED` شدن این نسخه:
- مالک محصول دامنه R0/R1/R2 را تأیید کند.
- تیم توسعه ناسازگاری‌های FR/NFR را با کد و API فعلی بررسی کند.
- مسئول امنیت محدودیت‌های Tenant/RBAC/AI/Data-Egress را تأیید کند.
- مسئول مستندسازی الزامات منبع و Copyright را بررسی کند.
- معیارهای پذیرش هر ماژول به Test Case و Issue/PR مرتبط شوند.
- هیچ وضعیت «پایان‌یافته» صرفاً بر مبنای وجود کد یا screenshot اعلام نشود.

---
**منابع داخلی:** `README.md`، `docs/product/PRODUCT_BRAIN_FA.md`، `FEATURE_MAP_FA.md`، `UX_PRODUCT_SPEC_FA.md`، `AI_AUTOMATION_DIRECTION.md`، `docs/architecture/CANONICAL_DOMAIN_MODEL_V2.md`، `docs/FINAL_RELEASE_ACCEPTANCE.md` و شواهد آزمون #161، مسائل #182 و #183.
