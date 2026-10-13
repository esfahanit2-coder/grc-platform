#!/usr/bin/env bash
# Real seven-image scanned/signed bundle cold-install on disposable GitHub runner only.
set -euo pipefail
umask 077
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GRC_SCANNED_INSTALL_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo 'ERROR: only opted-in disposable GitHub Actions runner permitted.' >&2
  exit 2
fi
[[ $# -eq 4 ]] || { echo 'ERROR: expected signed bundle, public key, exact SHA, images metadata.' >&2; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SIGNED="$(realpath "$1")"
PUBLIC="$(realpath "$2")"
SHA="$3"
IMAGES="$(realpath "$4")"
[[ "$SHA" =~ ^[0-9a-f]{40}$ && "$SHA" == "$(git rev-parse HEAD)" ]] || {
  echo 'ERROR: exact source SHA mismatch.' >&2; exit 2;
}
[[ -s "$SIGNED" && -s "$PUBLIC" && -s "$IMAGES" ]] || exit 2
for tool in docker openssl python realpath git sudo; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
TMP="$(mktemp -d)"
INSTALL="$TMP/installed"
HOSTNAME_CI="grc.ci.internal"
export COMPOSE_PROJECT_NAME="grcfull${GITHUB_RUN_ID:-unknown}${GITHUB_RUN_ATTEMPT:-1}"
export GRC_VERIFY_CA_CERT="$TMP/tls/server.crt"
export NO_PROXY="$HOSTNAME_CI,localhost,127.0.0.1,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
cleanup() {
  local result=$?
  trap - EXIT
  if [[ -s "$INSTALL/repository/.env" ]]; then
    (cd "$INSTALL/repository" && docker compose --env-file .env \
      -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml \
      --profile ops down --volumes --remove-orphans >/dev/null 2>&1) || true
  fi
  rm -rf -- "$TMP"
  echo "Disposable scanned-full cold install cleanup: status=$result"
  exit "$result"
}
trap cleanup EXIT

echo '[FULL-COLD 1/6] Verify exact scanned and disposable-signed archive.'
bash scripts/offline-release-verify.sh "$SIGNED" "$PUBLIC" >/dev/null
python - "$IMAGES" "$TMP/roles.txt" <<'PY'
import json,sys
from pathlib import Path
rows=json.loads(Path(sys.argv[1]).read_text())['images']
assert {x['role'] for x in rows} == {'backend','frontend','postgres','redis','objectstore','ollama','gateway'}
assert len({x['reference'] for x in rows}) == len(rows)
Path(sys.argv[2]).write_text('\n'.join(x['reference'] for x in rows)+'\n')
PY

echo '[FULL-COLD 2/6] Drop all seven image tags plus scan-only tags; assert absent.'
cp "$TMP/roles.txt" "$TMP/all-tags.txt"
printf '%s\n' 'grc-backend:ci' 'grc-frontend:ci' >> "$TMP/all-tags.txt"
while IFS= read -r ref; do
  if docker image inspect "$ref" >/dev/null 2>&1; then
    docker image rm "$ref" >/dev/null
  fi
done < "$TMP/all-tags.txt"
while IFS= read -r ref; do
  if docker image inspect "$ref" >/dev/null 2>&1; then
    echo "ERROR: cold import source image tag still exists: $ref" >&2; exit 4
  fi
done < "$TMP/all-tags.txt"

echo '[FULL-COLD 3/6] Create disposable TLS and independently generated config.'
mkdir -m 700 "$TMP/tls"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -sha256 \
  -subj "/CN=$HOSTNAME_CI" -addext "subjectAltName=DNS:$HOSTNAME_CI" \
  -keyout "$TMP/tls/server.key" -out "$TMP/tls/server.crt" >/dev/null 2>&1
chmod 600 "$TMP/tls/server.key"
VERSION="$(python - "$IMAGES" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))['images']
print(next(x['reference'].rsplit(':',1)[1] for x in data if x['role']=='backend'))
PY
)"
python scripts/server-pilot-env.py --hostname "$HOSTNAME_CI" \
  --release-version "$VERSION" --tls-cert "$TMP/tls/server.crt" \
  --tls-key "$TMP/tls/server.key" --output "$TMP/production.env" >/dev/null
python scripts/datacenter-env-validate.py --env "$TMP/production.env" \
  --release-version "$VERSION" --require-tls-files >/dev/null
getent hosts "$HOSTNAME_CI" >/dev/null ||
  printf '127.0.0.1 %s\n' "$HOSTNAME_CI" | sudo tee -a /etc/hosts >/dev/null

echo '[FULL-COLD 4/6] Load all seven signed scanned images with canonical offline installer.'
OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
  "$SIGNED" "$PUBLIC" "$INSTALL" "$TMP/production.env" > "$TMP/apply.log"
[[ "$(git -C "$INSTALL/repository" rev-parse HEAD)" == "$SHA" ]]
python - "$IMAGES" <<'PY'
import json,subprocess,sys
for item in json.load(open(sys.argv[1]))['images']:
    actual=subprocess.check_output(
        ['docker','image','inspect','--format','{{.Id}}',item['reference']],text=True
    ).strip()
    assert actual==item['image_id'], 'loaded Docker ID mismatch for '+item['role']
print('Signed image ID check passed for ALL SEVEN cold-loaded images.')
PY

echo '[FULL-COLD 5/6] Start and verify all eight TLS-protected core services.'
(
  cd "$INSTALL/repository"
  export DATACENTER_LOCAL_AI=NO
  CONFIRM_INSTALL=YES bash scripts/datacenterctl install > "$TMP/install-report.json"
)
python - "$TMP/install-report.json" <<'PY'
import json,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
i=s.find('{')
assert i>=0, 'missing datacenterctl structured report'
r=json.loads(s[i:])
assert r.get('ok') is True
assert r.get('config',{}).get('valid') is True
assert len(r.get('services',[])) >= 8
assert all(s['running'] for s in r['services'])
assert not r.get('missing_images')
print('Eight actual installed services verified with synthetic TLS.')
PY

echo '[FULL-COLD 6/6] Bootstrap synthetic tenant and exercise installed golden GRC.'
(
  cd "$INSTALL/repository"
  password="$(openssl rand -hex 24)"
  printf '%s\n%s\n' "$password" "$password" |
    bash scripts/datacenterctl bootstrap \
      --tenant-code "ci-full-${GITHUB_RUN_ID}" \
      --tenant-name "Disposable Scanned Full GRC" \
      --admin-username "ci-full-admin" \
      --admin-email "ci-full-admin@example.invalid" >/dev/null
  unset password
  docker compose --env-file .env \
    -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml \
    exec -T -e SECURE_SSL_REDIRECT=0 backend \
    python manage.py test apps.common.tests.GoldenPilotScenarioTests \
      --noinput --verbosity 1
  bash scripts/datacenterctl verify >/dev/null
)
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Cold install of scanned seven-image signed candidate: PASS (disposable CI only)'
    echo '- ALL SEVEN image tags removed before offline loader; every imported Docker ID matched signed metadata.'
    echo '- Eight core services verified under one-run TLS; synthetic tenant bootstrap and installed golden GRC test passed.'
    echo '- Not a production key, customer host, real-world UAT, content rights, independent pentest or RPO/RTO attestation.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
echo 'FULL-COLD scanned seven-image signed install PASS (CI-only); cleanup follows.'
