# Wave 4 — Generic Assessment Engine (Issue #108)

**State:** draft / CI and security gates required. Implementation branch: `feature/108-generic-assessment-foundations`. Do not treat this as a production-ready feature until review and release criteria pass.

## Architecture decision

A new additive Django application, `apps.generic_assessments`, introduces framework-agnostic execution while preserving the existing `apps.assessments` API and database schema. There is **no automatic conversion** or destructive migration of historical compliance assessments or `AssessmentItem` records. `RiskEvaluation` remains independent.

### Domain graph

```text
AssessmentTemplate (tenant, optional org unit)
  └── AssessmentTemplateVersion (draft → published → retired)
        ├── TemplateCriterion (answer type, validation, applicability mode, weight)
        ├── ComplianceAssessmentProfile → FrameworkVersion
        │     └── CriterionRequirementMapping → Requirement
        └── GenericAssessmentRun (tenant, org scope, owner)
              └── GenericAssessmentItem (immutable criterion snapshot)
                    ├── typed answer + deterministic score where meaningful
                    └── ApplicabilityDecision (proposer → independent reviewer)

Legacy AssessmentItem ← separate ApplicabilityDecision FK (NO legacy mutation)
```

## Data guarantees

- **Tenant and org isolation:** all new APIs scope their queries and writes using existing `assessment.view/manage/perform/review` grants. Referenced templates, profiles, requirements and organizational units must belong to the tenant or an explicitly permitted global framework.
- **Publication:** a template version starts as draft; at least one criterion is required; the template owner cannot self-publish. After publication, its criteria and version definition are immutable. A new version is required for revisions.
- **Assessment snapshot:** when a run is created, each criterion’s code, title, answer type, options, weight, required state, and applicability mode is copied to run items. Later framework/template changes cannot retroactively alter those item snapshots.
- **Typed responses:** boolean, numeric 0–100, single-choice enumerated strings, and bounded free text. Only boolean and numeric values produce deterministic percentage scores. Choice and text have no inferred numeric score; summary explicitly identifies partial scoring.
- **Applicability:** either a generic item or legacy item (exclusive-or FK), justification mandatory, independent review required. An applicability record referencing a legacy item is a **separate governance record**, not an edit to legacy `status`, `score`, or `applicability`. A completed generic run cannot be retrospectively changed.
- **Completion:** required applicable items must be answered, manually reviewed applicability decisions must exist and pending applicability proposals must be resolved before final completion. Completion locks answers.
- **Audit:** explicit events on template/version/criterion/profile/mapping/run creation, publication, criterion response, applicability proposal/review, and run completion.
- **Scoring:** weighted mean of explicitly scored items only; never `eval` arbitrary formulas or treat unscored text as zero.

## New API endpoints

All under `/api/v1/`:

- `assessment-templates/` — list, retrieve, create, update
- `assessment-template-versions/` — list, retrieve, create, `{id}/publish/`
- `assessment-criteria/` — list, retrieve, create, update
- `assessment-profiles/` — list, retrieve, create
- `assessment-criterion-mappings/` — list, retrieve, create
- `generic-assessments/` — list, retrieve, create, `{id}/summary/`, `{id}/complete/`
- `generic-assessment-items/` — list, retrieve, `{id}/answer/`
- `assessment-applicability-decisions/` — list, retrieve, create, `{id}/review/`

UI: `/assessments/generic`. Existing `/assessments/` and `/assessment-items/` retain their previous behavior.

## Compatibility acceptance matrix

| Case | Invariant |
|---|---|
| Existing completed Assessment and AssessmentItem | Unchanged status, score, requirements and applicability |
| Published template version | No criterion edits, immutable version metadata |
| Cross-tenant profile/template/requirement | Rejected |
| Unauthorized org unit access | No list/details or cross-unit writes |
| Applicant publishing own template | Rejected |
| Out-of-range, wrong-type or unapproved choice answer | Rejected |
| Completed run | Snapshot and answers locked |
| Manual applicability | Reviewed by a different authorized user |
| Always-applicable criterion | Can complete without redundant decision |
| Framework-specific logic | Data-driven profile; no special standard-specific code |

## Non-goals / follow-up work

- No copying of licensed ISO or Iranian regulatory text into source code.
- No migration of old Assessment/AssessmentItem data without a separate reversible, measured, consented project.
- No untrusted formula/script execution.
- No guarantee of full scoring for narrative criteria until a reviewed rubric is modeled and versioned.
- Broader human usability/UAT, reporting, policy mapping reviews, and air-gapped customer-DC deployment remain independent release gates tracked by #68.
