# Branching and Releases

## Branches

- `main`: canonical deployable branch; must remain protected by CI once workflows are enabled.
- `import/pilot-candidate`: one-time branch for importing the existing Pilot Candidate source tree.
- `feature/*`: short-lived product/engineering work.
- `fix/*`: short-lived defect/security remediation work.
- `docs/*`: documentation-only changes when useful.

## Pull requests

Every material code change should be reviewed via PR. Required review topics include tenant isolation, organization scope, auditability, migrations, AI human-review boundaries and restricted standards content.

## Release naming

Planned sequence:

- `v0.9.0-pilot`
- `v1.0.0-rc1`
- `v1.0.0`

Tagged release is blocked until runtime CI, frontend lockfile, migration tests, security checks and release reproducibility gates pass.
