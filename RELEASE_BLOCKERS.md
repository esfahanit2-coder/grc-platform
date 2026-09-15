# Release blockers

The current repository is a **Pilot Candidate**, not a production release.

## Blocking before a tagged release

1. Generate and commit `frontend/package-lock.json` from a trusted connected environment.
2. Pass `.github/workflows/release-gate.yml` using `npm ci`.
3. Pass all Django migrations and tests against PostgreSQL 18 + pgvector.
4. Pass Next.js lint and production build.
5. Run `python manage.py check --deploy` with the actual production environment.
6. Pin production container images to organization-approved tags or immutable digests.
7. Configure an approved S3-compatible object store and prove backup/restore.
8. Configure MFA encryption key and production secret management.
9. Test connector credentials using least-privilege service accounts / API administrators.
10. Perform a security test focused on tenant isolation, scoped RBAC, IDOR, file upload, CSRF/cookie auth and connector SSRF boundaries.

## Content/legal blocker

Do not bundle proprietary ISO/COBIT/AFTA text unless the distribution/use license explicitly permits embedding that content in the product. The included pilot baseline is original content and is intended only to prove the engine and workflow.
