# Two-host GRC field drill — blank operator execution record

**TEMPLATE ONLY — NO OBSERVATIONS HAVE BEEN MADE.** Copy this form into the customer's restricted evidence-management system; never commit a completed version with host identities, backup names, protected paths, credentials, raw application logs, data or customer payloads. Enter actual values only after observing them. Public GitHub issues may include a sanitized **reference ID**, not this restricted execution record.

This form is used with [TWO_HOST_RECOVERY_AND_AI_PILOT.md](TWO_HOST_RECOVERY_AND_AI_PILOT.md) and `docs/PILOT_ACCEPTANCE_EVIDENCE.md`.

## 1. Identity and approval

| Field | Actual value or restricted evidence reference |
| --- | --- |
| Change ticket / maintenance approval | **NOT RECORDED** |
| Scenario, environment and pilot tenant | **NOT RECORDED** |
| Approved exact signed release SHA / manifest | **NOT RECORDED** |
| Signing-public-key verification reference | **NOT RECORDED** |
| Operator / independent reviewer | **NOT RECORDED** |
| Host A independent inventory/fault-domain reference | **NOT RECORDED** |
| Host B independent inventory/fault-domain reference | **NOT RECORDED** |
| Approved encryption and backup custodian reference | **NOT RECORDED** |
| Recovery window and controlled test traffic / fencing approval | **NOT RECORDED** |
| Approved RPO objective / business definition | **NOT RECORDED** |
| Approved RTO objective / business definition | **NOT RECORDED** |
| Target TLS/DNS/PKI and approved network-flow reference | **NOT RECORDED** |
| Signed/destructive host-B authorization reference | **NOT RECORDED** |

## 2. Transfer and failure-domain evidence

| Check | Initial status | Internal witness/reference and observation time |
| --- | --- | --- |
| Source signed images/SHA verified | NOT_OBSERVED | — |
| Separate host/VM, Docker daemon and storage domain proved | NOT_OBSERVED | — |
| Host A/host B fencing/no split brain proved | NOT_OBSERVED | — |
| Backup captured with application writers quiesced | NOT_OBSERVED | — |
| Whole backup encrypted and under independently approved custody | NOT_OBSERVED | — |
| Signed release trust key obtained through independent channel | NOT_OBSERVED | — |
| Custodian-to-custodian send/receive acknowledged | NOT_OBSERVED | — |
| Backup / object archive integrity on B | NOT_OBSERVED | — |
| Crypto identity, bucket identity and exact SHA on B | NOT_OBSERVED | — |
| Actual `datacenterctl recovery-preflight` on B | NOT_OBSERVED | — |
| B target volumes pristine before restore | NOT_OBSERVED | — |

**Restricted custody ledger** (keep raw media and cryptographic secret details in the organization's security vault; include only their reference IDs here):

| Event | UTC time (measured) | Accountable role | Evidence reference |
| --- | --- | --- | --- |
| Backup completed on A | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| Encrypted media handed over | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| Custodian on B received it | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| Full backup integrity verified on B | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |

## 3. Controlled data and functional outcomes

Record opaque test IDs/hash references **in restricted storage**, never the actual Evidence payload.

| Probe | Initial status | Evidence reference (actual only) |
| --- | --- | --- |
| Pre-backup Action marker present after restore | NOT_OBSERVED | — |
| Post-backup Action marker absent after restore | NOT_OBSERVED | — |
| Pre-backup S3 Evidence recovered with exact SHA-256/metadata | NOT_OBSERVED | — |
| Post-backup Evidence absent | NOT_OBSERVED | — |
| TLS chain/hostname, login, MFA, cookies, CSRF | NOT_OBSERVED | — |
| Tenant / organization scope and Evidence access denied cross-tenant | NOT_OBSERVED | — |
| Worker/beat/queue and operational monitoring alert | NOT_OBSERVED | — |
| Local approved model generation and embedding | NOT_OBSERVED | — |
| Independently verified Internet-egress block during AI test | NOT_OBSERVED | — |
| AI-disabled operation and provider switch | NOT_OBSERVED | — |
| Real scan/audit storage/pentest handoff to #8 | NOT_OBSERVED | — |
| Cleanly fenced cleanup and retest plan | NOT_OBSERVED | — |

## 4. Measured recovery windows — no estimates

All timestamps must include UTC offset and measurement/witness source. `restore-observation.json` measures an **internal tool interval**, not business RTO.

| Observation | Measured value or evidence reference |
| --- | --- |
| `T_outage`: agreed service unavailable boundary | NOT_MEASURED |
| `T_backup_cutoff`: consistent recovery point | NOT_MEASURED |
| `T_last_retained`: latest confirmed restored business write | NOT_MEASURED |
| `T_first_lost`: first confirmed excluded post-backup test write | NOT_MEASURED |
| `T_restore_start`: host B restore initiation | NOT_MEASURED |
| `T_health`: first verified HTTPS+core health | NOT_MEASURED |
| `T_usable`: authenticated business workflow and Evidence confirmed | NOT_MEASURED |
| Tool `observed_rto_seconds` | NOT_MEASURED |
| Business-visible RTO = `T_usable - T_outage` | NOT_MEASURED |
| Measured RPO boundary / lost-write interval | NOT_MEASURED |
| Measured vs pre-approved objectives and reviewer decision | **BLOCKED — NOT MEASURED** |

## 5. Acceptance checklist and ownership

| Gate | Current result | Authorized human reviewer / restricted evidence |
| --- | --- | --- |
| Real independent two-host recovery | **BLOCKED — NOT OBSERVED** | — |
| Offsite encrypted independent custody | **BLOCKED — NOT OBSERVED** | — |
| Customer-controlled signing key / TLS trust | **BLOCKED — NOT OBSERVED** | — |
| Application / Evidence restore integrity | **BLOCKED — NOT OBSERVED** | — |
| Measured RPO / RTO accepted | **BLOCKED — NOT MEASURED** | — |
| Actual Internet-denied local AI generation/embedding | **BLOCKED — NOT OBSERVED** | — |
| Browser / tenant isolation / operations checks | **BLOCKED — NOT OBSERVED** | — |
| Issue #7 low-risk `acceptance-summary.json` | **BLOCKED — NOT GENERATED** | — |
| Independent #8 security approval | **SEPARATE GATE — NOT INFERRED** | — |
| Final #74 customer UAT / RC promotion | **SEPARATE GATE — NOT INFERRED** | — |

**Open defects / retests:** NOT_RECORDED.  
**Date and signatures of named reviewer(s):** NOT_RECORDED.  
**Final operator recommendation:** **NO-GO until real evidence is accepted**.

### Rules

- Do not change `NOT_OBSERVED` to PASS from GitHub Actions, mocked data or an operator's unverified claim.
- A failed or incomplete field test remains a blocker with an assigned remediation owner, dated retest plan and signed observation.
- The low-risk collector may produce a public *sanitized report* only after reviewing the exclusion rules in `docs/PILOT_ACCEPTANCE_EVIDENCE.md`. Never upload a backup, `.env`, private TLS key, protected application keys or real Evidence/customer records.
- Close #7 only after independent reviewers verify the original restricted evidence. #8 and #74 remain separate release decisions.
