# Release blockers

The current repository is a **Pilot Candidate**, not a production release.

## Blocking before a tagged release

1. Import the complete Pilot Candidate codebase into this canonical repository.
2. Generate and commit `frontend/package-lock.json` from a trusted connected environment.
3. Pass `.github/workflows/release-gate.yml` using `npm ci`.
4. Pass all Django migrations and tests against PostgreSQL 18 + pgvector.
5. Pass Next.js lint and production build.
6. Run `python manage.py check --deploy` with the actual production environment.
7. Pin production container images to organization-approved tags or immutable digests.
8. Configure an approved S3-compatible object store and prove backup/restore.
9. Configure MFA encryption key and production secret management.
10. Test connector credentials using least-privilege service accounts / API administrators.
11. Perform a security test focused on tenant isolation, scoped RBAC, IDOR, file upload, CSRF/cookie auth and connector SSRF boundaries.

## Content/legal blocker

Do not bundle proprietary ISO/COBIT/AFTA text unless the distribution/use license explicitly permits embedding that content in the product. The included pilot baseline is original content and is intended only to prove the engine and workflow.
