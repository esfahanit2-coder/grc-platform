# Explicit CI-only full seven-image requalification request

Request date: 2026-10-13 UTC (post PR #180 UX localization)
Tracking: https://github.com/esfahanit2-coder/grc-platform/issues/157 (release candidate handoff)
Accepted source at request time: `60e339694d57093e14a1a4b54dfbeefd159423ba`
Acceptance: Run the existing **fail-closed** scanned seven-image offline cold-install workflow once on the exact PR source checkout, and then again independently on the newly merged protected `main`. The signed temporary archive must install from its exact scanned image IDs, use disposable one-run synthetic TLS/keys, run the GRC golden scenario, and emit source-SHA-bound non-secret metadata.

**This file is a manual, auditable workflow trigger marker.** Editing it deliberately re-runs the expensive `ephemeral-scanned-full-release` workflow; ordinary UX commits should **not** automatically run that workflow. Always take final source SHA from `git rev-parse HEAD` of the actual runner checkout. The SHA printed above is **historical, not a predicted release SHA**.

Security and commercial boundaries: no actual release signature/key, no customer files, licensed standards content or non-synthetic records, no upload of full archives, no live datacenter host, no customer-approved SoA, and no independent pentest. GitHub CI SUCCESS cannot close commercial custody issue #161 or full-product approval issue #157. Customer target-host, DR, RPO/RTO, human UX and user acceptance remain outstanding.

## Requalification after PR #180

The earlier synthetic full seven-image cold-install on `main@e3e83b1809bc8d02f441e849b067226484bfefd5` passed on run [38378796195](https://github.com/esfahanit2-coder/grc-platform/actions/runs/38378796195), but that does **not** validate the later code of PR #180. This marker explicitly requests a fresh fail-closed requalification that includes Persian state labels, mobile risk scroll accessibility cues and genuine Chromium-checked risk/control/evidence pages.

Require exact PR-head Backend/Frontend, security/release-ready, full scanned seven-image signed-disposable cold install, behind=0, SHA-bound COMMENTED technical review and zero unresolved review threads before guarded squash merge. Recheck **separate protected new-main** workflows and verify artifact `source_commit == git rev-parse HEAD` of new main and `disposable_signed_full_archive_cold_install_golden_passed == true`. Previous synthetic PR merge SHA is not branch HEAD. Keep #161 commercial custody, #7 physical target host/recovery, #8 independent pentest, #42 human UX and #74 customer UAT OPEN.
