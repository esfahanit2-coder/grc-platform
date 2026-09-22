from pathlib import Path

from django.test import SimpleTestCase


class PilotBackupComposeContractTests(SimpleTestCase):
    def test_backup_preserves_tls_and_local_ai_compose_context(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "scripts" / "pilot-backup.sh").read_text(encoding="utf-8")

        self.assertIn('if [[ "${PILOT_TLS:-NO}" == "YES" ]]', script)
        self.assertIn("COMPOSE+=(-f docker-compose.pilot.tls.yml)", script)
        self.assertIn('if [[ "${PILOT_LOCAL_AI:-NO}" == "YES" ]]', script)
        self.assertIn("COMPOSE+=(--profile local-ai)", script)

        compose_declaration = script.index("COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml)")
        tls_override = script.index("COMPOSE+=(-f docker-compose.pilot.tls.yml)")
        first_service_action = script.index('"${COMPOSE[@]}" --profile ops run')
        self.assertLess(compose_declaration, tls_override)
        self.assertLess(tls_override, first_service_action)
