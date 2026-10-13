# مشخصات صفحات و تجربه کاربری (UX / Screen Catalog) — GRC Platform

> **شناسه:** GRC-UX-005 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT  
> **Baseline مسیرهای بررسی‌شده:** `frontend/app/**/page.tsx` در `main@e7a745c47919f6ec028e429c210bbdfd4589c691`  
> **قاعده:** `PRESENT` یعنی Route در Source وجود دارد؛ **به معنی قبولی CRUD یا UAT نیست**. `TARGET` یعنی نیاز طراحی.

## ۱. اصول UI
- زبان پیش‌فرض فارسی با `dir=rtl`؛ کد، UUID، آدرس، IP و اعداد فنی LTR به‌صورت موضعی.
- تاریخ ورودی/نمایشی کاربران ایرانی **جلالی**؛ ذخیره/API ISO Gregorian (FR-LOC-001، #182).
- «پیش‌نویس»، «پیشنهاد AI»، «جمع‌آوری خودکار»، «منتظر بازبینی»، «تأییدشده»، «ردشده» در رنگ و متن جدا شوند.
- حساب واردشده، Tenant فعال، محدوده سازمانی و خروج باید آشکار باشند.
- ناوبری ماژول‌ها بر اساس Permission و نقش؛ نمایش صفحه ناخواسته بدون مجوز با خطای معنادار.
- فرم‌ها: Label و راهنما، اجبار/اختیاری، Select Option معتبر، Validation هم‌زمان و سرور، Cancel، جلوگیری از Double Submit.
- فهرست‌ها: Search، Filtering، Pagination، Sort، Export در صورت مجوز، Loading/Empty/Error.
- جزئیات: Header، Owner، Status، Relations/Traceability، History، Evidence، Action و Audit، breadcrumb.
- اطلاعات بدون ارزیابی باید `ارزیابی‌نشده` نشان دهند؛ صفر سبز معنی «ایمن» ندارد.
- Browser Console نباید برای دیدن پیام ساده HTTP 400 لازم باشد؛ Body اعتبارسنجی به فیلد فرم وصل شود.
- Responsive و Keyboard navigation در محدوده Tablet و لپ‌تاپ آزمون شود.

## ۲. نقشه کامل Routeهای موجود

| ID صفحه | Route فعلی | نیازمندی مرتبط | ارزیابی وضعیت |
|---|---|---|---|
| UI-001 | `/` | FR-RPT-001 | PRESENT + authenticated screenshot |
| UI-002 | `/login` | FR-IAM-002 | PRESENT + Pilot login PASS |
| UI-003 | `/admin/onboarding` | FR-ORG-001 | PRESENT؛ UAT باقی |
| UI-004 | `/organization` | FR-ORG-002/FR-CTX-001 | PRESENT |
| UI-005 | `/admin/users` | FR-IAM-001 | PRESENT |
| UI-006 | `/admin/roles` | FR-IAM-001 | PRESENT |
| UI-007 | `/settings/security` | FR-IAM-002 | PRESENT |
| UI-008 | `/admin/data-exchange` | FR-FWK-002 | PRESENT |
| UI-009 | `/admin/operations` | FR-OPS-001 | PRESENT؛ سلامت اولیه Critical |
| UI-010 | `/frameworks` | FR-FWK-001 | PRESENT |
| UI-011 | `/frameworks/new` | FR-FWK-001 | PRESENT |
| UI-012 | `/frameworks/[id]` | FR-FWK-001 | PRESENT |
| UI-013 | `/frameworks/import` | FR-FWK-002 | PRESENT |
| UI-014 | `/frameworks/crosswalk` | FR-FWK-003 | PRESENT |
| UI-015 | `/controls` | FR-CTL-001/002 | PRESENT + pilot screenshot |
| UI-016 | `/controls/[id]` | FR-CTL-002 | PRESENT |
| UI-017 | `/control-tests` | FR-CTL-003 | PRESENT |
| UI-018 | `/assets` | FR-AST-001 | PRESENT + pilot CREATE/PERSIST PASS |
| UI-019 | `/assets/[id]` | FR-AST-001 | PRESENT |
| UI-020 | `/risks` | FR-RSK-001 | PRESENT + pilot CREATE |
| UI-021 | `/risks/[id]` | FR-RSK-001/003/004 | PRESENT + **ویرایش ندارد** #183 |
| UI-022 | `/risks/methodologies` | FR-RSK-002 | PRESENT + POST 400 FAIL |
| UI-023 | `/risks/governance` | FR-RSK-005 | PRESENT |
| UI-024 | `/assessments` | FR-ASM-001 | PRESENT |
| UI-025 | `/assessments/[id]` | FR-ASM-001 | PRESENT |
| UI-026 | `/assessments/history` | FR-ASM-001 | PRESENT |
| UI-027 | `/assessments/generic` | FR-ASM-002 | PRESENT |
| UI-028 | `/evidence` | FR-EVD-001 | PRESENT |
| UI-029 | `/findings` | FR-FND-001 | PRESENT |
| UI-030 | `/findings/[id]` | FR-FND-001 | PRESENT |
| UI-031 | `/actions` | FR-ACT-001 | PRESENT |
| UI-032 | `/actions/[id]` | FR-ACT-001 | PRESENT |
| UI-033 | `/audits` | FR-AUD-001 | PRESENT |
| UI-034 | `/audits/[id]` | FR-AUD-001 | PRESENT |
| UI-035 | `/documents` | FR-DOC-001 | PRESENT |
| UI-036 | `/soa` | FR-SOA-001 | PRESENT؛ فقط Draft |
| UI-037 | `/soa/[id]` | FR-SOA-001 | PRESENT؛ فقط Draft/Review |
| UI-038 | `/reports` | FR-RPT-001 | PRESENT |
| UI-039 | `/work` | FR-WFL-001 | PRESENT |
| UI-040 | `/workflows` | FR-WFL-001 | PRESENT |
| UI-041 | `/notifications` | FR-WFL-001 | PRESENT |
| UI-042 | `/ai` | FR-AI-001 | PRESENT؛ AI Runtime فعلی خاموش |
| UI-043 | `/ai/suggestions` | FR-AI-003 | PRESENT |
| UI-044 | `/settings/ai` | FR-AI-001 | PRESENT |
| UI-045 | `/connectors` | FR-CON-001 | PRESENT؛ Live Proof باقی |
| UI-046 | `/settings/integrations` | FR-CON-001 | PRESENT |

## ۳. دسته‌بندی هدف منوی اصلی

1. داشبورد و شاخص‌ها
2. سازمان، اهداف، فرآیندها، دارایی‌ها و خدمات
3. چارچوب‌ها، انطباق و ارزیابی‌ها
4. کنترل‌ها، پیاده‌سازی و آزمون‌ها
5. ریسک‌ها، روش‌ها، درمان و پذیرش
6. شواهد، ممیزی، یافته و اقدامات
7. اسناد، SoA و گزارش‌ها
8. کارتابل، گردش‌کار و اعلان
9. هوش مصنوعی، دانش و پیشنهادها
10. یکپارچه‌سازی و مدیریت سیستم

منو باید قابلیت جمع/بازکردن، جست‌وجوی سراسری و دسترسی مستقیم به صفحه Details داشته باشد؛ Route موجود اما خارج از منوی فعلی (مانند `/assets`) یک نقص UX است.

## ۴. قرارداد نمونه صفحات کلیدی

### UI-001 — داشبورد
**KPIها:** درصد انطباق، ریسک‌های بالا/بحرانی (بر پایه ارزیابی معتبر باقیمانده)، یافته‌های باز، اقدامات معوق، کنترل‌های مؤثر، ارزیابی‌های دارای سررسید.  
**بخش‌ها:** نقشه حرارتی ریسک، خلاصه Framework، پیشرفت ارزیابی‌ها، ریسک‌های برتر، اقدامات نیازمند توجه، سررسیدها.  
**رفتار:** هر KPI Drill-down به منبع، نمایش `No Assessment` در داده خالی، Refresh و زمان آخرین بروزرسانی.  
**مشاهده پایلوت:** تصویر واقعی، صفرها و Empty State بدون Error Banner؛ محاسبه KPI با داده غنی هنوز آزمایش نشده است.

### UI-018 — دفتر دارایی‌ها
**فیلد فرم موجود:** Code، Title، Type، OrganizationUnit، Owner، Custodian، Confidentiality، Integrity، Availability، Criticality، Status، Description.  
**رفتار:** گزینه‌های Owner/Unit از Endpoint مجاز؛ بدون Unit یا Owner ثبت نشود؛ Error از Backend؛ Cancel/Refresh؛ لینک Detail.  
**مشاهده پایلوت:** `TEST-ASSET-001` ایجاد و بعد از Reload باقی مانده است.

### UI-020/021 — دفتر و جزئیات ریسک
**Create:** Code، Title، Unit، Asset اختیاری، Owner، Scenario، Cause، Consequence، ReviewDate.  
**Detail:** نوع ارزیابی و تاریخچه، سناریو/علت/پیامد، پیوند Asset، Treatment، Action، RTP.  
**TARGET Edit:** فرم prefilled، PATCH، شرط Unit/Asset سازگار، مجوز risk.manage، Audit و Feedback.  
**مشاهده پایلوت:** Asset↔Risk در DB برقرار؛ کاربر رابطه را در Detail واضح پیدا نمی‌کند و Edit UI ندارد (#183).

### UI-022 — مدیریت روش ریسک
**Form موجود:** دکمه + روش 5×5، نام از Browser Prompt، بقیه مقادیر ثابت 1..5 و Thresholdهای 1-4/5-9/10-16/17-25.  
**TARGET:** فرم واقعی فارسی با نام، نوع، Scale، Formula، Threshold، Default، Validation و نسخه؛ `400` دقیق Field-level.  
**مشاهده پایلوت:** `POST /api/v1/risk-methodologies/` = HTTP 400؛ **ارزیابی ریسک UAT BLOCKED** تا تشخیص علت.

### UI-024/025 — ارزیابی انطباق
**Flow:** انتخاب Framework Version قفل‌شده، Scope و Owner؛ فهرست Requirement Snapshot؛ Evidence Links؛ Status/Score/Maturity؛ Assessor و Reviewer؛ Findings و Actions.  
**قواعد:** N/A با دلیل؛ Score و Progress مستقل؛ Review ثبت‌شده و Trail.

### UI-028 — Evidence
**Flow:** Upload → Quarantine → Scan/Clean → Scope/Classification → Link → Review → Reuse → Expiry.  
**افزوده UX:** فایل‌های Pending/Rejected/Expired تفکیک؛ Download فقط Clean؛ نمایش Provenance/Hash.

### UI-036/037 — SoA Draft
**نمایش:** هر تصمیم Included/Excluded/Undecided + Rationale، ControlImplementation/Treatment/Evidence، خوانش Readiness و Human Feedback.  
**هشدار ثابت:** «پیش‌نویس — نه SoA رسمی/تأییدشده». هیچ دکمه Approve/Sign واقعی تا تکمیل Gate نباشد.

### UI-038 — Reporting
**ساختار:** انتخاب گزارش/Scope/Filter، Preview، PDF/DOCX/XLSX/CSV مطابق Catalog.  
**قواعد:** Scope در Preview و Export یکسان، Draft Label در خروجی، تاریخ شمسی در فایل فارسی، Audit export.

### UI-042/043 — AI
**ساختار:** موضوع/دامنه منابع، نوع Task، Provider مجاز، Privacy Notice، پیشنهاد با Source/Uncertainty، Accept/Modify/Reject، Audit.  
**قواعد:** خروجی AI هرگز «Approved» به‌طور پیش‌فرض؛ AI Disabled، فعالیت GRC Core را غیرفعال نکند.

### UI-009 — عملیات
**محتوا:** Health DB/Redis/ObjectStore/Gateway، Queue، Beat↔Worker، Backup Freshness، Release SHA/Images، Notifications خطا و لینک Runbook.  
**مرز:** `Container Running` با `Operational Ready` یکی نیست؛ وضعیت `critical` دقیقاً نشان داده شود.

## ۵. الگوی خطاها

| پاسخ سرور | رفتار مطلوب |
|---|---|
| 400 | نمایش متن Field Validation و پیشنهاد اصلاح؛ نه «ثبت ناموفق بود» صرف |
| 401 | Refresh کنترل‌شده؛ اگر نشد، Login و حفظ مقصد امن |
| 403 | «مجوز کافی ندارید» با Scope و نام عملیات |
| 404 | عدم وجود/دسترس‌نبودن، بدون نشت داده |
| 409 | اعلام تغییر نسخه/بازبینی منسوخ؛ Reload ایمن |
| 429 | نمایش تأخیر و محدودیت نرخ |
| 5xx | پیام عمومی + Request ID برای پشتیبانی |

## ۶. چک‌لیست طراحی و تست صفحه
- [ ] RTL فارسی و متن‌های فنی LTR صحیح
- [ ] نام کاربر/سازمان و Breadcrumb
- [ ] Role/Scope درست در سرور و UI
- [ ] Search/Filter/Pagination/Empty/Loading/Error
- [ ] Create/View/Edit/Cancel (در صورت اجازه دامنه)
- [ ] روابط قابل مشاهده و لینک‌دار
- [ ] تاریخ شمسی با Roundtrip صحیح
- [ ] پیام موفقیت/خطای قابل اقدام
- [ ] Keyboard/Responsive/Contrast
- [ ] Refresh و Persistence
- [ ] Download/Export با مجوز معتبر
- [ ] Audit Trail در تغییرات حساس

**خروجی مرحله بعد:** برای هر Route یک Sheet یا Figma Frame دارای «فیلد/مدل/Endpoint/Permission/Use Case/Test ID» آماده شود؛ این سند، کاتالوگ مرجع مسیرهاست، نه فایل طراحی Figma تکمیل‌شده.
