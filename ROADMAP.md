# Roadmap

## Current state: Pilot Candidate

Implemented foundations include multi-tenancy, scoped RBAC, MFA, framework engine, common controls, asset/risk management, assessments, evidence, findings/CAPA, audit/workpapers, control testing, documents/report factory, workflows, notifications, AI gateway, permission-safe RAG and pilot connectors.

## Gate 0 — Repository and CI normalization

- Create private canonical GitHub repository.
- Commit a real `frontend/package-lock.json` using a connected Node environment.
- Require backend and frontend CI checks on `main`.
- Confirm PostgreSQL 18 migrations from empty database.
- Run the complete Django test suite and Next.js production build.
- Establish tagged release process and SBOM/security gates.

## Gate 1 — Internal pilot

- Deploy `docker-compose.pilot.yml` on a clean pilot host.
- Create first tenant and organization hierarchy.
- Run Golden E2E scenario end-to-end.
- Validate backup/restore.
- Validate browser cookie/CSRF mode under real TLS.
- Validate local Ollama/vLLM path without internet.

## Gate 2 — Content pilot

- Build legally clean AFTA/internal-security content pack from authorized source material.
- Build customer-provided ISO 27001 pack import workflow without redistributing ISO text.
- Define common-control mappings between AFTA, ISMS and internal controls.
- Produce SoA, RTP, assessment report and audit report from real pilot data.

## Gate 3 — Connector pilot

- AD/LDAP inventory and evidence collection.
- FortiGate evidence collection.
- Veeam backup evidence collection.
- Tenable/Nessus vulnerability evidence collection.
- Confirm credentials are stored only in approved secrets infrastructure.
- Add connector health dashboard and sync history.

## Gate 4 — v1.0 Release Candidate

- Final design system and critical UI polish.
- Performance/load testing.
- Penetration testing and dependency/SBOM review.
- HA/DR deployment guide.
- Upgrade/rollback tests.
- Signed offline update bundle.
- Operational runbooks and support handbook.

## Post-v1 priorities

- TPRM/vendor portal.
- BCM/BIA.
- Incident management.
- Continuous control monitoring.
- More connector packs.
- Quantitative risk/FAIR/Monte Carlo.
- Advanced document generation and regulated templates.
- AI governance pack / ISO 42001.
- Digital-transformation maturity pack.
- Mobile/PWA approval experience.
