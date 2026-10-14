# ماتریس ردیابی نیازمندی‌ها (RTM) — GRC Platform

> **شناسه:** GRC-RTM-006 · **نسخه:** 0.1.0 · **وضعیت:** DRAFT  
> **Baseline:** `main@e7a745c47919f6ec028e429c210bbdfd4589c691`  
> **مراجع:** [PRD](GRC-PRD-001_FA.md)، [SRS](GRC-SRS-002_FA.md)، [DATA](GRC-DATA-003_FA.md)، [UX](GRC-UX-005_FA.md)، [UAT](GRC-UAT-007_FA.md)

## ۱. قواعد شواهد
- `LOCAL-PASS`/ `OBSERVED`: فقط برای آزمون مشخص در محیط محلی، نه مشتری/Production.
- `PARTIAL`: یک زیرسناریو اجرا/مشاهده شده ولی همه معیارهای پذیرش خیر.
- `NOT-RUN`: حتی اگر کد موجود است، آزمون واقعی بر اساس سند اجرا نشده.
- `BLOCKED`: مانع شناخته‌شده؛ با PASS یا SKIP اشتباه نشود.
- `EXTERNAL-PROOF`: نیازمند محیط/دستگاه/مجوز مستقل.
- `RIGHTS-DEPENDENT`: به محتوای دارای مجوز وابسته است.
- `POST-V1`: خارج از Release نخست.
- به‌روزرسانی ستون وضعیت نیازمند `evidence_url / test_date / tester / target_commit_or_release / environment` است.

## ۲. ردیابی FR
| Requirement | قابلیت | صفحه | مدل/سرویس | Test Case | وضعیت امروز | پیگیری |
|---|---|---|---|---|---|---|
| FR-ORG-001 | Tenant bootstrap | UI-003 | Tenant, TenantMembership | UAT-002 | OBSERVED-PARTIAL | #161 |
| FR-ORG-002 | Unit hierarchy | UI-004 | OrganizationUnit | UAT-003 | NOT-RUN | — |
| FR-IAM-001 | RBAC/Membership | UI-005/006 | Role, UserRoleScope | UAT-010 | NOT-RUN | — |
| FR-IAM-002 | Auth/MFA/Logout | UI-002/007 | MFADevice, Auth | UAT-002 | OBSERVED-PARTIAL | #161 |
| FR-IAM-003 | Tenant isolation | All | TenantQuery/Scopes | UAT-010 | NOT-RUN | — |
| FR-FWK-001 | Framework/version | UI-010/011/012 | FrameworkVersion,Requirement | UAT-006 | NOT-RUN | — |
| FR-FWK-002 | Content import/licensing | UI-008/013 | Framework,LicenseMetadata | UAT-006 | RIGHTS-DEPENDENT | #5 |
| FR-FWK-003 | Crosswalk review | UI-014 | RequirementMapping | UAT-006 | NOT-RUN | — |
| FR-CTL-001 | Common Controls | UI-015 | Control,ControlRequirement | UAT-005 | NOT-RUN | — |
| FR-CTL-002 | Implementation | UI-016 | ControlImplementation | UAT-005 | NOT-RUN | — |
| FR-CTL-003 | Control testing | UI-017 | ControlTestRun | UAT-005 | NOT-RUN | — |
| FR-AST-001 | Asset registration | UI-018/019 | Asset,AssetDependency | UAT-003 | OBSERVED-PARTIAL | #161 |
| FR-CTX-001 | Process/objective | UI-004 | BusinessProcess,Objective | UAT-003 | NOT-RUN | — |
| FR-RSK-001 | Risk CRUD/link | UI-020/021 | Risk,RiskControl | UAT-003 | OBSERVED-CREATE-ONLY | #183 |
| FR-RSK-002 | Methodology | UI-022 | RiskMethodology | UAT-004 | BLOCKED-HTTP400 | #161 |
| FR-RSK-003 | Risk evaluation history | UI-021 | RiskEvaluation | UAT-004 | BLOCKED-BY-METHOD | #161 |
| FR-RSK-004 | Treatment/accept/RTP | UI-021/038 | RiskTreatment,RiskAcceptance | UAT-004/009 | NOT-RUN | — |
| FR-RSK-005 | Appetite/tolerance | UI-023 | RiskAppetiteStatement,RiskTolerance | UAT-004 | NOT-RUN | — |
| FR-ASM-001 | Compliance assessment | UI-024/025/026 | Assessment,AssessmentItem | UAT-006 | NOT-RUN | — |
| FR-ASM-002 | Generic assessment | UI-027 | TemplateCriterion,GenericAssessmentRun | UAT-006 | NOT-RUN | — |
| FR-EVD-001 | Evidence provenance | UI-028 | Evidence,EvidenceLink | UAT-005/006 | NOT-RUN | — |
| FR-EVD-002 | Quarantine/scan | UI-028 | Evidence + Scanner boundary | UAT-005 | EXTERNAL-PROOF | #8 |
| FR-FND-001 | Finding | UI-029/030 | Finding | UAT-006/007 | NOT-RUN | — |
| FR-ACT-001 | Corrective action | UI-031/032 | Action | UAT-006/007 | NOT-RUN | — |
| FR-AUD-001 | Audit/workpaper | UI-033/034 | AuditEngagement,Workpaper | UAT-007 | NOT-RUN | — |
| FR-DOC-001 | Controlled documents | UI-035 | DocumentVersion,DocumentApproval | UAT-007/009 | NOT-RUN | — |
| FR-SOA-001 | Draft SoA | UI-036/037 | SoARegister,SoAControlDecision | UAT-008 | NOT-RUN | #143 |
| FR-WFL-001 | Workflow/Inbox | UI-039/040/041 | WorkflowInstance,Notification | UAT-006/007 | NOT-RUN | — |
| FR-RPT-001 | Reports/exports | UI-001/038 | FormalReports | UAT-009 | NOT-RUN | — |
| FR-AI-001 | AI gateway | UI-042/044 | AIProviderConfig | UAT-012 | DISABLED-LOCAL | #8 |
| FR-AI-002 | Permission safe RAG | UI-042 | KnowledgeChunk | UAT-012 | NOT-RUN | #8 |
| FR-AI-003 | AI suggestions/review | UI-043 | AISuggestion | UAT-012 | NOT-RUN | — |
| FR-CON-001 | Read-only connectors | UI-045/046 | ConnectorConfig,ConnectorRun | UAT-012 | EXTERNAL-PROOF | #6 |
| FR-OPS-001 | Operations/backup | UI-009 | datacenterctl | UAT-001/011 | PARTIAL-CRITICAL | #161 |
| FR-LOC-001 | Jalali dates | All date forms | UI date adapter | UAT-013 | GAP | #182 |
| FR-UX-001 | Full CRUD/error/nav | All | Frontend + API | UAT-003/004 | GAP | #183 |
| FR-BCM-001 | BCM/BIA/DRP | TARGET | New domain | R2-UAT | POST-V1 | — |
| FR-TPRM-001 | Third party risk | TARGET | New domain | R2-UAT | POST-V1 | — |
| FR-INC-001 | Incident | TARGET | New domain | R2-UAT | POST-V1 | — |
| FR-CCM-001 | Continuous monitoring | TARGET | New domain | R2-UAT | POST-V1 | — |
| FR-RPT-002 | Report designer | TARGET | New domain | R2-UAT | POST-V1 | — |
| FR-RSK-006 | FAIR/quantitative | TARGET | New domain | R2-UAT | POST-V1 | — |
## ۳. ردیابی NFR
| Requirement | معیار | آزمون | وضعیت فعلی |
|---|---|---|---|
| NFR-SEC-001 | RBAC/Tenant isolation | UAT-010 | NOT-RUN |
| NFR-SEC-002 | Audit integrity | UAT-010 | NOT-RUN |
| NFR-SEC-003 | Malware scanner | UAT-005 | EXTERNAL-PROOF |
| NFR-DEP-001 | Offline signed install | UAT-001 | LOCAL-PASS |
| NFR-DEP-002 | Airgap egress policy | UAT-012 | NOT-RUN |
| NFR-REL-001 | Backup/restore | UAT-011 | NOT-RUN |
| NFR-REL-002 | Upgrade/rollback | UAT-011 | NOT-RUN |
| NFR-UX-001 | Jalali/RTL | UAT-013 | GAP |
| NFR-PERF-001 | Load | LOAD-001 | NOT-RUN |
| NFR-OBS-001 | Heartbeat/Backup freshness | UAT-001 | CRITICAL-INITIAL |
| NFR-DATA-001 | Migration/history | UAT-011 | PARTIAL |
| NFR-LEGAL-001 | Content licensing | RIGHTS-001 | RIGHTS-DEPENDENT |
| NFR-AI-001 | AI/RAG security | UAT-012 | DISABLED-LOCAL |
| NFR-OPS-001 | Secrets handling | UAT-001 | LOCAL-PARTIAL |
## ۴. شواهد اولیه قابل قبول از پایلوت
- Source: `e7a745c47919f6ec028e429c210bbdfd4589c691`؛ test signed release: `pilot-20261013-r1`؛ Windows WSL2/Docker Desktop، نه Host مستقل.
- `START_EXIT_CODE=0`; Containerهای اصلی اجرا؛ HTTPS API `live/ready` هر دو HTTP 200.
- `BOOTSTRAP_EXIT_CODE=0`; Login user test و tenant session موفق.
- Anonymous GET dashboard API=401؛ این نتیجه فقط همان Endpoint را اثبات می‌کند.
- Asset `TEST-ASSET-001` پس از Refresh باقی مانده و Risk `TEST-RISK-001` ایجاد شده؛ FK در Django DB به‌صورت read-only تأیید شد.
- Creation methodology UI با HTTP 400 رد شد؛ Score ریسک هنوز محاسبه/ثبت/تأیید نشده است.
- Initial operational critical: Beat/Worker heartbeat و Backup not_recorded؛ Django deploy 2 warning.
- Test certificate و key فقط برای پایلوت‌اند؛ Recovery/UAT مستقل/Production signing و Security approval هنوز انجام نشده است.

## ۵. قالب ثبت اجرای موردی (برای هر تست)
```yaml
requirement_id: FR-RSK-002
test_case_id: UAT-004
environment: local-wsl2-test
release: pilot-20261013-r1
source_sha: e7a745c47919f6ec028e429c210bbdfd4589c691
tester: operator
execution_date: 2026-10-13
status: BLOCKED
observed: "POST /api/v1/risk-methodologies/ = HTTP 400"
expected: "201 with active methodology"
evidence_url: "https://github.com/esfahanit2-coder/grc-platform/issues/161"
defect_issue: "ISSUE-TBD"
```

## ۶. کنترل کیفیت RTM
- همه FRهای PRD باید در RTM و حداقل یک Test وجود داشته باشند؛ شناسه‌های Orphan پذیرفته نیستند.
- تست اجرا‌نشده هرگز `PASS` نمی‌گیرد.
- تغییر Requirement باید مسیر `PRD → SRS → Data/API/UX → Test → Evidence` را به‌روز کند.
- پیش از Merge باید Product Owner وضعیت‌ها و QA Lead Test Evidence را بازبینی کنند.
- زمان‌بندی R0/R1/R2 در `PRD` مرجع است؛ RTM تغییر دامنه مجاز نمی‌دهد.

## ۷. ردیابی تفصیلی ماژول مدیریت ریسک

اسناد سطح ماژول:
- [GRC-RISK-101](modules/GRC-RISK-101_FA.md): Field Dictionary، روابط، State Machine، API، UI، هوش مصنوعی، گزارش و شکاف‌ها.
- [GRC-RISK-UAT-102](modules/GRC-RISK-UAT-102_FA.md): ۱۳ سناریوی مثبت + ۲۰ مورد منفی؛ پذیرش اجرای واقعی نیازمند شواهد است.

| Requirement | آزمون جزئی | وضعیت اولیه |
|---|---|---|
| FR-RSK-001 | RSK-TC-001, 002؛ NEG-01..03,09 | ثبت/FK PARTIAL؛ Edit BLOCKED |
| FR-RSK-002 | RSK-TC-003؛ NEG-04,06,07 | POST HTTP 400، BLOCKED |
| FR-RSK-003 | RSK-TC-004, 005؛ NEG-05,08 | BLOCKED به‌دلیل Method |
| FR-RSK-004 | RSK-TC-006, 011؛ NEG-11,18 | NOT-RUN |
| FR-RSK-005 | RSK-TC-007..010؛ NEG-12..16,19 | NOT-RUN |
| FR-AI-001/002/003 | RSK-TC-013؛ NEG-20 | AI خاموش؛ NOT-RUN |
| FR-LOC-001 | RSK-TC-012 | FAIL برای رابط جلالی (#182) |
| FR-UX-001 | RSK-TC-002,003 | GAP ویرایش/خطای فرم |
| FR-RPT-001 | RSK-TC-011؛ NEG-10 | NOT-RUN |

## ۸. ردیابی تفصیلی ماژول مدیریت کنترل‌ها

- [GRC-CONTROL-201](modules/GRC-CONTROL-201_FA.md): ۱۶ معیار پذیرش، مشخصات Control/Mapping/Implementation/Test/Run/Evidence، API و گزارش‌ها؛ وضعیت AS-IS و هدف جداست.
- [GRC-CONTROL-UAT-202](modules/GRC-CONTROL-UAT-202_FA.md): ۱۳ Test مثبت و ۲۰ Test منفی؛ **تست‌های جدید اجرا نشده‌اند**.

| نیازمندی | Test IDهای مرتبط | وضعیت فعلی شواهد |
|---|---|---|
| FR-CTL-001 | CTL-TC-001..004؛ CTL-NEG-01..09 | کد و چهار تست repository بررسی شد؛ UAT واقعی NOT-RUN |
| FR-CTL-002 | CTL-TC-005؛ CTL-NEG-10..15 | Interface موجود؛ اثربخشی بدون Review شکاف |
| FR-CTL-003 | CTL-TC-006..007؛ CTL-NEG-16..18 | API موجود؛ UI ایجاد/اجرا/تاریخچه ناقص؛ UAT NOT-RUN |
| FR-EVD-001/002 | CTL-TC-008؛ CTL-NEG-19..20 | File Gate وابسته به Config/Scanner؛ UAT NOT-RUN |
| FR-RSK-004 | CTL-TC-009..010 | RiskControl + Finding/Action؛ UAT NOT-RUN |
| FR-RPT-001 | CTL-TC-011 | گزارش‌های اختصاصی هدف؛ NOT-RUN / بخشی PLANNED |
| FR-LOC-001 | CTL-TC-012 | Gap تاریخ شمسی #182 |
| FR-AI-001/002/003 | CTL-TC-013 | AI runtime محلی غیرفعال؛ NOT-RUN |

**شرط تغییر وضعیت RTM:** SHA و نسخه جدید، نام Test، Actor/زمان، Expectation/Observation، شواهد قابل بررسی و Defect/PR ذکر شود؛ PASS بر اساس وجود فایل مستند صادر نمی‌شود.

## ۹. ردیابی تفصیلی استانداردها و ارزیابی انطباق

- [GRC-COMPLIANCE-301](modules/GRC-COMPLIANCE-301_FA.md): فرهنگ داده و Workflow همه Framework/Requirement/Assessmentهای Legacy و Generic، ۲۴ Validation Rule، ۱۸ Acceptance Criteria و ۱۵ Gap Source/Design.
- [GRC-COMPLIANCE-UAT-302](modules/GRC-COMPLIANCE-UAT-302_FA.md): ۱۸ تست مثبت و ۲۰ منفی **تدوین‌شده اما اجرا‌نشده**.

| Requirement | Test Cases | وضعیت/پیگیری |
|---|---|---|
| FR-FWK-001 | CMP-TC-001/002؛ CMP-NEG-01..05 | AS-IS کد موجود؛ UAT NOT-RUN |
| FR-FWK-002 | CMP-TC-003/014؛ CMP-NEG-06..09 | حقوق محتوا / Import/Export؛ UAT NOT-RUN |
| FR-FWK-003 | CMP-TC-004؛ CMP-NEG-10..12 | Approval invalidation P1 GAP |
| FR-CTL-001 | CMP-TC-005/018؛ CMP-NEG-14 | **P0 SECURITY REVIEW #186** |
| FR-ASM-001 | CMP-TC-006..009/018؛ CMP-NEG-13..16 | Score/Snapshot در کد؛ Review Gate GAP؛ UAT NOT-RUN |
| FR-ASM-002 | CMP-TC-010..012؛ CMP-NEG-17..20 | Generic published template/typed answers؛ UAT NOT-RUN |
| FR-EVD-001 / FR-FND-001 / FR-ACT-001 | CMP-TC-013 | API در کد؛ UI Auto-first GAP |
| FR-RPT-001 | CMP-TC-016 | Gap Report رسمی TO-BE / NOT-RUN |
| FR-AI-001..003 | CMP-TC-017 | AI خاموش / NOT-RUN |
| FR-LOC-001 / FR-UX-001 | CMP-TC-015 | Jalali #182 + UX GAP |
| NFR-SEC-001 / NFR-LEGAL-001 | CMP-TC-014/018 | Tenant leakage #186 + حقوق محتوا نیازمند Test/Approval |

**قانون:** Evidence واقعی و SHA دقیق برای تغییر وضعیت TEST الزامی است؛ متن Source-reviewed Gap به معنای وقوع Incident واقعی نیست.


## ۱۰. ردیابی تفصیلی مدیریت شواهد، ممیزی و CAPA

- [GRC-EVIDENCE-AUDIT-401](modules/GRC-EVIDENCE-AUDIT-401_FA.md): موجودیت‌ها و حق دسترسی، ۲۶ قاعده اعتبارسنجی، ۱۸ معیار پذیرش، ۱۶ شکاف شناسایی‌شده.
- [GRC-EVIDENCE-AUDIT-UAT-402](modules/GRC-EVIDENCE-AUDIT-UAT-402_FA.md): ۱۹ سناریوی مثبت، ۲۴ سناریوی منفی، Fixtures و شواهد/گیت‌های پذیرش. **آزمون تازه اجرا نشده است.**

| Requirement | Test Cases | وضعیت شواهد |
|---|---|---|
| FR-EVD-001 | EAU-TC-001/002/005؛ EAU-NEG-01/02/05/08/09 | Model/API و Unit Tests موجود؛ UAT NOT-RUN |
| FR-EVD-002 | EAU-TC-002..004؛ EAU-NEG-03..07 | Scanner و Production download gate نیازمند آزمون مستقل |
| FR-AUD-001 | EAU-TC-006..009/015؛ EAU-NEG-12..16 | P0 Cross-Tenant #188؛ Review/Plan gap P1 #189 |
| FR-FND-001 | EAU-TC-009/010/013/014؛ EAU-NEG-17..19 | Closing effectiveness gap #189 |
| FR-ACT-001 | EAU-TC-011..014؛ EAU-NEG-20/21 | Action Done≠Verified #189 |
| FR-RPT-001 | EAU-TC-015/016 | DOCX/API Source موجود؛ UAT صادرات رسمی NOT-RUN |
| FR-AI-001/002/003 | EAU-TC-018؛ EAU-NEG-24 | AI نصب‌شده خاموش / NOT-RUN |
| FR-LOC-001 / FR-UX-001 | EAU-TC-017 | شمسی #182 و UX Gap |
| FR-IAM-003 / NFR-SEC-001 | EAU-TC-005/007؛ EAU-NEG-08..13/22 | **P0 Review #188**؛ Issue #186 از Compliance مرتبط |
| NFR-SEC-002 / NFR-OPS-001 | EAU-TC-016؛ EAU-NEG-23 | Audit HMAC/SIEM Source؛ Retest و Key Backup NOT-RUN |

**Gate:** وضعیت PASS فقط همراه SHA/Runtime/Operator/Time/Expected/Observed و Evidence مستقل؛ باز کردن Issue نشان‌دهنده برطرف‌شدن نقص نیست.


## ۱۱. ردیابی تفصیلی اسناد، قالب‌ها، گزارش و SoA

- [GRC-DOCUMENT-SOA-501](modules/GRC-DOCUMENT-SOA-501_FA.md): مدل و قرارداد اسناد/نسخه/تصویب/Template/SoA، ۲۶ Validation Rule، ۱۸ معیار پذیرش، ۱۶ Gap.
- [GRC-DOCUMENT-SOA-UAT-502](modules/GRC-DOCUMENT-SOA-UAT-502_FA.md): ۲۰ سناریوی مثبت و ۲۴ منفی، **تعریف‌شده ولی اجرا‌نشده**.

| Requirement | تست‌های مرتبط | وضعیت/Gap |
|---|---|---|
| FR-DOC-001 | DOC-TC-001..007؛ DOC-NEG-01..13 | Source lifecycle دارد؛ Review Independence و DocumentLink GAP |
| FR-SOA-001 | DOC-TC-012..017؛ DOC-NEG-19..23 | Draft-only واقعی؛ Formal SoA Approval **موجود نیست** |
| FR-WFL-001 | DOC-TC-003..006/016؛ DOC-NEG-06..10/22 | Approval داخلی و Feedback SoA مجزا |
| FR-RPT-001/002 | DOC-TC-008..011/019؛ DOC-NEG-14..18 | **P0 security review #190**؛ Print/RTL UAT NOT-RUN |
| FR-AI-001/002/003 | DOC-TC-018؛ DOC-NEG-24 | AI disabled در نصب فعلی؛ فقط Suggestion |
| FR-EVD-001 | DOC-TC-007/013/014؛ DOC-NEG-13/21 | Evidence/Document scope، Readiness غیراعتباری |
| FR-LOC-001 / FR-UX-001 | DOC-TC-019؛ DOC-NEG-17..18 | Jalali #182، UI و فارسی DOCX |
| NFR-SEC-001 | DOC-TC-008/011/012؛ DOC-NEG-03/14..16/19..22 | Tenant/Scope/Template Write P0 Test |
| NFR-LEGAL-001 | DOC-TC-015/017/018 | حقوق متن استاندارد و SoA Formal Gate |
| NFR-OPS-001 | DOC-TC-020 | Export/Release/Backup/Restore نیازمند UAT مستقل |

**شرط تغییر وضعیت:** Release دقیق + Actor/Time + Expected/Observed + HTTP/DB/Screenshot Sanitized + Audit + فایل/Hash در صورت وجود؛ باز بودن #190 یا این سند به معنی اصلاح کد نیست.


## ۱۲. ردیابی تفصیلی معماری هوش مصنوعی و اتصال‌دهنده‌ها

- [GRC-AI-INTEGRATIONS-601](modules/GRC-AI-INTEGRATIONS-601_FA.md): فرهنگ داده و API/Scope، AI Provider/RAG/Suggestion، ۴ اتصال‌دهنده read-only، ۳۰ قاعده، ۲۲ معیار پذیرش و ۱۸ شکاف شناسایی‌شده.
- [GRC-AI-INTEGRATIONS-UAT-602](modules/GRC-AI-INTEGRATIONS-UAT-602_FA.md): ۲۲ سناریوی مثبت و ۲۸ منفی با Fixture مصنوعی؛ `NOT-RUN`.
- [GRC-DELIVERY-GATES-603](GRC-DELIVERY-GATES-603_FA.md): گیت امنیتی/آزمون/نصب/رندر/Backup، تفکیک R1 core با AI/Connector Optional.

| نیازمندی | سناریوهای UAT | Status / Defect |
|---|---|---|
| FR-AI-001 | AII-TC-001..004/009/011/016؛ AII-NEG-01..05/13/14 | **P0 #192** Provider Egress؛ Local AI Disabled |
| FR-AI-002 | AII-TC-005..009/012؛ AII-NEG-06..11 | **P0 #192** Source Classification / Knowledge Collision، Prompt Injection Human Review |
| FR-AI-003 | AII-TC-003/010/011؛ AII-NEG-12/13 | AISuggestion AS-IS؛ Replay/Independent Apply gap |
| FR-CON-001 | AII-TC-013..021؛ AII-NEG-15..27 | چهار Connector Source موجود؛ **P1 #193**؛ Vendor live NOT-RUN |
| FR-EVD-001/002 | AII-TC-013/019/021؛ AII-NEG-25..27 | Collected Evidence ≠ Verified؛ Scope/Classification |
| FR-CTL-001/003 | AII-TC-004/021/022؛ AII-NEG-26 | No Control Effective from Sync؛ Assurance #185 |
| FR-DOC-001 | AII-TC-011/022؛ AII-NEG-13 | AI Document Draft صرفاً Suggestion |
| FR-RPT-001 | AII-TC-022 | Connector/AI audit/provenance reports TO-BE |
| NFR-AI-001 | AII-TC-005..012/018؛ AII-NEG-04..14 | Adversarial evaluation Source موجود؛ Real Model Human Review NOT-RUN |
| NFR-SEC-001 / NFR-OPS-001 | AII-TC-001/007..009/017..021؛ AII-NEG-01..10/17..25 | Provider Secret/Egress، TLS LDAP، Tenant/Unit |
| NFR-DEP-002 | AII-TC-009/022؛ AII-NEG-04/05/21/22 | Airgap/TLS network capture EXTERNAL-PROOF |

**تغییر وضعیت فقط با Test Runner/Network Evidence واقعی، Build SHA/Digest، Actor/Time، Expected/Observed و Retest مجاز است.** #192/#193 هنوز رفع نشده‌اند و احتمال‌های Source-reviewed را نباید Incident اثبات‌شده تعبیر کرد.
