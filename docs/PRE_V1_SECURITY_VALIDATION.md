# Pre-v1 Security Validation Register

Status: **IN PROGRESS**  
Issue: #8  
Target: v1.0.0-rc1  
Last updated: 2026-09-16

This document separates CI-verifiable security controls from validation that requires a real deployment, an approved malware scanner, or an independent penetration tester. A control is not marked complete merely because a mock or synthetic test exists.

## Automated validation scope

The pre-v1 automated suite covers or is being extended to cover:

- tenant isolation and direct cross-tenant object-ID access;
- organization-scoped RBAC boundaries;
- public authentication throttling;
- MFA challenge flows and TOTP replay resistance;
- cookie authentication and CSRF enforcement;
- evidence upload active-content rejection and malware-clearance download gating;
- connector SSRF, redirect, TLS and secret-handling boundaries;
- RAG organization scope, classification controls and untrusted-context framing;
- sandboxed report rendering with external/local resource fetch disabled;
- sensitive document/report export audit events;
- release SAST, secret scan and HIGH/CRITICAL container vulnerability gates.

## Finding / remediation register

| ID | Finding | Severity | Owner | Due | Status | Retest evidence |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-001 | Public login/MFA/refresh endpoints lacked dedicated throttles | High | Backend/Security | 2026-09-30 | Remediated in security branch | CI pending |
| SEC-002 | Accepted TOTP could be replayed during its validity window | High | Backend/Security | 2026-09-30 | Remediated with persisted atomic time-step consumption | CI pending |
| SEC-003 | WeasyPrint report templates could attempt network/local URL fetches | High | Backend/Security | 2026-09-30 | Remediated; only `data:` fetches allowed | CI pending |
| SEC-004 | Uploaded evidence had no fail-closed malware-clearance download gate | High | Backend/Security | 2026-09-30 | Exposure remediated; production requires `clean` status | CI pending; real scanner integration still required operationally |
| SEC-005 | Sensitive document/report exports were not consistently audited | Medium | Backend | 2026-09-30 | Remediated for document, SoA and template exports | CI pending |
| SEC-006 | Retrieved RAG text was blended into the prompt without explicit untrusted-evidence framing | Medium | AI/Security | 2026-09-30 | Guardrail added; adversarial model evaluation still pending | CI pending |
| SEC-007 | Independent penetration test has not yet been completed or formally scheduled | Release blocker | Security/Release owner | Before v1.0.0-rc1 production approval | OPEN | External evidence required |
| SEC-008 | Database-level audit-log tamper-evidence/WORM control has not yet been independently validated | Medium | Security/Operations | Before production rollout | OPEN | Deployment/control evidence required |

Severity here is an engineering triage classification for release management; final penetration-test findings retain the independent assessor's severity.

## Evidence malware-scanning boundary

New file uploads are forced to `malware_scan_status=pending`; client-supplied claims of `clean` are overwritten. Active/executable formats are rejected before object-storage write. In production, `EVIDENCE_REQUIRE_CLEAN_DOWNLOAD=1` means a stored file cannot be downloaded until an authorized scanning/integration process marks it `clean`.

This is intentionally a fail-closed integration boundary. The repository does **not** pretend that a malware engine has scanned a file when no scanner is connected.

## RAG / prompt-injection boundary

Retrieved chunks remain permission-filtered. They are serialized as JSON and explicitly labelled untrusted evidence. System/user instructions state that commands, disclosure requests, role changes, tool requests and policy overrides inside retrieved text are data rather than executable instructions.

Prompt framing is defense-in-depth, not proof of immunity. A model-specific adversarial evaluation remains required for the actual pilot model/version before security sign-off.

## External penetration test

Current state: **NOT SCHEDULED / NOT COMPLETED**.

Before production rollout, the release owner must attach evidence that an independent test is completed or formally scheduled. Minimum scope must include tenant isolation/IDOR, privilege escalation, authentication/MFA/session/CSRF, upload/download boundaries, connector SSRF, report rendering, AI/RAG leakage and prompt injection, and audit/export behavior.

## Security sign-off

Current state: **PENDING**.

Sign-off is blocked until:

1. latest-head CI and release-security gates pass for the security hardening PR;
2. no unresolved Critical/High engineering or penetration-test finding remains for the RC;
3. open findings have owners, dates and retest evidence;
4. the external penetration test is completed or formally scheduled;
5. the real pilot environment validates the relevant production settings and operational controls.
