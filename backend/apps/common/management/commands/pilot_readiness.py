import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = "Run non-destructive pilot readiness checks."
    def handle(self,*args,**options):
        failures=[];warnings=[]
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version=cursor.fetchone()[0]
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
            row=cursor.fetchone()
        self.stdout.write(f"Database: {db_version}")
        if row:self.stdout.write(self.style.SUCCESS(f"pgvector: {row[0]}"))
        else:failures.append("pgvector extension is not enabled")
        if getattr(settings,"APP_ENV","development")=="production":
            if settings.DEBUG: failures.append("DEBUG must be disabled in production")
            if not settings.SECURE_SSL_REDIRECT: warnings.append("SECURE_SSL_REDIRECT is disabled")
            if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE: failures.append("Secure cookies are required")
            if settings.SECRET_KEY in {"unsafe-dev-key","change-me-in-production"}: failures.append("Production secret key is not configured")
        if not os.getenv("S3_ENDPOINT_URL") and not os.getenv("S3_BUCKET"): warnings.append("Object storage settings are not explicitly configured")
        for item in warnings:self.stdout.write(self.style.WARNING("WARN: "+item))
        if failures:
            for item in failures:self.stdout.write(self.style.ERROR("FAIL: "+item))
            raise SystemExit(2)
        self.stdout.write(self.style.SUCCESS("Pilot readiness checks passed"))
