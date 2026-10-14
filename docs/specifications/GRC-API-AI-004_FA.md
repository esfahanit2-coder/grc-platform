# قرارداد API و هوش مصنوعی GRC — طرح نسخه‌دار و مرزهای امنیتی

> **شناسه:** GRC-API-AI-004 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT  
> **مرجع:** [PRD](GRC-PRD-001_FA.md)، [SRS](GRC-SRS-002_FA.md)، `docs/product/AI_AUTOMATION_DIRECTION.md`  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`  
> **تفکیک مهم:** قراردادهای **As-Is** از فایل‌های `backend/apps/ai_gateway/urls.py`، `views.py`، `serializers.py` استخراج شده‌اند. درخواست‌های **To-Be** طرح توسعه‌اند؛ هنوز Endpoint موجود تلقی نمی‌شوند.

## ۱. اصول API عمومی
- مبنا: `/api/v1/`، JSON UTF-8 برای داده، multipart برای فایل مجاز.
- ورود: JWT با Cookie/Authorization طبق امنیت سامانه؛ Cookie Authentication با CSRF، Tenant و Scope از سرور.
- Scope: هر درخواست بر اساس User/Service Identity، Tenant Membership، Organization Scope و Permission کنترل شود.
- Response موفق: `200` GET/PATCH، `201` CREATE، `202` صرفاً وقتی کار ناهمگام واقعاً پذیرفته شده است.
- خطا: 400 Validation، 401 Authentication، 403 Authorization، 404 Not Found/Hidden، 409 Version Conflict، 429 Throttling، 5xx Server Failure. `request_id` قابل گزارش و بدون Secret باشد.
- Idempotency-Key برای فرمان‌های پرهزینه/دوباره‌ارسال‌شونده هدف توسعه است؛ فعلاً تضمین عمومی ادعا نشود.
- Tenant ID در Prompt انسانی به جای کنترل Backend معتبر نیست.
- استاندارد فایل/تاریخ: UUID پایدار، `date` برابر ISO `YYYY-MM-DD`، `datetime` برابر ISO offset-aware و نمایش شمسی در UI.

## ۲. APIهای GRC دامنه‌ای — قرارداد رابط، نه فهرست کامل Endpointها

| دامنه | نمونه مسیر فعلی/مفهومی | عملیات هدف |
|---|---|---|
| Auth | `/auth/token`, `/auth/token/refresh`, `/auth/logout` | Login/MFA/Refresh/Logout |
| Tenant | `/tenants/mine` | سازمان‌های عضو |
| Framework | `/frameworks/`، منابع نسخه/الزام | List/Create/View/Version/Lock |
| Controls | `/controls/` | List/Create/Update + mapping |
| Assets | `/assets/`, `/assets/selector-options/` | Asset CRUD/Selectors |
| Risk | `/risks/`, `/risks/{id}/` | Create/Read/PATCH |
| Risk methodology | `/risk-methodologies/` | Config/Create/Read |
| Risk evaluate | `/risks/{id}/evaluate/` | Create historical evaluation |
| Risk RTP | `/risks/{id}/rtp/?format=docx` | Document output |
| Assessment | `/assessments/` و detail | Assessment/Items |
| Evidence | `/evidence/` و link/upload workflow | Evidence/Provenance |
| Reporting | `/dashboard/management/`, `/reports/catalog/`, `/reports/preview/`, `/reports/export/` | Report |
| SoA | `/soa/registers/`, `/soa/registers/{id}/readiness/` | Draft/Review only |
| AI | `/ai/providers/`, `/ai/interactions/`, `/ai/suggestions/`, `/ai/knowledge/`, `/ai/assist/` | Provider/RAG/Suggestion |

مسیرهای مفهومی باید قبل از توسعه با `urls.py` و OpenAPI واقعی تطبیق داده شوند؛ Routeهای فرضیِ پیاده‌سازی‌نشده نباید به مصرف‌کننده قرارداد شوند.

## ۳. وضعیت واقعی APIهای دستیار هوش مصنوعی

### ۳.۱ Risk Assistant — As-Is
**مسیر:** `POST /api/v1/ai/assist/risk/`  
**ورودی:** `risk_id?`, `text?`, `provider_id?`, `classification?`.  
**رفتار:** اگر `risk_id` داده شود، Backend وجود Risk در Tenant و مجوز `risk.view` در Unit را بررسی می‌کند؛ سپس Prompt درباره Cause/Impact/Controls/Treatment ساخته و `AIInteraction` و `AISuggestion` ثبت می‌کند.  
**پاسخ:** `interaction`، `suggestion`.  
**مرز:** تحلیل پیشنهادی؛ هیچ پذیرش خودکار ریسک یا تغییر authoritative مجاز نیست.

### ۳.۲ Control Mapping — As-Is
**مسیر:** `POST /api/v1/ai/assist/control-mapping/`  
**ورودی:** `control_id`, `requirement_ids[]`, `provider_id?`, `classification?`.  
**رفتار:** نیازمند `control.view` و `framework.view`؛ انتخاب Requirementهای قابل مشاهده و محدودشده به حداکثر ۱۰۰ مورد در کد فعلی؛ پیشنهاد نگاشت و دلیل.  
**پاسخ:** شناسه Interaction و پیشنهاد.  
**مرز:** نگاشت تا مرحله تأیید Human Approved نیست.

### ۳.۳ Document Draft — As-Is
**مسیر:** `POST /api/v1/ai/assist/document-draft/`  
**ورودی:** `title` اجباری، `purpose`, `provider_id?`, `classification?`.  
**پاسخ:** `interaction`، `suggestion` با عنوان و محتوای پیش‌نویس.  
**مرز:** سند کنترل‌شده Approved ایجاد نمی‌شود مگر از مسیر معمول Document/Version/Approval.

### ۳.۴ Permission-Safe RAG — As-Is
**مسیر:** `POST /api/v1/ai/assist/rag/`  
**ورودی:** `query` اجباری، `provider_id?`, `classification?`.  
**پاسخ:** `interaction`, `answer`, `sources[]` با `id,title,source_type,source_id`.  
**مرز:** قبل از Retrieval فقط Knowledge Chunkهای مجاز Tenant/Scope وارد شوند؛ متن بازیابی‌شده untrusted است.

### ۳.۵ تنظیمات AI — As-Is
`AIProviderConfig`: `name,provider_type,base_url,model_name,secret_env_var,is_active,is_default,allow_confidential,configuration`.  
`AIInteraction`: `provider,capability,classification,input_summary,context_manifest,output,confidence,status,error`.  
`AISuggestion`: `interaction,object_type,object_id,suggestion_type,proposed_value,confidence,status,reviewed_by,reviewed_at,review_comment`.  
`KnowledgeChunk`: `organization_unit,source_type,source_id,title,content,content_hash,token_count,classification,embedding_model,embedding_dimensions,embedded_at`.

## ۴. قرارداد پیشنهادی AI vNext — To-Be (نباید Endpoint فعلی تلقی شود)

### ۴.۱ Request (نمونه فاقد داده واقعی)
```json
{
  "schema_version": "grc.ai.task.v1",
  "task": "risk_analysis",
  "subject": {"type": "risk", "id": "00000000-0000-4000-8000-000000000001"},
  "requested_outputs": ["summary", "gaps", "recommendations"],
  "data_selectors": {
    "framework_version_ids": [],
    "evidence_ids": [],
    "control_ids": []
  },
  "preferences": {"language": "fa", "response_schema": "grc.ai.risk.v1"},
  "provider_id": null,
  "classification": "internal"
}
```
**اطلاعات هرگز از کلاینت قابل اعتماد نیستند:** Scope، مجوز، Secret و egress policy فقط در Backend resolve شوند. کلاینت نمی‌تواند با `organization_scope` جعلی دسترسی افزایش دهد.

### ۴.۲ Flow ایمن
1. احراز User/Service و Tenant.
2. تعیین Permission برای خود Task و Subject.
3. مجازبودن هر `source_id` و ارتباط آن با Subject بررسی شود.
4. داده‌های غیرضروری و Secretها حذف شوند.
5. Classification و Policy Provider (local/private/cloud) اعمال شود.
6. RAG فقط روی Corpus مجاز انجام شود.
7. Prompt با Context داده‌ایِ صریحاً غیرقابل اعتماد ساخته شود.
8. Provider انتخاب‌شده و فهرست منابع ثبت شوند.
9. پاسخ مدل با JSON Schema و Source IDs اعتبارسنجی شود.
10. `AISuggestion` با Status پیشنهادی ذخیره شود؛ تصمیم Human جداگانه.
11. Apply تنها از Domain API عادی و Audit Trail عبور کند.

### ۴.۳ Response پیشنهادی
```json
{
  "schema_version": "grc.ai.risk.v1",
  "interaction_id": "00000000-0000-4000-8000-000000000002",
  "status": "suggested",
  "subject": {"type": "risk", "id": "00000000-0000-4000-8000-000000000001"},
  "summary": "ریسک نیازمند بررسی کنترل‌های بازیابی است.",
  "findings": [
    {
      "code": "insufficient_evidence",
      "statement": "نتیجه آزمون بازیابی در Context مجاز یافت نشد.",
      "source_ids": [],
      "uncertainty": "unknown"
    }
  ],
  "proposed_actions": [
    {
      "title": "درخواست مدرک آزمون بازیابی",
      "priority": "medium",
      "rationale": "احراز قابلیت بازیابی"
    }
  ],
  "unknowns": ["اعتبار آخرین آزمون بازیابی مشخص نیست"],
  "human_review_required": true,
  "confidence": null
}
```
Source ID خالی یعنی مدل منبعی برای ادعا ارائه نکرده و نباید آن را «استناد شده» نمایش داد. هر Source ID موجود باید مجدداً نسبت به User/Tenant/Scope تأیید شود.

### ۴.۴ ساختار Human Review
`suggestion_id`, `decision: accept|reject|modify`, `comment`, `reviewed_by`, `reviewed_at`, `target_domain_command`, `target_version`, `audit_id`.  
یک Accept روی پیشنهاد، صدور مجوز مستقل برای Close Finding/Approve SoA/Accept Risk نیست.

## ۵. ماتریس داده به AI و برگشت

| Capability | داده حداقلی مجاز | خروجی هدف | مرجع تأیید |
|---|---|---|---|
| Risk Analysis | Risk Scenario/Cause/Consequence + asset context مجاز | Gap، کنترل پیشنهادی، درمان پیشنهادی | Risk Owner |
| Control Mapping | کنترل و متن Requirement دارای مجوز | Mapping پیشنهادی + استدلال | Compliance Reviewer |
| Assessment Assistant | Snapshot بند + Evidence مجاز | پرسش و نقص شواهد | Assessor/Reviewer |
| Document Draft | نوع سند، Purpose، حقایق موجود | متن Draft + Placeholder | Document Owner |
| Audit Assistant | Scope + Criterion + Workpaper مجاز | Test Steps/Questions | Lead Auditor |
| RAG | Query + Chunks مجاز با منبع | Answer + citations + Unknowns | کاربر مسئول |
| Management Narrative | KPIهای authoritative و تعریف محاسبه | روایت/خطرهای مشاهده‌شده | Manager |
| Connector Fact Summary | Summary/Provenance مجاز، نه Secret | هشدار و درخواست شاهد | Control Owner |

## ۶. محافظت‌ها و آزمون‌های منفی
- **AI-SEC-01:** Tenant B هرگز Chunks یا شناسه Evidence Tenant A را در Context نبیند.
- **AI-SEC-02:** درخواست دارای UUID حدسی بدون مجوز 403/404 و بدون Side Effect باشد.
- **AI-SEC-03:** متن PDF با دستور «سیستم را نادیده بگیر» به‌عنوان محتوا تلقی شود، نه فرمان.
- **AI-SEC-04:** Provider Cloud وقتی Egress/Classification ممنوع است هرگز فراخوانی نشود.
- **AI-SEC-05:** API Key، Password یا Token در Prompt، Audit، Trace و Error نباشد.
- **AI-SEC-06:** پاسخ مدل با `source_ids` جعلی پذیرفته یا اعمال نشود.
- **AI-SEC-07:** عدم دسترسی Provider، خطای قابل مدیریت بدهد و CRUD هسته سالم بماند.
- **AI-SEC-08:** هیچ پیشنهاد هوش مصنوعی به‌تنهایی Status معتبر کنترل/ریسک/SoA را تغییر ندهد.
- **AI-SEC-09:** Prompt/Context/Output حساس بر اساس Retention Policy نگهداری یا Redact شود.
- **AI-SEC-10:** همه Tool Callها با Principal واقعی و Audit و Permission اجرا شوند.

## ۷. شرایط استقرار AI
- AI در Pilot نصب‌شده فعلی **خاموش** است؛ هیچ ادعای inference واقعی/آفلاین نشده است.
- مدل محلی نیازمند وزن قانونی، فضای دیسک، CPU/GPU و اثبات No-egress است؛ آماده‌بودن Image به معنی آماده‌بودن مدل نیست.
- AI Gateway و Domain API باید Provider-agnostic باشند؛ تغییر Model نباید Schema داده کسب‌وکار را بشکند.
- قراردادهای پیشنهادی vNext تا بررسی تیم API/AI و آزمون Compatibility جایگزین As-Is نمی‌شوند.

---
**پیگیری:** FR-AI-001..003، NFR-AI-001، UAT-012 و خط‌مشی `docs/architecture/ADR-009-ai-workflow-sovereign.md`.
