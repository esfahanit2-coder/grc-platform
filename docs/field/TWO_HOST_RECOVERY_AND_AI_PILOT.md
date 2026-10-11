# Two-host field acceptance: signed GRC recovery, local AI and real RPO/RTO

**Status:** operator execution plan, **NOT executed / NOT customer accepted**  
**Scope:** Issue [#7](https://github.com/esfahanit2-coder/grc-platform/issues/7); release [#68](https://github.com/esfahanit2-coder/grc-platform/issues/68) and UAT [#74](https://github.com/esfahanit2-coder/grc-platform/issues/74).  
**Canonical details:** [DATACENTER_OPERATIONS.md](../DATACENTER_OPERATIONS.md), [PILOT_ACCEPTANCE_EVIDENCE.md](../PILOT_ACCEPTANCE_EVIDENCE.md), [PILOT_OPERATIONS.md](../PILOT_OPERATIONS.md). This is a field handoff that uses those procedures, **not** an alternative restore implementation.

## What this drill must prove

A customer-authorized operator can restore **one consistent release point** of PostgreSQL, S3 Evidence and protected configuration from an **approved encrypted, separately controlled backup** onto **host B, genuinely independent of source host A**. Host B must use the **same exact signed release/source commit** and approved cryptographic identity, and must demonstrate tenant UI, authentication/MFA, Evidence bytes, health and local AI under an independently checked egress block. Observed RPO and RTO are **real field observations**, not GitHub-runner timings or product promises.

This test is mandatory before closing #7; it alone cannot close independent security acceptance #8, framework rights #5, live connectors #6, UI evidence #42 or final customer UAT #74.

**Environment definitions**

| Environment | Mandatory distinction | Required internal record |
| --- | --- | --- |
| Host A — source pilot | Signed application and original **real running** PostgreSQL/S3 volume(s) | Host/VM identity, approved subnet, OS, release SHA, storage identifier and change ticket |
| Custody C — recovery medium | Encrypted storage physically/logically **outside** source data volumes and under the customer's approved custody | Encryption control, access approver, sealed-media/transfer reference, custody timestamps; never attach secrets |
| Host B — replacement | A different host/VM and storage fault domain with its **own Docker daemon and previously unused volumes**; not a second Compose project on host A | Separate host/VM/OS/storage identifiers and network-zone approval |
| Reviewer R | Named security/operations reviewers with authority to accept actual evidence | Change authorization, RPO/RTO objectives and UAT approval references |

**Hard preconditions:** obtain the customer change/maintenance window, a *disposable* test tenant and test Evidence, backup restoration permission, explicit destructive approval **only for host B**, operator access to approved release key and PKI, original protected application cryptographic keys, network flow matrix, local licensed model artifacts, and capacity/time to retain the original backup. **Never perform this drill against live customer production data without formal, independently approved maintenance and rollback.**

## Stage 0 — approval and independent topology (STOP if any item is missing)

1. Assign an accountable recovery operator and a different reviewer. Record both in the [execution record template](PILOT_EXECUTION_RECORD_TEMPLATE.md). Identify host A and B by infrastructure inventory identifiers, not fabricated evidence or copied screenshots.
2. Record customer-approved RPO **objective** and RTO **objective** *before* the test. Explicitly define when service loss begins and when service is considered restored (authenticated workflow complete, not just container health). Define what business records must survive.
3. Confirm source and replacement do **not** share the same virtual machine, Docker daemon, PostgreSQL volume, SeaweedFS volume or primary failure domain. A storage snapshot mounted by both is not evidence of independent recovery. Explicitly check the rendered target Compose configuration and storage endpoint destinations: host B's PostgreSQL, Redis and S3 connections must resolve **only to approved isolated recovery services**. A B-side S3 endpoint pointing to host A or production object storage is a **hard STOP**, because replace-restore can remove objects in that bucket.
4. Freeze exact source commit, immutable image IDs, signed offline manifest/bundle identity, separately approved trusted public key fingerprint and source-to-target PostgreSQL **major version**. A GitHub green badge alone does not provide customer signing-key trust.
5. Confirm customer-managed TLS chain/SAN/hostname trust, replacement DNS/routing and **fencing/no-split-brain** procedure. Do not connect two writable copies to the same production endpoints.
6. Approve backup-encryption/custody arrangement independently of GRC: transport protection, storage encryption, restricted access and private recovery artifact retention/deletion. The GRC backup checksum file **is not a signed authenticity proof**.
7. Approve the allowed service and AI network flows. Confidential local AI tests require an **actually observed deny of Internet egress**, not merely an application setting.
8. Create exactly one restricted evidence folder through the customer's approved document/incident system. Its public reference ID may be listed in GitHub; raw dumps, `.env`, private keys, logs, malware samples, personal data, AI prompts/outputs and Evidence payloads must not be.

### STOP and do not start destructive work if

- Recovery media custody, approved authorization or trusted signing key is missing; SHA/source or PostgreSQL-major version is incompatible.
- Encrypted data keys from backup cannot be recovered, `S3_BUCKET` differs, target config has unsafe permissions, or the `recovery-preflight` command fails.
- Host B is not independent, is not disposable/approved, or could expose the recovered service alongside the still-active source (split brain).
- Network controls, time synchronization, TLS/PKI or source rollback plan are not signed off.
- The restore would rely on an unreviewed forward-compatible migration or a PostgreSQL major upgrade.

## Stage 1 — source-host signed installation and controlled markers

On **A**, use the *already installed and verified* approved signed release. Confirm the output of:

```bash
git rev-parse HEAD
bash scripts/datacenterctl verify
```

Use real browser/API workflows to create a uniquely traceable *synthetic* pre-backup business marker (e.g. an Action) and an uploaded Evidence file. In the **restricted** record, capture their opaque IDs, event timestamps and SHA-256 of Evidence content **without** recording the content itself. Confirm a real authenticated login and a successful Evidence download/hash before backup.

Use one unique safe backup name chosen by the operator, for example `dr-test-<approved-id>` (replace placeholder; no angle brackets in the command):

```bash
bash scripts/datacenterctl backup <approved-backup-name>
bash scripts/datacenterctl backup-status --restore-preflight <approved-backup-name>
```

The canonical datacenter backup quiesces writers. Its backup observation and archive are in `backups/<approved-backup-name>/`, which contains **secret-bearing `config.env`**. Handle the entire backup directory as confidential material.

After the backup is complete, unquiesce/start the normal source application as approved, create a **different** synthetic *post-backup* Action and Evidence marker, and record their IDs/timestamps. These later changes must **not** appear on B after restoring the earlier consistent point.

## Stage 2 — encrypted custody C and offline handoff

1. Copy **the whole canonical backup directory without modifying any file**, through the customer's approved encrypted transfer/media procedure. Avoid archiving one database while leaving Evidence from another point.
2. Independently retain the approved signed release bundle + trusted **public** key outside the recovery backup; verify the trusted key fingerprint by a known-good channel (not from the bundle or this repository).
3. Record send/receive timestamps, operator and receiver, encrypted-media control IDs, archive size and an externally witnessed SHA-256 of the transferred protected blob or custody envelope. The built-in `SHA256SUMS` checks accidental modification, **not** an adversarial source substitution.
4. Deliver the approved original `DJANGO_SECRET_KEY`, `AUDIT_INTEGRITY_KEY` and `MFA_ENCRYPTION_KEY` using customer-controlled secret recovery. **Do not paste their values in tickets, GitHub, chat or screenshots.** The restored `S3_BUCKET` identity must be unchanged; source PostgreSQL/S3 access passwords and target TLS paths may be different after a reviewed target configuration migration.
5. Record complete custody transitions until host B receives the material. If custody or integrity cannot be established, stop.

### Optional authenticated, encrypted transport using customer-managed age keys

The datacenter operator now has an **optional** streaming custody path. It is **not** a substitute for the customer's media encryption, access-control, approved recipient identity or chain of custody. The audited open-source `age` and `age-keygen` executables are **external optional prerequisites** and must be provisioned through the customer's approved offline package process; GRC never creates or stores the customer's decryption identity. The backup itself remains unencrypted in its existing protected source directory until the organization's retention/cleanup procedure disposes of it.

With a **recipient PUBLIC key file** independently approved by the intended host-B custodian, on host A after the quiesced backup and preflight:

```bash
bash scripts/datacenterctl custody-export <approved-backup-name> \
  /secure/approved-age-recipients.txt /mnt/encrypted-custody/backup-transfer.age
```

The command revalidates the complete backup (PostgreSQL/S3 archive and hashes), then streams only canonical files through the external **age authenticated recipient-encryption CLI** into a new encrypted `.age` file. It neither copies secret-bearing plaintext to a second TAR file nor replaces an existing custody artifact. The recipient list must be verified with the custodian **out of band**; age encryption does not itself attest who originated the ciphertext, or that the media crossed a real failure-domain boundary.

Transfer this ciphertext using the approved external custody workflow; record envelope digest/size, custody handoffs and approved access controls **without** recording key values. On host B, after the signed installation has created a mode-0700 empty `backups/` directory, decrypt using a separate, customer-controlled **PRIVATE age identity file with mode 0600**, on an at-rest-encrypted destination filesystem:

```bash
cd <empty-install-root>/repository
bash scripts/datacenterctl custody-import <approved-backup-name> \
  /mnt/encrypted-custody/backup-transfer.age /secure/age-identity.txt
bash scripts/datacenterctl recovery-preflight <approved-backup-name>
```

The importer streams decrypted TAR members into a restricted temporary directory, permits **only** known regular canonical backup files (no symlinks, traversal, duplicates or extra members), checks completed authenticated decryption, and runs the same full official restore-preflight **before** moving the backup into its final absent name. If it fails, the temporary extraction is removed; it never overwrites an existing backup. **Plaintext PostgreSQL/S3/config will exist in host B's restricted, approved, encrypted-at-rest backup folder after import.** Restrict this folder; clean up only under retention policy. The private age identity stays outside the repository, CI, GitHub, support bundles and chat. A successful local encrypted/decrypted roundtrip still does **not** prove customer-controlled custody, second-host isolation, acceptance RPO/RTO or authorized signing keys.

The existing manual encrypted-media process is still supported. Do not skip the signed release verification, independent host storage/endpoints check, read-only `recovery-preflight`, approved destructive action or actual application markers if choosing `custody-export/import`.

## Stage 3 — install onto genuinely separate host B

**Do not start the application on B yet.** Prepare a hardened B under the customer's OS policy with prerequisites in `docs/DATACENTER_OPERATIONS.md`, independent Docker volumes, customer TLS private key/certificate **outside backup custody**, offline signed source/images and an approved host-specific mode-0600 `.env` preserving the protected original cryptographic identities.

From the approved **installer checkout** (not from an untrusted extracted directory), verify the release with the **independently trusted** public key, then install the exact bundle to a clean empty destination:

```bash
bash scripts/offline-release-verify.sh <signed-release-bundle> <trusted-public-key>
OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
  <signed-release-bundle> <trusted-public-key> <empty-install-root> <approved-target-env-file>
```

On B only: **choose one** approved transport method. For the existing manual transfer path, copy the verified custody backup directory into `<empty-install-root>/repository/backups/<approved-backup-name>/` with access-restricted permissions. For the optional **age envelope** path above, use `custody-import` from the installed B checkout instead; do not copy or overwrite the restored directory again. Then `cd` into `<empty-install-root>/repository`. Confirm the canonical backup contents are protected, readable by the operator and unmodified. The target `.env` is already provisioned: generating new independent application cryptographic keys on B is **not** a valid recovery of signed/encrypted records.

Before **any** destructive restore or new destination database creation:

```bash
git rev-parse HEAD
bash scripts/datacenterctl recovery-preflight <approved-backup-name>
```

The preflight must return exit code **0** and JSON `ready_for_operator_review=true`; `backup_integrity`, `critical_config_identity` and `exact_source_commit` must each be `ok=true`. Its PASS does not attest independent B, custody or signed artifact provenance. Verify externally that target Docker volumes were not previously shared/used, using the site's container inventory and approved change record.

With explicit **host-B-only** destructive approval, bring up restored dependencies and data:

```bash
RESTORE_INITIALIZE_MISSING_BUCKET=YES CONFIRM_RESTORE=YES \
  bash scripts/datacenterctl restore <approved-backup-name>
bash scripts/datacenterctl verify
```

The `RESTORE_INITIALIZE_MISSING_BUCKET=YES` option is **only** for a newly absent, approved bucket and never for authorization failures or a wrong bucket identity. It is off by default. Do **not** casually set `RESTORE_CONFIG=YES`: that would replace target config with A's saved hostname/TLS/storage settings and demands separately reviewed host-specific compatibility. If cryptographic identity fails, stop and have the custodian provision matching protected keys; do not bypass preflight. If the underlying S3 replacement fails halfway, do not attempt a partial live repair: preserve original encrypted backup, follow the approved complete coordinated recovery procedure and reverify every marker.

## Stage 4 — independent functional verification and observations

On host B, under the approved test-only DNS/routing boundary (source A fenced appropriately), exercise **real** customer-facing workflows:

| Test | Evidence requirement | Fail condition |
| --- | --- | --- |
| Signed runtime | Exact manifest/source SHA, image identities; `datacenterctl verify` | Source/version mismatch, untrusted TLS, unhealthy service |
| Data consistency | Pre-backup Action exists, post-backup Action is absent | Wrong cutoff, cross-point SQL/Evidence |
| Evidence | Pre-backup Evidence downloads; original content SHA-256, metadata and access controls match; post-backup marker absent | Missing, corrupted or readable by unauthorized tenant |
| Identity/security | Browser TLS, authenticated login, MFA, Secure cookies/CSRF, permissions and tenant isolation | Any cross-tenant exposure, authentication/CSRF bypass |
| Background operations | Worker/beat task executed and real operational alert/health checked | Silent queue/task failures |
| Real local AI | Licensed model artifacts preloaded, generation **and embedding** through `pilot_readiness --ai-provider-id`, actual egress DENY proof, AI-disabled mode, provider switch | Calls Internet, model fake/absent, confidential content egress |
| Monitoring | Operator metrics/backup freshness checked, alert and SIEM handoff reference as applicable | Undetected service or backup failures |
| RPO/RTO | Measured outage/cutoff with timestamps, signed reviewer decision vs **pre-agreed** objectives | Missing real measurements or exceeded objectives |

For the local-AI step, follow `docs/PILOT_OPERATIONS.md` and `docs/PILOT_ACCEPTANCE_EVIDENCE.md`: set **real** approved tenant/model/provider configuration on B, block external egress **through the approved network-control plane**, and collect independently verifiable firewall/flow observations. Do not use the disposable CI Ollama placeholder as proof. `AI_PROVIDER_ID` passed to a smoke test only proves an invocation, not network isolation. Record test of AI-disabled functionality as a separate observation.

**RTO (field):** separately record outage declared at `T_outage`, restore initiated at `T_restore_start`, first service readiness at `T_health`, and authenticated functional/Evidence/AI validation complete at `T_usable`. Report both tool `observed_rto_seconds` and **business-visible RTO = T_usable - T_outage**, with clock-source consistency and operator identity. These quantities are not interchangeable.

**RPO (field):** record last controlled business write intended to be recoverable at `T_last_retained`, backup consistency boundary, first deliberately nonrecovered post-backup write at `T_first_lost`, and outage `T_outage`. Report the approved business definition and measured recovery cutoff/lost-window bound, including whether all markers demonstrate the claimed boundary. Do **not** derive a customer SLA from CI, backup duration or a single marker without reviewing the production write pattern.

## Stage 5 — package evidence, review and handover

From B's approved restricted checkout, copy the repository template into Git-ignored runtime storage and complete it with **real** reviewer references (never fill hypothetical `PASS`):

```bash
mkdir -p runtime
chmod 700 runtime
cp docs/PILOT_MANUAL_OBSERVATIONS.example.json runtime/pilot-manual-observations.json
chmod 600 runtime/pilot-manual-observations.json

python3 scripts/pilot-acceptance-evidence.py \
  --tls \
  --base-url https://<approved-target-hostname>/ \
  --ai-provider-id <REAL_AI_PROVIDER_UUID> \
  --ai-tenant-code <PILOT_TENANT_CODE> \
  --backup-observation backups/<approved-backup-name>/backup-observation.json \
  --restore-observation backups/<approved-backup-name>/restore-observation.json \
  --manual-observations runtime/pilot-manual-observations.json \
  --require-complete
```

The operator should run the exact command **after** replacing the placeholders and configuring required local AI. `--require-complete` must remain; missing checks are blockers, not waivers. The collector's `acceptance-summary.json` is a **low-risk derivative**; keep raw confidential records under the customer's restricted custody. A reviewer checks the real referenced evidence and exact SHA. The handoff uses [PILOT_EXECUTION_RECORD_TEMPLATE.md](PILOT_EXECUTION_RECORD_TEMPLATE.md). A failed check or insufficient measurement means **BLOCKED**, with owner/remediation and a controlled retest plan.

After the customer/operator acknowledges evidence and isolation, follow the approved cleanup/retention plan for **host B test state**, keep a defensible copy of the original sealed backup, revoke temporary test access and ensure A is restored to its intended independent configuration. Never automatically promote B into production routing.

## Final no-go boundaries

Only human, named reviewers can accept host-separation, custody, RPO/RTO, browser/security and real local AI. CI and this document prove **no** live external observations. Close #7 only when all its real-host acceptance checks and references pass, then continue independent issues #5, #6, #8, #42 and final #74. Do **not** create a production release tag merely because this checklist is complete or `ready_to_close_issue_7` is reported without validated referenced evidence.
