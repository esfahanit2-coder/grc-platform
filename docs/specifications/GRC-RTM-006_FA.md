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
