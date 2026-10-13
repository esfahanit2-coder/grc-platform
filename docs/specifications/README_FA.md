# مجموعه مشخصات رسمی طراحی محصول GRC — فهرست و کنترل اسناد

> **Document Register ID:** GRC-SPEC-INDEX-000 · **نسخه:** 0.1.0  
> **وضعیت همه اسناد این مجموعه:** **DRAFT / برای بازبینی** · **تاریخ پایه:** ۱۴۰۵/۰۷/۲۱ (2026-10-13)  
> **Source baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691` · **Installed trial:** `pilot-20261013-r1`
>
> **این مجموعه برای طراحی و توسعه محصول است؛ نه گواهی انطباق، تأیید امنیت مستقل، پذیرش مشتری یا مجوز فروش به‌عنوان Production Ready.**

## ۱. ترتیب خواندن و کاربرد

| ترتیب | شناسه | سند | مخاطب و کاربرد |
|---|---|---|---|
| ۱ | GRC-PRD-001 | [Product Requirements Document](GRC-PRD-001_FA.md) | مالک محصول، مدیران، دامنه و اولویت |
| ۲ | GRC-SRS-002 | [Software/Functional Requirements](GRC-SRS-002_FA.md) | Backend/Frontend؛ رفتار، داده، مجوز، خطا |
| ۳ | GRC-DATA-003 | [Data Dictionary & Conceptual ERD](GRC-DATA-003_FA.md) | Database/Backend؛ مدل و روابط موجود/هدف |
| ۴ | GRC-API-AI-004 | [API/AI Interface & Security Contract](GRC-API-AI-004_FA.md) | Backend/AI/Integration؛ As-Is و To-Be |
| ۵ | GRC-UX-005 | [Screen Catalog & RTL UX Specification](GRC-UX-005_FA.md) | UX/Frontend؛ مسیرها، فرم‌ها، حالت‌ها |
| ۶ | GRC-RTM-006 | [Requirements Traceability Matrix](GRC-RTM-006_FA.md) | PM/QA؛ اتصال FR/NFR به تست و شاهد |
| ۷ | GRC-UAT-007 | [Acceptance & Evidence Test Plan](GRC-UAT-007_FA.md) | QA/Operator/Customer؛ مراحل، انتظار، گیت |

## اسناد تکمیلی سطح ماژول (افزوده‌شده)

| شناسه | سند | کاربرد |
|---|---|---|
| GRC-RISK-101 | [مشخصات تفصیلی مدیریت ریسک](modules/GRC-RISK-101_FA.md) | تمام فیلدهای Risk/Method/Evaluation/Treatment/Appetite/Acceptance، قواعد، API، UI، AI، گزارش و Gapها |
| GRC-RISK-UAT-102 | [آزمون‌های تفصیلی مدیریت ریسک](modules/GRC-RISK-UAT-102_FA.md) | ۱۳ سناریوی مثبت و ۲۰ سناریوی منفی، شواهد و گیت پذیرش |

**وضعیت:** DRAFT؛ اسناد جدید هیچ کد یا Migrationی را تغییر نمی‌دهند. مسائل #161، #182 و #183 همچنان باز و مرتبط‌اند.

## ۲. اصول کنترل سند
- شناسه و نسخه ثابت باشند؛ هر تغییر محتوای مهم به PR و Change Log نیاز دارد.
- اصطلاح `existing/implemented` بر اساس کد/مدل merged تفسیر شود؛ `observed` فقط وقتی خروجی آزمون مربوطه وجود دارد.
- `blocked/not-run` با `passed` هم‌ارز نیست.
- `DRAFT` تا تأیید Product Owner و Tech Lead و Security و QA باقی بماند.
- این مجموعه هیچ Schema Migration، Code Change یا اصلاح Runtime ایجاد نمی‌کند.
- در صورت اختلاف با کد، `main` و Migration مرجع رفتار اجرایی هستند و سند اصلاح می‌شود؛ برای جهت محصول تصمیم رسمی Product Owner لازم است.
- داده و اسناد واقعی مشتری، Secrets و محتوای محدود استانداردها در Repo عمومی نوشته نشوند.

## ۳. توالی ایجاد/تکمیل اسناد تکمیلی
| مرحله | سند تکمیلی | معیار تکمیل |
|---|---|---|
| A | Logical/Physical ERD و Migration Matrix دقیق | FK/Unique/Index/Constraint با Migrationهای موجود کنترل شود |
| B | OpenAPI قرارداد کامل مسیرها + خطا و RBAC | از Schema اجرای نسخه واقعی استخراج و Diff شود |
| C | Spec سطح فرم/فیلد هر ماژول و Figma Screen Flow | همه 46 Route بررسی و فرم‌ها به API/Permission متصل شوند |
| D | Report/Document Templates Catalog | برای هر خروجی Layout، داده، نسخه، Workflow و File Test تعریف شود |
| E | AI Context Schema/Tool Policy/Red-team Scenarios | برای هر Task قرارداد ورودی/خروجی و فیلتر منابع و Human Review |
| F | Database Migration & Upgrade/Rollback Design | Test Data، Backward Compatibility، Restore |
| G | Security Architecture / Threat Model / Test Evidence | STRIDE، Cross-Tenant، File/Connector/AI، Pentest |
| H | Deployment/Operations/Support Runbooks | بر مبنای Runbookهای فعلی، اثبات Host مستقل و Backup/Restore |
| I | Commercial Product Licensing/Packaging | دامنه بسته‌ها، تعهد پشتیبانی، فعال‌سازی آفلاین |
| J | Customer Acceptance Pack و Sign-off | همه Gateهای واقعی Customer PASS و محدودیت‌ها مکتوب |

**اولویت در ضرب‌الاجل پایلوت:** P0/P1 نصب و Workflow آزمایش واقعی قبل از افزودن ویژگی‌های Post-v1.

## ۴. مرجع‌های موجود که نباید بی‌دلیل بازنویسی شوند
- `docs/product/PRODUCT_BRAIN_FA.md` — تفکر محصول
- `docs/product/FEATURE_MAP_FA.md` — نقشه قابلیت‌ها
- `docs/product/UX_PRODUCT_SPEC_FA.md` — قواعد RTL و تجربه کاربری
- `docs/product/AI_AUTOMATION_DIRECTION.md` — مرزهای AI
- `docs/architecture/CANONICAL_DOMAIN_MODEL_V2.md` — معماری دامنه هدف
- `docs/architecture/ERD_V2_MIGRATION_MATRIX.md` — ماتریس مهاجرت موجود
- `docs/FINAL_RELEASE_ACCEPTANCE.md` و `docs/DATACENTER_OPERATIONS.md` — الزامات پذیرش و استقرار
- `README.md`، `ARCHITECTURE.md`، `RELEASE_BLOCKERS.md` — وضعیت کد/Release

## ۵. موضوعات آشکار از آزمون واقعی
- روش ارزیابی Risk: `POST /risk-methodologies/` پاسخ HTTP 400 داده؛ پیش از ادعای کارکرد محاسبه ریسک باید پاسخ خطا تشخیص/رفع و UAT-004 اجرا شود.
- Edit ریسک UI ندارد — #183.
- تقویم شمسی لازم است — #182.
- Bootstrap/HTTPS/Login/Asset Persistence و Risk FK در پایلوت محلی با شواهد اپراتور ثبت شده‌اند — #161.
- Heartbeat/Backup و 2 Warning Django هنوز به شواهد تکمیلی نیاز دارند.

## ۶. راهنمای تصویب
- Product Owner: تأیید دامنه و اولویت R0/R1/R2.
- Technical Lead: تأیید سازگاری با کد و راهبرد پیاده‌سازی.
- Security Lead: کنترل Tenant/Scope/Egress/AI/Secrets.
- QA Lead: پوشش Test IDs و وجود Evidence.
- Content/Legal Reviewer: حقوق استفاده و بازتوزیع Frameworkها.
- Operator/Customer: استقرار، بازیابی و UAT واقعی در محیط مجاز.

**وضعیت امضا و تصویب همه نقش‌ها در این نسخه: PENDING.**

### مدیریت کنترل‌ها — اسناد سطح ماژول

| شناسه | سند | محتوای تحویلی |
|---|---|---|
| GRC-CONTROL-201 | [مشخصات تفصیلی مدیریت کنترل‌ها](modules/GRC-CONTROL-201_FA.md) | فیلدها، روابط، نگاشت به چارچوب‌ها، چرخه اجرا و آزمون، Evidence، RBAC، API، AI و گزارش‌ها |
| GRC-CONTROL-UAT-202 | [آزمون تفصیلی مدیریت کنترل‌ها](modules/GRC-CONTROL-UAT-202_FA.md) | ۱۳ تست مثبت و ۲۰ تست منفی؛ مرزهای اثربخشی، مجوز و پذیرش |

**یادداشت انتشار:** این دو سند DRAFT هستند و نسخه جاری `pilot-20261013-r1`، کد اجرایی، تنظیمات و اطلاعات پایگاه داده را تغییر نمی‌دهند. موارد Effectiveness بدون Review و UI ناقص Control Test به‌عنوان شکاف طراحی/آزمون ثبت شده‌اند.
