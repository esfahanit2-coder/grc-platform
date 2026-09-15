# Changelog

This project follows semantic versioning once tagged releases begin.

## Unreleased — Pilot Candidate

### Added
- Multi-tenant foundation and scoped RBAC.
- TOTP MFA and tenant security settings.
- Framework/version/requirement engine with import/export, translations and crosswalks.
- Common control library and organization-specific implementations.
- Asset register, configurable risk methodology, historical evaluations, treatments and RTP.
- Compliance assessments, reusable evidence, findings and CAPA.
- Internal audit, workpapers, control testing and document approval/versioning.
- SoA, RTP and audit/report generation.
- AI provider abstraction, local AI support, human-reviewed AI suggestions and RAG.
- Generic workflows, notifications and production cookie/CSRF hardening.
- pgvector semantic/hybrid pilot retrieval.
- Read-only pilot connectors for AD/LDAP, Tenable/Nessus, Veeam and FortiGate.
- Golden pilot E2E test and pilot deployment composition.

### Known release blocker
- A committed `frontend/package-lock.json` is required before an official tagged release.
