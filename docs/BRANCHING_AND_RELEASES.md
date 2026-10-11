# Branching and Releases

## Branches

- `main`: canonical deployable branch. Changes must reach it through a validated pull request once the protection policy below is active.
- `import/pilot-candidate`: historical one-time branch used for importing the existing Pilot Candidate source tree.
- `feature/*`: short-lived product/engineering work.
- `fix/*`: short-lived defect/security remediation work.
- `docs/*`: documentation-only changes when useful.

## Pull requests

Every material code change should be reviewed through a pull request. Required review topics include tenant isolation, organization scope, auditability, migrations, AI human-review boundaries and restricted standards content.

The repository uses exact-head validation: a green workflow result belongs only to the commit SHA that produced it. If the PR head changes, the new head must pass the required checks again before merge.

## `main` protection policy

Issue #40 tracks verification and continuing maintenance of this policy in GitHub repository administration. The policy is intentionally compatible with a single-owner repository: automated release gates are mandatory, but a second human approval is not required merely to satisfy process.

Preferred implementation: an active GitHub **branch ruleset** targeting only `refs/heads/main`. Classic branch protection is acceptable if it enforces the same controls.

Required controls:

1. **Require a pull request before merging.** Direct unvalidated changes to `main` are not an accepted development path.
2. **Require status checks to pass before merging** and require the branch to be up to date with `main` before merge.
3. Configure these exact GitHub Actions check names as required checks:
   - `runtime / backend`
   - `runtime / frontend`
   - `release-ready`

   The Release Gate workflow's `release-ready` job requires the separate `security` job to succeed; therefore `security` is **transitively enforced**, not a fourth independently configured required check. Do not delete the upstream security dependency or weaken this release-ready guard.
4. **Require conversation resolution before merging.** Unresolved review threads block merge.
5. **Block force pushes** to `main`.
6. **Restrict deletion** of `main`.
7. Do **not** require a human approval count greater than zero while this repository has a single owner. Security-sensitive work still receives explicit review where another authorized reviewer is available, but repository policy must not force self-approval.
8. Keep bypass capability minimal. Prefer no routine bypass actor. If an emergency administrative bypass is retained, restrict it to repository administrators/owners and record the reason, affected SHA and follow-up validation in a tracked issue or incident record. GitHub Actions should not receive a general merge-policy bypass.

### Owner/Admin application steps

In GitHub:

1. Open **Settings → Rules → Rulesets**.
2. Create or inspect the existing **Branch ruleset** named `GRC - Protect Main Branch` (ruleset ID `24891630`).
3. Set enforcement to **Active**.
4. Target the default branch or explicitly include `refs/heads/main` only.
5. Enable the controls listed above.
6. Under required status checks, select the three exact checks listed above from GitHub Actions (including `release-ready`, which fails if `security` fails).
7. Enable the option that requires the PR branch to be up to date before merging.
8. Keep required approvals at `0` for the current single-owner operating model.
9. Review the bypass list and remove any actor that does not have a documented operational need.
10. Save the ruleset.

### Active repository ruleset snapshot (verified 2026-10-11)

- GitHub repository: `esfahanit2-coder/grc-platform` (public); rule: [`GRC - Protect Main Branch`](https://github.com/esfahanit2-coder/grc-platform/rules/24891630), `active`, target `~DEFAULT_BRANCH` (`main`).
- GitHub branch endpoint reports `main.protected=true`; current user bypass is `never`.
- Rules include `deletion`, `non_fast_forward`, `creation`, `pull_request` (required approvals `0`, required review-thread resolution), `required_status_checks` (three names above, GitHub Actions source, strict/up-to-date), and `required_linear_history`.
- Extra `creation` restriction prevents recreating the protected default branch, not creating normal feature branches.
- The server-side ruleset is authoritative. Re-check its current state after any rules change; this snapshot is historical evidence only.

### Verification after applying the rule

Issue #40 may be closed only after all of the following are observed on GitHub:

- `main` is reported as protected by an active rule/ruleset;
- a PR with a pending or failing required check cannot merge;
- moving the PR head requires checks on the new SHA rather than accepting stale green results;
- an unresolved review conversation blocks merge;
- direct force-push and branch deletion are blocked according to policy;
- the configured bypass list matches the documented minimal exception policy.

A **non-destructive negative check** may use a normal ready-for-review test PR and read GitHub's `mergeable_state` / ruleset check verdict **before required checks finish**. Verify that the PR is blocked for missing/pending checks, then allow the exact head to finish its checks. Never test by deliberately force-pushing, deleting, or committing directly to production `main`. To show that a changed head invalidates stale green checks, amend only the PR feature branch and re-inspect the new check SHA; do not modify `main` for a negative test.

Repository CI cannot prove these administration controls. The final verification must be performed against the actual GitHub repository configuration.

## Merge discipline

Before merging any PR to `main`:

1. confirm the PR head SHA has not moved since the validated workflow runs;
2. require successful `runtime / backend`, `runtime / frontend` and `release-ready` checks for that exact head (including upstream `security=success` in the Release Gate);
3. confirm there are no unresolved review conversations;
4. prefer squash merge unless preserving individual commits is specifically justified;
5. after merge, confirm the push-triggered `main` CI succeeds on the resulting merge/squash commit.

## Release naming

Real-host acceptance uses an **untagged signed Server Candidate artifact** before any GitHub release tag is promoted.

Candidate artifact convention:

```text
v0.9.0-pilot-<12-char-source-sha>
```

The candidate label is bound to the full source SHA and exact image identities inside the signed offline manifest. It does not imply Pilot acceptance, RC approval or production readiness.

Planned promoted tag sequence:

- `v0.9.0-pilot`
- `v1.0.0-rc1`
- `v1.0.0`

Tagged release is blocked until runtime CI, frontend lockfile, migration tests, security checks and release reproducibility gates pass, together with the applicable external acceptance evidence tracked by the active release blockers.
