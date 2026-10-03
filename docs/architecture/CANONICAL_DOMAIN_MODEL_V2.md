# Canonical Domain Model v2

**Status:** Proposed architecture freeze candidate  
**Baseline:** `main@22ab5675da1d5525aff04ee8986943961648d4ab`  
**Tracking:** #96  
**Scope:** Domain architecture only. No runtime schema/API/deployment changes are authorized by this document.

## 1. Purpose

This document converts the current GRC pilot architecture into an enterprise-product domain model without discarding sound existing work.

The governing approach is:

```text
Preserve sound core
        +
Correct weak abstractions
        +
Add missing enterprise domains
        +
Productize configuration/licensing/extensions
```

A full rewrite is explicitly rejected.

The existing modular monolith, Django/PostgreSQL stack, tenant model, scoped RBAC, framework/version/requirement model, control-definition versus control-implementation separation, immutable-ish risk evaluation history, evidence core, control testing, shared findings/actions, audit/document core, workflow engine, audit integrity chain, AI provider abstraction and on-prem/offline architecture remain strategic assets.

---

## 2. Canonical invariants

These rules are architectural invariants:

1. `Requirement != Control`.
2. `Control != ControlImplementation`.
3. `Risk != RiskEvaluation`.
4. `RiskTreatment != RiskAcceptance`.
5. `Evidence != EvidenceArtifact`.
6. `Evidence != ControlTest`.
7. `Evidence != ComplianceDecision`.
8. `Finding != Action`.
9. `Framework != FrameworkVersion`.
10. `Document != DocumentVersion`.
11. `ConnectorFact != authoritative GRC decision`.
12. `AISuggestion != human approval`.
13. Historical completed assessments/tests/decisions must not be silently rewritten.
14. Tenant isolation and authorization scope are backend responsibilities, not UI conventions.
15. Framework and regulatory content is data, not framework-specific application code.
16. Product licensing and content licensing are separate concerns.
17. Semantic business relationships prefer explicit database relations.
18. Generic typed references are permitted only for bounded cross-cutting infrastructure use cases.

---

# Part A — Context Model

## 3. Problem

The current product has strong `Tenant`, `OrganizationUnit` and `Asset` concepts, but business context is still too narrow for enterprise GRC.

A mature GRC object may need to be understood in relation to:

- legal entity;
- organization unit;
- objective;
- business process;
- business service;
- asset;
- project;
- location;
- third-party engagement.

The wrong solution would be one universal `ContextObject(type,id,json)` table. That would weaken database integrity, make reporting obscure, complicate authorization, and allow unrelated concepts to become interchangeable.

## 4. Decision: explicit domain context, unified resolution contract

We will use **explicit domain entities** for important business concepts and a **context resolution contract** for cross-cutting services.

### 4.1 Existing entities retained

- `Tenant`
- `OrganizationUnit`
- `Asset`
- `AssetDependency`

### 4.2 New canonical entities

#### Objective

Represents something the organization is trying to achieve.

Suggested kinds:

- strategic;
- operational;
- financial;
- compliance;
- security;
- resilience.

Core relationships:

```text
Objective <-> Risk
Objective <-> Metric
Objective <-> BusinessProcess
```

#### BusinessProcess

Represents an operational/business process, not merely an org chart node.

Properties should include:

- tenant;
- code;
- name;
- parent;
- owner;
- criticality;
- organization owner/scope;
- status.

Core relationships:

```text
BusinessProcess <-> Risk
BusinessProcess <-> ControlImplementation
BusinessProcess <-> AuditEngagement
BusinessProcess <-> Objective
```

#### BusinessService

Represents a service/capability whose continuity matters.

It is especially important for BCM and operational resilience, but it belongs in the canonical model before those modules are implemented.

Core relationships:

```text
BusinessService <-> BusinessProcess
BusinessService <-> Asset
BusinessService <-> Risk
BusinessService <-> Objective
```

#### LegalEntity

The current `OrganizationUnit(unit_type=company)` can represent company hierarchy, but a registered legal entity has additional semantics such as jurisdiction, registration identity, regulatory applicability and contract ownership.

**Decision for v2:** do not replace `OrganizationUnit`. Introduce `LegalEntity` only when the ERD confirms a real need for legal/regulatory attributes. If introduced, it should link to the corresponding organizational node rather than creating a second unrelated hierarchy.

## 5. Authorization scope is not equal to business context

A critical distinction:

```text
Business context answers: "what is this GRC record about?"
Authorization scope answers: "who is allowed to see/manage it?"
```

For v2, `OrganizationUnit` remains the primary authorization scope.

BusinessProcess, BusinessService, Asset and Objective should normally resolve to an owning/primary OrganizationUnit for authorization. This prevents an explosion of incompatible RBAC scope types.

Future scope types may be added deliberately, but not by making every context entity an authorization boundary.

## 6. Relationship rule

Important business links use explicit relations.

Examples:

- Risk-to-Objective: explicit link/FK table.
- Risk-to-BusinessProcess: explicit link.
- Risk-to-Asset: explicit link.
- ControlImplementation-to-BusinessProcess: explicit link.
- BusinessService-to-Asset: explicit link.

We do **not** use a generic `context_type/context_id` relation for all business semantics.

## 7. Current-model migration

Current:

```text
Risk -> OrganizationUnit
Risk -> Asset
ControlImplementation -> OrganizationUnit
AuditEngagement -> OrganizationUnit
```

Target evolution:

```text
Risk
  -> primary authorization OrganizationUnit
  <-> Objective
  <-> BusinessProcess
  <-> BusinessService
  <-> Asset

ControlImplementation
  -> authorization OrganizationUnit
  <-> BusinessProcess
  <-> BusinessService
  <-> Asset
```

Existing fields remain valid during additive migration.

---

# Part B — Generic Assessment Engine

## 8. Problem

The current Assessment model looks generic by name, but structurally every Assessment requires a `FrameworkVersion` and every AssessmentItem requires a `Requirement`.

Therefore the actual current abstraction is:

```text
Framework Requirement Assessment Engine
```

This is suitable for compliance/maturity assessments, but not for:

- control self-assessment;
- risk questionnaires;
- vendor assessments;
- maturity questionnaires not backed by Framework Requirement records;
- audit questionnaires;
- custom organizational assessments.

## 9. Decision: template/criterion/runtime architecture

The new engine separates **definition**, **runtime execution**, and **domain-specific profile**.

### 9.1 AssessmentTemplate

A reusable/versioned definition of an assessment.

Suggested attributes:

- tenant/global ownership;
- code;
- name;
- assessment family;
- version;
- status;
- scoring model;
- workflow/configuration;
- language;
- metadata.

Templates become immutable/versioned after publication.

### 9.2 AssessmentCriterion

A criterion/question/check within a template.

Suggested attributes:

- template;
- code;
- parent;
- title;
- description/guidance;
- response type;
- allowed options;
- weight;
- mandatory;
- sort order;
- scoring rule;
- snapshot payload.

A criterion may be generated from a Requirement, Control or another module-specific source, but the generic assessment engine must not require one particular source type.

### 9.3 Assessment

Runtime instance.

Core fields:

- tenant;
- template/version;
- authorization organization scope;
- title;
- owner;
- start/due/completed dates;
- workflow/status;
- overall score;
- progress;
- metadata.

**FrameworkVersion is no longer mandatory in generic core.**

### 9.4 AssessmentItem

Runtime criterion result.

Core fields:

- assessment;
- criterion;
- criterion snapshot;
- response/result;
- score;
- applicability;
- assignee;
- reviewer;
- comments;
- decision metadata.

Completed items preserve the exact criterion snapshot used at that point in time.

## 10. Domain adapters/profiles

Business modules extend the engine rather than duplicating it.

### Compliance profile

```text
ComplianceAssessmentProfile
  -> Assessment
  -> FrameworkVersion
```

A FrameworkVersion can generate/publish an AssessmentTemplate whose Criteria correspond to Requirements.

Explicit mappings preserve:

```text
AssessmentCriterion <-> Requirement
```

### Control assessment profile

Criteria can map to Control/ControlImplementation.

### Third-party profile

Criteria can be questionnaire questions with an Engagement/Vendor context.

### Risk assessment profile

Risk evaluation methodology remains a separate risk-domain concept. The generic assessment engine may orchestrate questionnaires/evidence around risk, but it must not replace `RiskEvaluation`.

## 11. Scoring

Scoring becomes a strategy/configuration, not hard-coded compliance status arithmetic.

A safe design supports named strategies such as:

- weighted status;
- weighted numeric;
- maturity scale;
- pass/fail;
- custom declarative formula from an approved safe DSL.

No arbitrary Python/eval execution is allowed.

## 12. Applicability

`Not Applicable` is a governance decision, not merely a result value.

A future applicability decision should preserve:

- criterion/item;
- justification;
- actor;
- approval;
- timestamp;
- validity/review if applicable.

## 13. Migration from current Assessment

No destructive rewrite.

Phase migration:

1. create generic template/criterion models;
2. generate a template per currently used locked FrameworkVersion;
3. create criteria corresponding to Requirements;
4. link existing Assessments to generated templates;
5. preserve current AssessmentItem requirement snapshots;
6. add ComplianceAssessmentProfile rows referencing current FrameworkVersion;
7. move new creation paths to the generic engine;
8. retain compatibility readers until all API/frontend/reporting paths are migrated;
9. only then consider removing mandatory legacy FKs.

Historical results must remain byte-for-byte semantically equivalent.

---

# Part C — Cross-Domain Reference Contract

## 14. Problem

The same typed-reference pattern currently exists independently in multiple places:

- `EvidenceLink(object_type, object_id)`
- `DocumentLink(object_type, object_id)`
- `Action(source_type, source_id)`
- `WorkflowInstance(object_type, object_id)`
- `AISuggestion(object_type, object_id)`

Workflow also contains a hard-coded `OBJECT_MODEL_MAP`.

This pattern is useful, but scattered resolution rules create duplication and future module coupling.

## 15. Decision: central Domain Object Registry, not universal business FK replacement

Create a platform-level **Domain Object Registry contract**.

A registered object type supplies at least:

- stable type code;
- model/service resolver;
- tenant resolver;
- authorization scope resolver;
- human display label;
- existence/deleted-state validation;
- permission capability mapping;
- optional URL/API identity metadata.

Conceptual interface:

```text
resolve(type, id, tenant) -> object
tenant_of(object)
scope_of(object)
display_of(object)
can_reference(capability, object)
```

Each module registers public object types through a controlled module interface.

## 16. Where typed generic references are allowed

Allowed for cross-cutting infrastructure:

- Evidence attachments/links;
- Document links;
- Workflow targets;
- AI suggestion targets;
- Notifications;
- comments/mentions if added;
- generic activity feeds;
- non-authoritative source references.

## 17. Where typed generic references are not allowed

Do not replace semantically important relationships such as:

- Risk -> Objective;
- Risk -> ControlImplementation;
- Control -> Requirement;
- Finding -> ControlImplementation;
- Assessment compliance profile -> FrameworkVersion;
- Audit Workpaper -> ControlImplementation;
- RiskAcceptance -> RiskEvaluation.

These need explicit relational integrity.

## 18. Persistence design

A single universal `ObjectReference` table is **not required**.

Dedicated tables may remain:

- EvidenceLink;
- DocumentLink;
- etc.

They should use the same type codes and the same resolver/validation contract.

This limits migration risk while eliminating scattered hard-coded object resolution.

## 19. Integrity controls

Because a typed UUID reference cannot use a normal FK to many target tables, cross-cutting generic references require:

- validation on create/update;
- tenant/scope validation;
- soft-delete awareness;
- periodic orphan integrity checks;
- deletion policies from registered target types;
- audit logging;
- tests ensuring foreign-tenant UUIDs remain cloaked.

---

# Part D — Core vs Module Boundary

## 20. Three architectural layers

Technical architecture and commercial packaging must not be confused.

### 20.1 Platform Core

Cross-domain infrastructure required by the product:

- tenancy;
- organization structure;
- identity;
- scoped RBAC;
- MFA/SSO;
- configuration;
- workflow;
- audit trail/integrity;
- files/object storage;
- notifications;
- domain object registry;
- import/export foundation;
- localization;
- background jobs;
- observability hooks;
- product license/entitlement enforcement infrastructure;
- API foundation.

### 20.2 Shared GRC Core

Canonical objects reused by multiple GRC business domains:

- Objective;
- shared Context foundations;
- Control definition;
- ControlImplementation;
- Evidence;
- Evidence Review;
- Finding;
- Action;
- Metric foundation;
- generic Assessment engine.

These are not owned by Risk, Compliance or Audit individually.

### 20.3 Business Modules

Domain-specific capabilities:

#### Enterprise Risk
- Risk;
- RiskCategory;
- RiskMethodology;
- RiskEvaluation;
- RiskTreatment;
- RiskAppetite;
- RiskTolerance;
- RiskAcceptance;
- KRI behavior.

#### Compliance / Obligations
- Framework;
- FrameworkVersion;
- Requirement;
- mappings;
- obligation sources;
- compliance assessment profile;
- regulatory applicability/change.

#### Assurance / Controls
- ControlTest;
- ControlTestRun;
- design effectiveness;
- operating effectiveness;
- effectiveness conclusion.

#### Internal Audit
- AuditUniverse;
- AuditPlan;
- AuditEngagement;
- AuditTeam;
- Workpaper;
- audit reports.

#### Policy / Controlled Documents
- Document;
- DocumentVersion;
- approvals;
- policy relationships;
- attestation if added.

#### Future optional modules
- Third-Party Risk;
- Contracts;
- BCM;
- Operational Resilience;
- Privacy;
- AI Governance;
- ESG;
- Model Risk.

## 21. Technical module presence vs commercial entitlement

The v1 product remains **one modular-monolith codebase**.

We do not create per-customer branches or dynamically install arbitrary Python packages into customer deployments.

A build may contain multiple business modules while the customer's license determines which features are entitled.

Therefore:

```text
Code/module availability != commercial entitlement
```

Commercial checks must be centralized through entitlement services, not scattered:

```text
if edition == "enterprise"
```

throughout business code.

## 22. Product licensing vs content licensing

Separate models and policies:

### Product licensing

Controls:

- edition;
- enabled modules;
- active-user limits if used;
- legal entities if used;
- connector entitlements;
- support/maintenance validity.

### Content licensing

Controls:

- whether a framework/content pack can be distributed;
- tenant-only customer-provided content;
- publisher/right-to-use metadata;
- pack version/provenance.

A valid product license never grants copyright rights to content.

---

# Part E — Control Effectiveness Authority

## 23. Problem

Current `ControlImplementation.effectiveness` can diverge from `ControlTestRun` results.

This creates two potential sources of truth.

## 24. Decision

`ControlTestRun.result` is test evidence/result.

A separate governed **EffectivenessConclusion** should become the authoritative conclusion where needed.

Conceptually:

```text
ControlImplementation
      -> ControlTest
      -> ControlTestRun(s)
      -> Evidence
      -> EffectivenessConclusion
```

Conclusion should capture:

- design effectiveness;
- operating effectiveness;
- overall conclusion;
- reviewer/approver;
- effective period;
- source runs/evidence;
- rationale.

`ControlImplementation.effectiveness` should become either:

1. a derived/cache summary of the current approved conclusion; or
2. deprecated after compatibility migration.

It should not remain an independently editable authoritative field.

---

# Part F — Risk Governance

## 25. Risk appetite/tolerance

Add explicit entities/value models so thresholds are not conflated with methodology scoring bands.

Conceptual scope:

```text
RiskAppetiteStatement
  -> tenant
  -> optional category
  -> optional objective
  -> optional org scope
  -> metric/threshold expression
  -> effective period
  -> approval
```

Tolerance may be represented as measurable boundaries associated with appetite.

## 26. Risk acceptance

Create independent `RiskAcceptance`.

Required relationships:

- tenant;
- Risk;
- accepted RiskEvaluation (normally current/residual);
- decision maker;
- decision/approval record;
- rationale;
- conditions;
- valid_from;
- valid_until;
- review date;
- status/supersession.

An acceptance must not erase or mutate the underlying RiskEvaluation.

---

# Part G — Metrics Foundation

## 27. Canonical metric model

Create a shared foundation:

```text
MetricDefinition
   -> type: KPI/KRI/KCI
   -> unit
   -> owner
   -> frequency
   -> source
   -> thresholds

MetricObservation
   -> observed_at
   -> value
   -> source/provenance

MetricBreach
   -> threshold
   -> detected_at
   -> acknowledged/resolved state
```

Module-specific use:

- Risk uses KRI;
- Controls use KCI;
- Objectives use KPI;
- dashboards use all three;
- connectors may produce observations without directly making compliance decisions.

This foundation also provides the correct future home for normalized connector facts/time series.

---

# Part H — Content Pack v2

## 28. Direction

Content Pack v1 remains valid for Framework/Version/Requirement imports.

Content Pack v2 may optionally include:

- control library entries;
- requirement-control mappings;
- translations;
- assessment templates/criteria;
- scoring models;
- risk methodology templates;
- taxonomies;
- report templates;
- workflow templates;
- licensing/provenance metadata.

All sections must be optional and versioned.

Pack data must never execute arbitrary code.

Customer-provided restricted content must remain tenant-scoped.

---

# Part I — Migration Map

## 29. Preserve

Preserve with no conceptual rewrite:

- Tenant;
- TenantMembership;
- OrganizationUnit;
- Asset;
- AssetDependency;
- Framework;
- FrameworkVersion;
- Requirement;
- RequirementTranslation;
- RequirementMapping;
- Control;
- ControlRequirement;
- RiskCategory;
- Risk;
- RiskEvaluation;
- RiskControl;
- Evidence;
- Finding;
- Action;
- AuditPlan;
- AuditEngagement;
- AuditTeamMember;
- Workpaper;
- Document;
- DocumentVersion;
- DocumentApproval;
- WorkflowDefinition/State/Transition/Instance/Event;
- Permission/Role/UserRoleScope;
- AuditEvent integrity chain;
- AIProviderConfig/AIInteraction/AISuggestion/KnowledgeChunk;
- ConnectorRun fundamentals.

## 30. Refactor additively

- RiskMethodology execution engine;
- RiskTreatment acceptance fields -> independent RiskAcceptance;
- ControlImplementation effectiveness -> governed EffectivenessConclusion;
- Assessment/AssessmentItem -> generic template/criterion engine;
- generic links -> central Domain Object Registry contract;
- Workflow hard-coded target map -> registry;
- ConnectorConfig type model -> future registered ConnectorDefinition;
- Content Pack importer -> v2 optional sections.

## 31. Add

Priority enterprise foundations:

- Objective;
- BusinessProcess;
- BusinessService (canonical now; implementation may follow later);
- RiskAppetite/RiskTolerance;
- RiskAcceptance;
- AssessmentTemplate;
- AssessmentCriterion;
- ComplianceAssessmentProfile;
- ApplicabilityDecision;
- EffectivenessConclusion;
- MetricDefinition/Observation/Breach;
- product License/Edition/Entitlement infrastructure;
- Exception/Waiver;
- optional LegalEntity after ERD validation.

Expansion modules later:

- ThirdParty;
- ThirdPartyEngagement;
- Contract;
- AuditUniverse;
- RegulatoryChange;
- BCM;
- OperationalResilience;
- Privacy;
- AI Governance domain;
- ESG;
- Model Risk.

---

# Part J — Migration Principles

## 32. Additive-first

All domain modernization follows:

```text
Add new model
-> dual-read/adapter
-> migrate/backfill
-> switch writes
-> verify
-> remove legacy dependency only after proven compatibility
```

No destructive migration merely to achieve naming purity.

## 33. Historical integrity

Do not recalculate historical:

- RiskEvaluations;
- completed Assessments;
- completed AssessmentItems;
- ControlTestRuns;
- Finding closures;
- document approvals;
- audit conclusions.

Migration may attach new metadata/profile records around them but must not change historical meaning.

## 34. API compatibility

Where current Pilot APIs are externally consumed, introduce versioned/deprecation-compatible changes rather than abrupt schema replacement.

## 35. Tenant safety

Every migration/backfill must prove:

- tenant consistency;
- org-scope consistency;
- no cross-tenant reference;
- no orphan references;
- deterministic repeatability.

---

# Part K — Non-goals

This architecture freeze does **not** authorize:

- a full rewrite;
- microservice decomposition;
- framework-specific code branches;
- a graph database migration;
- arbitrary user-defined executable formulas;
- dynamic customer forks;
- SaaS-only assumptions;
- replacing OrganizationUnit as the current authorization scope;
- enabling external acceptance blockers #5/#6/#7/#8/#40/#42/#74;
- declaring RC/production readiness.

---

# Part L — Sequence after freeze

## 36. Step 1 — ERD v2

Produce an implementation-level ERD for the P0/P1 entities only.

Focus first on:

1. Objective;
2. BusinessProcess;
3. RiskAppetite/Tolerance;
4. RiskAcceptance;
5. AssessmentTemplate/Criterion/Profile;
6. EffectivenessConclusion;
7. Metric foundation;
8. Product licensing/entitlements;
9. Domain Object Registry contract interfaces.

## 37. Step 2 — Migration plan

For each affected current model identify:

- new fields/tables;
- backfill;
- compatibility API;
- data invariant;
- rollback strategy;
- tests;
- removal criteria.

## 38. Step 3 — scoped implementation waves

Separate issues/PRs:

1. domain registry and context foundations;
2. objective/process;
3. risk governance;
4. assessment engine;
5. assurance/effectiveness;
6. metrics;
7. commercial licensing foundation;
8. content pack v2.

Each implementation PR follows exact-head CI, branch synchronization, review, merge, and post-merge CI discipline.

---

# 39. Architecture freeze recommendation

The following four decisions are recommended for acceptance:

1. **Context:** explicit business entities + OrganizationUnit authorization scope; no universal context table.
2. **Assessment:** generic template/criterion runtime engine; compliance becomes a profile/adapter rather than the core abstraction.
3. **Cross-domain references:** central resolver/registry for bounded cross-cutting references; semantic relations retain explicit FKs.
4. **Core/modules:** one modular-monolith codebase with Platform Core + Shared GRC Core + Business Modules; commercial entitlements remain separate from technical code packaging.

Once these decisions are accepted, the next artifact is **ERD v2 + migration matrix**, not runtime implementation.
