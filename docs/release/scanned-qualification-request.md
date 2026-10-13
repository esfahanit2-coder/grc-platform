# Explicit CI-only full seven-image requalification request

Request date: 2026-10-13 UTC
Tracking: https://github.com/esfahanit2-coder/grc-platform/issues/177
Accepted source at request time: `f0e53bcc0922cfb77ba020d252047ea6401cd3fd`
Acceptance: Run the existing **fail-closed** scanned seven-image offline cold-install workflow once on the exact PR source checkout, and then again independently on the newly merged protected `main`. The signed temporary archive must install from its exact scanned image IDs, use disposable one-run synthetic TLS/keys, run the GRC golden scenario, and emit source-SHA-bound non-secret metadata.

**This file is a manual, auditable workflow trigger marker.** Editing it deliberately re-runs the expensive `ephemeral-scanned-full-release` workflow; ordinary UX commits should **not** automatically run that workflow. Always take final source SHA from `git rev-parse HEAD` of the actual runner checkout. The SHA printed above is **historical, not a predicted release SHA**.

Security and commercial boundaries: no actual release signature/key, no customer files, licensed standards content or non-synthetic records, no upload of full archives, no live datacenter host, no customer-approved SoA, and no independent pentest. GitHub CI SUCCESS cannot close commercial custody issue #161 or full-product approval issue #157. Customer target-host, DR, RPO/RTO, human UX and user acceptance remain outstanding.
