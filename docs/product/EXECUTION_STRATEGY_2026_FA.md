# GRC Platform | راهبرد محصول و نقشه راه اجرایی ۱۴۰۵ / ۲۰۲۶

**تاریخ بررسی:** 2026-10-09  
**شاخه مبنا:** `main@50659cbbc219e0e1e3c58c9b0ede0568ed7cd0fa`  
**وضعیت:** سند تصمیم‌سازی/برنامه‌ریزی، نه تأیید تولید یا ادعای عبور از پذیرش.  
**پیگیری:** #105، برنامه انتشار #68 و آزمون نهایی #74.

## ۱. تصمیم اجرایی

GRC Platform باید یک محصول **بومی، چندچارچوبی، نصب‌شونده در دیتاسنتر مشتری، فارسی/انگلیسی، دارای شواهد قابل ممیزی و قابل استفاده بدون اینترنت** باشد. عرضه نرم‌افزار اولویت تجاری است؛ خدمات مشاوره/استقرار درآمد مکمل و مرحله بعد است. مشتریان نخست: سازمان‌های متوسط و بزرگ دارای الزامات امنیت، ممیزی و حسابرسی و سازمان‌های حساس به نگهداری محلی داده. صادرات در گام بعد و با محتوای دارای مجوز و بومی‌سازی بازار مقصد.

**تصمیم صریح: بازنویسی ممنوع**؛ معماری Django/DRF + Next.js + PostgreSQL/pgvector + Redis/Celery + S3-compatible در قالب Modular Monolith حفظ شود. «چارچوب‌ها محتوا هستند، نه کد». کنترل مشترک و شواهد مشترک نقطه مرکزی محصول‌اند؛ تصمیم‌های حساس AI و Connector خودکار تأیید نمی‌شوند.

## ۲. وضعیت واقعی مبنا

در `main` هسته‌های زیر پیاده‌سازی شده‌اند و دارای تست/بستر نرم‌افزاری‌اند:
- tenancy، ساختار سازمانی، scoped RBAC، MFA و audit trail؛
- Framework/Version/Requirement، Control/Implementation، دارایی/ریسک، RiskEvaluation و RTP؛
- Assessment، Evidence، Finding/Action/CAPA، Internal Audit و Control Test؛
- Document lifecycle، Reporting Center (از جمله SoA/RTP)، Work Center/Workflow؛
- AI gateway، RAG با فیلتر مجوز، Connectorهای خواندنی AD/LDAP، FortiGate، Veeam و Tenable/Nessus؛
- داشبورد، عملیات، Docker/pilot/offline-release tooling، CI/SAST/SBOM و ابزار تست/بازیابی.

این فهرست **معادل آمادگی نصب مشتری نیست**. `README.md` و `RELEASE_BLOCKERS.md` هنوز صریحاً Pilot Candidate / pre-RC اعلام کرده‌اند. هیچ موفقیت CI جای آزمون محیط واقعی را نمی‌گیرد.

پیشرفت معماری: Canonical Domain Model v2 و ERD/Migration Matrix در #96/#97 در main؛ Domain Object Registry در #103 به main راه یافته؛ #104 آغاز Wave 2 برای Objective/BusinessProcess است. PRهای بازِ قدیمی #87/#90/#92/#101 باید پیش از هر ادغام مجدد با main بازبینی و بسته/جایگزین شوند؛ صرفاً عنوان آنها دلیل merge نیست.

## ۳. Benchmark رقبای خارجی و درس محصول

| خانواده/نمونه | ارزش قابل اقتباس (بدون کپی کد/رابط/محتوا) | خطری که برای محصول ما روشن می‌کند |
|---|---|---|
| ServiceNow IRM | اتصال Risk/Compliance/Operations، پایش و ارجاع کار | فرم‌ها بدون اتصال به عملیات روزمره کنار گذاشته می‌شوند |
| Archer، MetricStream، IBM OpenPages | دامنه سازمانی گسترده، پیکربندی‌پذیری، نقش‌های مختلف | پیچیدگی و هزینه استقرار نباید تجربه مشتری متوسط را نابود کند |
| Optro (AuditBoard سابق)، Diligent | ممیزی، شواهد، همکاری و گزارش‌دهی اجرایی | Audit/Evidence باید workflow واقعی داشته باشد نه checklist |
| LogicGate | فرآیندهای قابل پیکربندی و Integration | سفارشی‌سازی امن از ساخت fork برای هر مشتری بهتر است |
| OneTrust، Vanta/Drata/Hyperproof | اتوماسیون شواهد، privacy و compliance monitoring | Connector باید Fact تولید کند؛ قضاوت انطباق جدا باشد |
| CISO Assistant (AGPL/community + commercial) | جداسازی Domain، mapping، library import و تنوع چهارچوب | رقیب جدی برای feature breadth؛ مزیت ما باید نصب مستقل، محتوای ایران، تجربه RTL و خدمات عملیاتی باشد |
| eramba، SimpleRisk | workflow ساده و ثبت risk/control/policy | time-to-value و آموزش/پذیرش مهم‌تر از فهرست بلند قابلیت‌هاست |

**مرزبندی:** مقایسه بر پایه مستندات/اظهارات منتشرشده فروشندگان است، نه اجرای آزمایش هم‌شرایط. اعداد قیمت، تعداد مشتری، تطابق قانونی و عملکرد محصول خارجی بدون بررسی مستقل نباید در فروش به‌عنوان واقعیت قطعی ادعا شوند. از کد AGPL، متن ISO/COBIT، قالب اختصاصی رقبا یا نگاشت‌های مالکیتی بدون بررسی حق استفاده تجاری کپی نشود.

منابع: 
- https://www.servicenow.com/uk/products/integrated-risk-management.html
- https://www.ibm.com/products/openpages
- https://optro.ai/auditboard-to-optro
- https://www.logicgate.com/platform/integrations/thehive/
- https://github.com/intuitem/ciso-assistant-community
- https://www.eramba.org/get-community

## ۴. بازار داخلی و خلأ قابل فروش

نمونه‌های بررسی‌شده: Sooratec GRC، Fortress GRC (Farzan)، Daya GRC/VA و ISOAFZAR؛ سایر نمونه‌های ثبت‌شده در `COMPETITIVE_LANDSCAPE.md` باید از نظر موجود بودن نسخه فعلی و امکان دمو مجدد ارزیابی شوند. ادعاهای محصولِ فروشندگان، برابر با اثبات قابلیت نیستند.

- Sooratec: تمرکز معرفی بر حاکمیت، ممیزی داخلی، ریسک، کنترل و انطباق؛
- Fortress/Farzan: در کاتالوگ منتشرشده ارزیابی شکاف، بلوغ، فرم/فرآیندساز، دارایی، ریسک، ممیزی، اسناد و گزارش؛
- ISOAFZAR: ISMS/ITIL، چرخه اسناد، کارتابل، فرم‌ساز، مدیریت ریسک و گزارش؛
- Daya GRC/VA: مدیریت ریسک و انطباق/ارزیابی آسیب‌پذیری بر اساس معرفی محصول.

موقعیت پیشنهادی ما: **زنجیره قابل رهگیری هدف/فرآیند/دارایی → ریسک → کنترل و اجرا → مدرک/آزمون → ارزیابی/ممیزی → یافته/اقدام → گزارش رسمی** + نگاشت چنداستانداردی و استقرار محرمانه. هیچ ادعای «اولین»، «تنها» یا تأییدیه افتا بدون سند رسمی مجاز نیست.

منابع: https://samanitg.com/ ؛ https://farzan-group.net/wp-content/uploads/catalog/GENERAL.pdf ؛ https://amnafzar.net/products/isoafzar-information-security-management-system ؛ https://bankbridge.net/products/grc/

## ۵. سبد استاندارد و حقوق محتوا

| چارچوب | نقش در محصول | اولویت و احتیاط |
|---|---|---|
| ISO/IEC 27001:2022 + Amd 1:2024 | ISMS، SoA، Risk Treatment، ارزیابی | P0، متن فقط با مجوز یا داده مجاز مشتری |
| AFTA / الزامات نهادهای داخلی | سناریوی بازار ایران | P0، provenance و مجوز و نسخه‌بندی، بدون ادعای تأیید رسمی |
| ISO 31000:2018 | روش‌شناسی مدیریت ریسک | P0/P1؛ راهنماست، نه استاندارد صدور گواهی |
| COBIT 2019 | حاکمیت و مدیریت فناوری اطلاعات | P1؛ mapping به اهداف و کنترل‌های مشترک، با مجوز محتوا |
| **ISO 9001:2026** | کیفیت و مدیریت فرآیند | P1؛ نسخه جدید **2026-09-16** منتشر شده؛ 2015 و 2026 باید نسخه‌های مجزا باشند؛ migration/crosswalk با human review |
| NIST CSF 2.0 | راهبری امنیت و اولویت‌بندی ریسک | P1؛ `Govern` از عملکردهای اصلی است |
| ISO 37301:2021، ISO/IEC 42001:2023 | Compliance/AI Governance | P2 و فقط با نیاز بازار/حقوق محتوا |
| سایر حوزه‌ها مانند پدافند غیرعامل/تاب‌آوری | محتوای اختصاصی مشتری/مجاز | بدون ادعای پوشش یا اخذ مجوز سازمانی |

محدودیت حقوقی: تأیید داشتن لایسنس *نرم‌افزار* هیچ حقی برای توزیع متن استاندارد ایجاد نمی‌کند. هر Content Pack دارای ناشر، منبع، تاریخ، نسخه، scope، حق استفاده و checksum باشد. هیچ Importی نباید داده مشتری A را در Pack عمومی مشتری B منتشر کند.

منابع: https://committee.iso.org/standard/27001 ؛ https://www.iso.org/standard/9001 ؛ https://www.iso.org/standard/65694.html ؛ https://www.isaca.org/resources/cobit ؛ https://www.nist.gov/cyberframework ؛ https://www.iso.org/standard/42001

## ۶. دو مسیر موازی با دروازه‌های جدا

### Track R — رساندن Pilot به محصول قابل استقرار (اولویت تجاری P0)

| گام | تحویل قابل مشاهده | وابستگی | معیار خروج / Evidence |
|---|---|---|---|
| R0: تثبیت مبنا | فریز SHA/manifest، پاکسازی PRهای تکراری، بازبینی API/security، CI | #40 #68 | snapshot و release checklist قابل تکرار؛ قواعد حفاظت main فعال |
| R1: Golden User Journeys | onboarding، Scope/RBAC، ریسک/ارزیابی، مدرک، اقدام، ممیزی، سند، گزارش، dashboard، i18n/RTL | #42 #68 | هر مسیر با دیتای نماینده بدون shortcut و با نقش‌های واقعی اجرا شود |
| R2: محتوای مجاز | حداقل یک Pack ISMS/AFTA و یک crosswalk کنترل مشترک | #5 | provenance/licensing + مصوبه انسانی mapping + خروجی SoA/RTP |
| R3: Integration | اتصال عملی به حداقل سه خانواده منبع با اجازه مشتری | #6 | لاگ read-only، Evidence با hash/source/زمان و handling خطا |
| R4: Clean-host | نصب آفلاین روی host پاک، TLS، MFA، backup/restore، migration/rollback، no-egress AI، health | #7 #68 | سنجش واقعی RPO/RTO، فیلم/لاگ/صورتجلسه آزمون و acceptance signed |
| R5: امنیت و بار | pentest مستقل، retest، audit integrity، malware scan، auth/IDOR/cross tenant، workload واقعی | #8 #40 | بدون آسیب‌پذیری بحرانی/بالای بازِ موردپذیرش‌نبوده، مستند sign-off |
| R6: پذیرش/فروش | UAT دو نقش کاربردی+ادمین، راهنمای نصب/پشتیبانی، قرارداد و licensing، داده نمونه مجاز | #74 | سازمان آزمایشی با runbook بدون کمک توسعه‌دهنده استفاده کند |

**قاعده انتشار:** RC فقط وقتی ساخته/ترویج شود که شروط محیط واقعی R2-R6 و تصویب سازمانی انجام شده باشد. نسخه قابل‌نمایش فروش و نسخه production یکی نیستند.

### Track D — نوسازی تدریجی Enterprise Domain (بدون توقف Track R)

| موج | حوزه | Ticket | شرط ایمنی |
|---|---|---|---|
| D0 | Domain Object Registry | #100/#103 | در main؛ PR قدیمی #101 با وضعیت merge ارزیابی شود |
| D1 | Objective و BusinessProcess + روابط صریح | #104 | migrations افزایشی، hierarchy بدون چرخه، tenant-safe، عدم backfill اجباری |
| D2 | Risk Appetite/Tolerance/Acceptance | Issue مجزا | پذیرش ریسک از RiskTreatment و RiskEvaluation جدا؛ تاریخچه محفوظ |
| D3 | generic AssessmentTemplate/Criterion/Profile | Issue مجزا | backfill تدریجی و immutable historical snapshots |
| D4 | Control EffectivenessConclusion | Issue مجزا | نتیجه آزمون ≠ نتیجه مصوب، single source of authority |
| D5 | KPI/KRI/KCI metric foundation | Issue مجزا | provenance/threshold/observations، صرفاً مشاهدات Connector |
| D6 | Commercial Edition/Entitlements | Issue مجزا | جدا از Content license، حالت کاملاً آفلاین و عدم قفل‌کردن داده مشتری |
| D7 | Content Pack v2 / template expansion | Issue مجزا | همه اجزاء optional/نسخه‌دار و non-executable |

Track D نباید migration یا API شکست‌دهنده وارد release branch کند؛ Feature flag/compatibility adapter و rollback لازم است. Full rewrite، microservices، generic universal FK و hard-coded standard engine مجاز نیست.

## ۷. معیار سنجش ارزش واقعی

اندازه‌گیری در یک Pilot واقعی و با baseline قبل/بعد، نه اعداد تبلیغاتی:

1. **Time to first value:** مدت نصب تا نخستین ارزیابی کامل + خروجی رسمی.
2. **Evidence reuse:** نسبت شواهد پذیرفته‌شده مرتبط به بیش از یک requirement/control با اعتبار scope.
3. **Cycle time:** مدت ارجاع تا بستن یافته با review.
4. **Adoption:** کاربران فعال نقش‌های مالک کنترل/ریسک/ممیز در دوره Pilot.
5. **Operational readiness:** موفقیت clean-host، restore، upgrade/rollback، عدد واقعی RPO/RTO.
6. **Security:** عدم نشت بین tenantها، نرخ عبور تست authorization منفی، نتیجه pentest و re-test.
7. **Usability:** سهم workflowهایی که بدون دخالت توسعه‌دهنده تکمیل می‌شوند؛ خطا/زمان کاربر.
8. **Supportability:** عیب‌یابی از health/log/support bundle بدون credential و secret.

اهداف عددی SLO/ظرفیت/زمان راه‌اندازی باید پس از اندازه‌گیری روی سخت‌افزار نماینده تعیین و تصویب شوند، نه از زمان GitHub Runner استنتاج شوند.

## ۸. بسته‌بندی محصول و بازار

پیشنهاد نسخه‌های تجاری (طرح اولیه، نه تصمیم نهایی قیمت):
- **Core:** Framework/Control/Risk/Assessment/Evidence/Actions/Documents/Reports/RTL.
- **Professional:** Audit، Workflow پیشرفته، API/Connectorهای منتخب، AI محلی با پذیرش انسانی.
- **Enterprise:** SSO سازمانی بر اساس پروتکل واقعی، HA/DR، monitoring، entitlement و پشتیبانی پیشرفته.

**اصل مهم:** نسخه تجاری = انتخاب دسترسی ماژول، نه fork کد برای مشتری. پیشنهاد قرارداد: حق استفاده نرم‌افزار/پشتیبانی/به‌روزرسانی، استقرار، آموزش و توسعه‌های سفارشی جداگانه. صحت این بسته‌بندی باید با مصاحبه حداقل ۳ خریدار احتمالی و دریافت بازخورد روی دمو سنجیده شود.

## ۹. ظرفیت و ترتیب اجرا (برآورد برنامه‌ریزی، نه تعهد زمانی)

با تیم فرضی ۱ Backend، ۱ Frontend، ۱ Full-stack/QA، DevOps/Security پاره‌وقت و Product Owner:
- هفته ۱–۲: baseline، PR cleanup، Priority freeze، سناریوهای UAT، مجوز استاندارد، host plan؛
- هفته ۳–۶: user journeys و اصلاح UX/RTL، داده دمو غیرحساس، اسناد و workflow؛
- هفته ۵–۹: integration proof، content proof، install و restore روی میزبان؛
- هفته ۸–۱۲: تست امنیت مستقل، اصلاحات، UAT و پذیرش Pilot؛
- هفته ۱۲–۱۶: release hardening، handbook، commercial demo؛
- موج‌های D به PRهای کوچک مستقل تقسیم می‌شوند و اجرای آنها نباید R-gates را عقب بیندازد.

این بازه‌ها **مشروط** به دسترسی به میزبان، استاندارد مجاز، دستگاه‌های اتصال واقعی، افراد مسئول و تست نفوذ هستند؛ در صورت کمبود این‌ها پیشرفت نرم‌افزاری ممکن است اما RC قابل اعلام نیست.

## ۱۰. اولین پنج اقدام قابل اجرا بدون زیرساخت مشتری

1. نگهداری `main` به‌عنوان SSOT و پاکسازی/تعیین‌تکلیف PRهای stale؛ بررسی Ruleset توسط Administrator (#40).
2. ساخت UAT golden scripts نقش‌محور و gap list برای صفحات فارسی (#42/#74).
3. اجرای Wave 2 فقط در PR مستقل و با مهاجرت افزایشی (#104).
4. تعریف Content Pack مجاز و جدول نسخه/حقوق برای ISO 27001، AFTA و ISO 9001:2026 (#5).
5. آماده‌کردن اسکریپت، داده و فرم Evidence برای روز استقرار واقعی (#6/#7/#8)، بدون ادعای عبور از آنها.

**تصمیم نهایی:** سرعت توسعه خوب است، اما اولویت محصول باید «قابل نصب و قابل استفاده بودن با شواهد پذیرفته‌شده» باشد. اضافه‌کردن BCM/TPRM/Incident/FAIR/AI Governance قبل از پذیرش v1، مگر با سفارش مشخص مشتری، اولویت پایین دارد.

---
**تاریخ بازبینی بعدی:** با بسته‌شدن هر Release Gate یا تغییر نسخه رسمی استاندارد/مقررات؛ تاریخ این سند برای ارزیابی منابع و نسخه‌ها حیاتی است.
