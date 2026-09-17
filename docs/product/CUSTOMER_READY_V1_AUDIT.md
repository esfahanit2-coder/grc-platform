# Customer-Ready v1 Product Audit

Status baseline: `main@48a5c0e284267eebbce7f4fb245ae227570de9f5`

Related umbrella: #44

## Purpose

This audit answers a narrower question than the architecture roadmap: **what remains before a real customer can install the platform, onboard independently, use it every day, and receive production support?**

Customer readiness is intentionally stricter than “feature exists in the backend” or “CI is green.” It requires usable product flows, operational evidence, authorized content, supportability and a defensible product identity.

## Executive assessment

The platform is substantially beyond a toy MVP. Its domain model, backend modules, security boundaries, deployment tooling and release discipline are already strong for a pre-RC product. The principal mismatch is that the **backend/domain engine is materially more mature than the customer-facing experience**.

Engineering judgment at this baseline:

| Area | Readiness | Interpretation |
|---|---:|---|
| Domain model / GRC core | 85–90% | Major entities and traceability primitives exist. |
| Backend APIs / security / workflow primitives | 80–85% | Strong tenant/RBAC/audit/security foundation; external validation remains. |
| On-prem / offline / release engineering | 80–90% software-side | Strong tooling; real clean-host evidence remains under #7. |
| Core customer functionality | 65–70% | Most business capabilities exist, but several customer flows are incomplete in UI. |
| Daily usability / UX productization | 45–55% | Dashboard is now strong; many module pages remain prototype-like/read-only. |
| Customer onboarding / administration | 40–50% | RBAC exists, but onboarding and user/role administration are not productized end-to-end. |
| Reporting / executive deliverables | 50–60% | Secure rendering foundation exists; customer-facing reporting center is thin. |
| Live production validation | 30–40% | Automated evidence is strong, but #5–#8 require real external/environment evidence. |

Overall engineering judgment:

- **Controlled Pilot readiness:** approximately 75–80%.
- **Independent customer production readiness:** approximately 55–65%.

These are deliberately approximate weighted judgments, not mathematical completion percentages.

## What is already strong

### GRC domain and traceability

The core architecture is sound and extensible:

`Framework -> Version -> Requirement <-> Common Control -> Control Implementation -> Evidence -> Test`

`Asset/Process -> Risk -> Evaluation -> Treatment -> Action -> RTP`

Assessment, finding/CAPA, internal audit, document, workflow and AI/RAG primitives are present around that core. This supports the core principle that frameworks are content rather than hard-coded application logic.

### Security and auditability

The platform already has meaningful security engineering:

- tenant-scoped RBAC and organization scopes;
- TOTP MFA and hardened authentication flows;
- tamper-evident audit chain with verifier/sealing;
- fail-closed Evidence malware quarantine path;
- permission-safe RAG / AI boundaries;
- explicit human-review authority boundary for AI;
- migration/release/security gates;
- dependency/SAST/secret/container checks;
- signed offline-release path and support evidence tooling.

At this audit baseline the latest `main` CI passes 132 backend tests, the Golden Pilot / connector subset, frontend typecheck/lint/build, migration checks and pilot compose/TLS/ops validation. This is strong repository evidence, but it does not substitute for #7/#8 real deployment evidence.

### Deployment model

The Pilot stack already supports PostgreSQL + pgvector, Redis, S3-compatible object storage, Django, Celery, Next.js, Nginx TLS and optional local Ollama. Backup, restore, upgrade, rollback and acceptance-evidence tooling exist.

### Dashboard

The management dashboard now uses real tenant/scoped application data for executive KPIs, framework summaries, assessment progress, residual-risk heatmap, top risks, attention actions and upcoming deadlines. It is no longer the main UI maturity problem.

## The real customer-readiness gap

The central issue is not missing database tables. It is **productization of the last mile**.

### 1. Prototype interaction patterns remain in core workflows

Several high-value screens call real APIs but still use browser `prompt()` dialogs or silently choose the first available object from a list.

Observed examples include:

- Assessment creation choosing the first framework version/user/org unit;
- Risk creation choosing the first org unit/owner/asset;
- Risk evaluation/treatment/action flows driven by prompts and first-record defaults;
- Assessment Evidence linking selecting the first Evidence record;
- Finding creation selecting the first user;
- Evidence creation with first user/unit shortcuts and sample-like text.

These are development shortcuts, not customer-ready interactions.

### 2. Evidence is not yet a full customer workspace

Customer-ready Evidence needs:

- real file upload plus text/link Evidence;
- upload/quarantine/scan progress;
- provenance and connector/run references;
- SHA-256/integrity metadata where appropriate;
- owner/classification/validity/expiry/review;
- links to requirements, implementations, tests, assessments and audits;
- visible reuse/freshness;
- controlled download states and actionable scanner errors.

### 3. No unified Work Center / My Tasks

The UX specification already defines Work Center as a primary concept, but it is not implemented. Daily users should see one authoritative operational inbox for:

- assigned assessment items;
- pending reviews/approvals;
- risk-treatment actions;
- findings/CAPA actions;
- document reviews/approvals;
- audit/workpaper work;
- workflow transitions;
- overdue and due-soon items.

The Work Center must aggregate source records, not invent a second business-state model.

### 4. Customer administration is backend-capable but UI-thin

A customer administrator needs product UI for:

- create/invite/deactivate user;
- tenant membership management;
- role and organization-scope assignment;
- effective-permission visibility;
- MFA administration/recovery consistent with policy;
- auditable security-sensitive changes.

Normal customer setup must not require Django shell/admin shortcuts.

### 5. Document lifecycle UX is incomplete

Controlled document/version/approval primitives exist, but customer-ready v1 needs create/edit/version/submit/review/approve UI and visible history.

### 6. Workflow engine needs an operational UI

Definitions and instances exist, but users need practical transition actions, assignee/status visibility and history. A full no-code visual builder is **not required** before the first customer.

### 7. Reporting foundation exceeds reporting product

The backend has a hardened rendering foundation, but the customer-facing Reports area is minimal. A v1 Reporting Center should expose at least:

- SoA;
- RTP;
- Audit Report;
- executive risk/compliance report;
- findings/actions/CAPA report;
- scope/date filters;
- PDF/DOCX/XLSX/CSV/JSON where appropriate;
- source/scope and generated-output audit events.

### 8. Customer onboarding is not productized

A fresh installation needs a first-run/setup experience or equivalent product UI covering first admin, tenant, organization structure, security/MFA, users/scopes, framework initialization, connector readiness, storage/scanner readiness, optional AI provider and environment readiness.

### 9. Enterprise authentication is incomplete

MFA/JWT/cookie authentication exists. No SAML/OIDC enterprise SSO implementation was found at this baseline. The AD/LDAP connector is read-only evidence collection and must not be presented as login SSO.

SSO becomes P0 if the first customer requires it.

### 10. Notifications are narrow

In-app notifications exist, but enterprise operation will normally require SMTP/email reminders/escalations. Teams/webhook adapters can follow.

### 11. Observability needs a production operator surface

Health/readiness exists, but no first-class Prometheus/OpenTelemetry-style integration was found. At minimum the first customer needs alertable visibility for API/worker/beat/queue/database/cache/object-store/backup/storage/scanner/connectors/audit-integrity conditions.

This can integrate with the customer's existing monitoring stack rather than becoming a separate monitoring product.

### 12. Initial customer data migration needs product treatment

Framework import is mature, but onboarding also needs safe CSV/XLSX import/export for organization, users, assets, risks and controls where appropriate, with validation and error reports.

## External acceptance blockers remain real

A VPS can materially advance #7 and #42, and expose real UX/operations defects. It cannot satisfy every blocker by itself:

- **#5:** authorized/licensed framework content and approved mappings.
- **#6:** actual authorized AD/FortiGate/Veeam/Tenable targets.
- **#7:** VPS can close most clean-host/TLS/backup/restore/RPO/RTO/local-AI evidence.
- **#8:** independent pentest/final security acceptance and deployment controls remain external evidence.
- **#40:** server-enforced GitHub protection remains plan-blocked on the current private Free repository; process controls remain compensating controls.
- **#42:** genuine running-Pilot screenshot/visual comparison remains required.

## Customer-Ready v1 P0 sequence

### P0-A — deploy the real product and observe it

Use the provided VPS first:

1. deploy exact `main` release candidate;
2. configure TLS and production environment;
3. create a real tenant/admin without unsafe defaults;
4. populate controlled representative data;
5. run main user journeys in the browser;
6. capture screenshots and UX defects;
7. execute backup/restore/RPO/RTO/readiness evidence;
8. exercise local-AI/no-AI modes where infrastructure permits.

### P0-B — productize primary daily workflows

Replace every prompt/first-record shortcut with real forms/selectors and finish Assessment, Risk/RTP, Evidence, Finding/CAPA/Actions, Documents and workflow-transition experiences.

### P0-C — build Work Center

Create the unified task/approval/due-soon inbox from existing authoritative records.

### P0-D — customer administration and onboarding

Deliver tenant/org/users/scopes/MFA/security/framework setup plus CSV/XLSX onboarding imports.

### P0-E — reporting and customer outputs

Turn existing generation capabilities into an auditable Reporting Center.

### P0-F — operational production baseline

Add/validate monitoring integration, SMTP/reminders, support diagnostics, backup alerting and whichever enterprise SSO mechanism is required by the target customer.

### P0-G — real acceptance

Close applicable #5/#6/#7/#8/#42 evidence and run final customer UAT.

## Product identity: where differentiation should come from

Do not compete by merely having more forms or more standards. The defensible direction is a combination of sovereignty, traceability and intelligent continuous assurance.

### 1. Sovereign Persian-first GRC

- first-class Persian/RTL rather than translated English UI;
- on-prem and air-gapped operation;
- local AI providers;
- signed offline releases;
- controlled licensed/customer-provided framework imports;
- fit for regulated/restricted networks.

### 2. Control & Evidence Graph

Expose the architecture visually and operationally:

`Framework -> Requirement -> Common Control -> Implementation -> Evidence -> Test -> Assessment -> Finding -> Action`

Use it to answer:

- Which Evidence proves this Requirement?
- Which Controls are reused by multiple Frameworks?
- What changes if a Framework version changes?
- Which Assessments/Controls are affected if Evidence expires?
- How much of a newly added Framework is already covered?

### 3. Human-governed Sovereign GRC Copilot

Embed AI inside Risk/Assessment/Control/Evidence/Audit context rather than only a generic chat page. AI may draft/summarize/suggest mappings or remediation, but outputs remain cited suggestions subject to tenant/RBAC scope and human approval.

### 4. Continuous Assurance rather than automatic compliance

Connector facts + Evidence freshness + control tests + expiry/change signals should create human-review tasks, exceptions and remediation. A successful Connector run must never silently mean “compliant.”

### 5. Framework change impact engine

When a Framework/version/content pack changes, compute impact through Common Controls and Evidence relationships. AI may propose crosswalk candidates; authorized users approve them.

### 6. AI Governance as a later adjacent module

The same core can later govern AI assets/models/agents and authorized ISO/IEC 42001, NIST AI RMF or equivalent content packs. This should not block first-customer readiness.

## Market direction checked in September 2026

Current GRC/compliance leaders are converging on:

1. continuous Evidence and Control monitoring;
2. common-control reuse across multiple frameworks;
3. AI embedded into operational workflows;
4. AI governance as a new enterprise GRC domain.

The product should meet the first three selectively before/around first-customer readiness and preserve AI governance as a high-value adjacent expansion.

## Explicit scope control

The following are valuable but should not delay the first production customer unless contractually required:

- full TPRM/vendor portal;
- BCM/BIA;
- incident management;
- FAIR/Monte-Carlo quantitative risk;
- mobile/PWA;
- full visual no-code workflow designer.

After the first customer, Continuous Assurance should generally precede breadth expansion because it reinforces the platform's core differentiation.

## Customer-Ready v1 exit test

A fresh environment must pass this scenario without developer-only shortcuts:

1. install from controlled release artifacts;
2. configure TLS/storage/database/backup/support;
3. create tenant/admin and complete onboarding;
4. import authorized Framework/content;
5. create organization/users/scopes;
6. register assets/processes/risks and evaluate/treat risks;
7. implement controls and attach/reuse Evidence;
8. run Assessment -> Evidence -> Finding -> CAPA/Action -> review/close;
9. run internal audit/control testing/document approval;
10. generate formal reports;
11. use Work Center for assignments/approvals;
12. demonstrate tenant/scope enforcement and audit trail;
13. complete backup/restore/upgrade/support drill;
14. demonstrate required Connectors/local AI/SSO according to customer scope;
15. pass security and customer UAT acceptance.

Until this passes, the product should remain described as **Pilot Candidate / pre-RC**, not a finished production release.
