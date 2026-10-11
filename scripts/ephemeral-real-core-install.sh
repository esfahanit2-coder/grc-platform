#!/usr/bin/env bash
# Real-core-image signed installer + full TLS stack smoke on a disposable CI runner.
# The optional Ollama role is an explicit synthetic placeholder (AI disabled).
# NOT a licensed production release, disconnected-network test, or customer acceptance.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GRC_CORE_INSTALL_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo 'ERROR: only an explicitly opted-in disposable GitHub Actions runner is permitted.' >&2
  exit 2
fi
for command in git docker python openssl tar gzip sha256sum sudo; do
  command -v "$command" >/dev/null || { echo "ERROR: missing prerequisite $command" >&2; exit 2; }
done
docker info >/dev/null
VERSION="v-ci-core-${GITHUB_RUN_ID:-unset}-${GITHUB_RUN_ATTEMPT:-1}"
[[ "$VERSION" != *unset* ]] || { echo 'ERROR: missing real GitHub run ID.' >&2; exit 2; }
SHA="$(git rev-parse HEAD)"
SOURCE_TREE="$(git rev-parse HEAD^{tree})"
TMP="$(mktemp -d)"
STAGE="$TMP/$VERSION"
SIGNED="$TMP/core-signed.tar.gz"
INSTALL="$TMP/installed"
REF="refs/grc-release/$VERSION"
PROJECT="grccore${GITHUB_RUN_ID}${GITHUB_RUN_ATTEMPT:-1}"
HOSTNAME_CI="grc.ci.internal"
export COMPOSE_PROJECT_NAME="$PROJECT"
export GRC_VERIFY_CA_CERT="$TMP/tls/server.crt"
export NO_PROXY="grc.ci.internal,localhost,127.0.0.1,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
declare -a TEST_TAGS=()
cleanup() {
  local result=$?
  trap - EXIT
  if [[ -s "$INSTALL/repository/.env" ]]; then
    (cd "$INSTALL/repository" && docker compose --env-file .env \
      -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml \
      --profile ops down --volumes --remove-orphans >/dev/null 2>&1) || true
  fi
  git update-ref -d "$REF" >/dev/null 2>&1 || true
  for tag in "${TEST_TAGS[@]}"; do docker image rm "$tag" >/dev/null 2>&1 || true; done
  rm -rf -- "$TMP"
  echo "Real-core signed installer cleanup: status=$result"
  exit "$result"
}
trap cleanup EXIT
test ! -e .env || { echo 'ERROR: refusing to use checkout containing production .env' >&2; exit 3; }
mkdir -p "$STAGE"/{images,metadata,source} "$TMP/tls" "$TMP/placeholder"
printf 'CI test-only optional Ollama placeholder, AI profile disabled\n' > "$TMP/placeholder/NOTICE"
tar -cf "$TMP/optional-ai-placeholder.tar" -C "$TMP/placeholder" .
echo '[1/8] Building real GRC backend and frontend images.'
docker build --pull -t "grc-backend:$VERSION" backend
docker build --pull -t "grc-frontend:$VERSION" frontend
TEST_TAGS+=("grc-backend:$VERSION" "grc-frontend:$VERSION")
echo '[2/8] Pulling pinned real dependencies (optional AI runtime is intentionally skipped).'
for image in pgvector/pgvector:0.8.6-pg18-trixie redis:8.2.1-alpine \
  chrislusf/seaweedfs:4.47 nginx:1.28.0-alpine; do
  docker pull "$image" >/dev/null
  TEST_TAGS+=("$image")
done
docker import "$TMP/optional-ai-placeholder.tar" "ollama/ollama:0.34.1" >/dev/null
TEST_TAGS+=("ollama/ollama:0.34.1")

echo '[3/8] Building signed candidate metadata from exact local image identities.'
ROWS="$STAGE/metadata/image-rows.jsonl"
: > "$ROWS"
export_image() {
  local role="$1" tag="$2"
  docker save -o "$STAGE/images/$role.tar" "$tag"
  local id digests
  id="$(docker image inspect --format '{{.Id}}' "$tag")"
  digests="$(docker image inspect --format '{{json .RepoDigests}}' "$tag")"
  python - "$ROWS" "$role" "$tag" "$id" "$digests" <<'PY'
import json, sys
from pathlib import Path
path, role, ref, ident, digests = sys.argv[1:]
row = {'role':role, 'reference':ref,'archive':f'images/{role}.tar',
       'image_id':ident,'repo_digests':json.loads(digests or 'null') or []}
with Path(path).open('a', encoding='utf-8') as target:
    target.write(json.dumps(row, sort_keys=True)+'\n')
PY
}
export_image backend "grc-backend:$VERSION"
export_image frontend "grc-frontend:$VERSION"
export_image postgres pgvector/pgvector:0.8.6-pg18-trixie
export_image redis redis:8.2.1-alpine
export_image objectstore chrislusf/seaweedfs:4.47
export_image ollama ollama/ollama:0.34.1
export_image gateway nginx:1.28.0-alpine
python - "$ROWS" "$STAGE/metadata/images.json" <<'PY'
import json,sys
from pathlib import Path
rows=[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
Path(sys.argv[2]).write_text(json.dumps({'schema':'grc-offline-images-v1',
 'images':rows},indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
rm -f "$ROWS"
python scripts/offline-release-manifest.py prepare-metadata --repo "$ROOT" --stage "$STAGE"
python - "$STAGE/metadata/security-evidence.json" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
 'schema':'grc-release-security-evidence-v1','reports':[],
 'test_only':True,'note':'This integration fixture is NOT a scanned release candidate'
},sort_keys=True)+'\n',encoding='utf-8')
PY
BACKEND_ID="$(docker image inspect --format '{{.Id}}' "grc-backend:$VERSION")"
FRONTEND_ID="$(docker image inspect --format '{{.Id}}' "grc-frontend:$VERSION")"
python scripts/release-evidence-provenance.py write --source-commit "$SHA" \
  --source-tree "$SOURCE_TREE" --backend-image-id "$BACKEND_ID" \
  --frontend-image-id "$FRONTEND_ID" \
  --out "$STAGE/metadata/release-evidence-provenance.json"
python scripts/server-pilot-candidate.py --release-version "$VERSION" \
  --source-commit "$SHA" --images "$STAGE/metadata/images.json" \
  --out "$STAGE/metadata/server-candidate.json" >/dev/null
git show-ref --verify --quiet "$REF" && { echo 'ERROR: release ref exists' >&2; exit 4; } || true
git update-ref "$REF" "$SHA"
git bundle create "$STAGE/source/grc-platform.bundle" "$REF"
git bundle verify "$STAGE/source/grc-platform.bundle" >/dev/null
python scripts/offline-release-manifest.py build --stage "$STAGE" \
  --version "$VERSION" --source-commit "$SHA"
python scripts/offline-release-manifest.py verify --stage "$STAGE" >/dev/null
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$TMP/test-private.pem" >/dev/null 2>&1
openssl pkey -in "$TMP/test-private.pem" -pubout \
  -out "$TMP/trusted-public.pem" >/dev/null 2>&1
bash scripts/offline-release-sign.sh "$STAGE" "$TMP/test-private.pem" "$SIGNED" >/dev/null
bash scripts/offline-release-verify.sh "$SIGNED" "$TMP/trusted-public.pem" >/dev/null

echo '[4/8] Removing original image tags to force image import from signed archives.'
for tag in "${TEST_TAGS[@]}"; do docker image rm "$tag" >/dev/null; done
for tag in "${TEST_TAGS[@]}"; do
  if docker image inspect "$tag" >/dev/null 2>&1; then
    echo "ERROR: source image tag still present before signed install: $tag" >&2
    exit 4
  fi
done

echo '[5/8] Preparing ephemeral host certificates and an independently generated config.'
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -sha256 \
  -subj "/CN=$HOSTNAME_CI" -addext "subjectAltName=DNS:$HOSTNAME_CI" \
  -keyout "$TMP/tls/server.key" -out "$TMP/tls/server.crt" >/dev/null 2>&1
chmod 600 "$TMP/tls/server.key"
python scripts/server-pilot-env.py --hostname "$HOSTNAME_CI" \
  --release-version "$VERSION" --tls-cert "$TMP/tls/server.crt" \
  --tls-key "$TMP/tls/server.key" --output "$TMP/production.env" >/dev/null
python scripts/datacenter-env-validate.py --env "$TMP/production.env" \
  --release-version "$VERSION" --require-tls-files >/dev/null
# Host modification is confined to this short-lived GitHub-hosted runner.
getent hosts "$HOSTNAME_CI" >/dev/null || \
  printf '127.0.0.1 %s\n' "$HOSTNAME_CI" | sudo tee -a /etc/hosts >/dev/null

echo '[6/8] Using the unmodified signed offline installer to restore core images.'
OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
  "$SIGNED" "$TMP/trusted-public.pem" "$INSTALL" "$TMP/production.env" >/dev/null
[[ "$(git -C "$INSTALL/repository" rev-parse HEAD)" == "$SHA" ]]
# A clean install must never let Docker first-create /backups as root.
[[ -d "$INSTALL/repository/backups" && ! -L "$INSTALL/repository/backups" ]]
[[ -w "$INSTALL/repository/backups" ]]
[[ "$(stat -c '%a' "$INSTALL/repository/backups")" == "700" ]] || {
  echo 'ERROR: signed installer did not provision operator-writable private backups directory.' >&2
  exit 4
}
for tag in "${TEST_TAGS[@]}"; do docker image inspect "$tag" >/dev/null; done
echo '[7/8] Starting exact preloaded core application through datacenterctl.'
(
  cd "$INSTALL/repository"
  export DATACENTER_LOCAL_AI=NO
  CONFIRM_INSTALL=YES bash scripts/datacenterctl install > "$TMP/install-report.json"
)
python - "$TMP/install-report.json" "$SHA" <<'PY'
import json,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(encoding='utf-8')
idx=text.find('{')
if idx<0:
    raise SystemExit('No structured verification result from datacenterctl install')
report=json.loads(text[idx:])
assert report.get('ok') is True, 'Datacenter verification returned not-ok'
assert report.get('config',{}).get('valid') is True, 'Production config did not validate'
assert len(report.get('services',[])) >= 8, 'Full core service set was not inspected'
for service in report['services']:
    assert service['running'], f"service not running: {service['service']}"
assert not report.get('missing_images'), 'Missing signed image'
print('Full signed core runtime checks PASSED (synthetic operator keys).')
PY

if [[ "${GRC_CORE_DR_EPHEMERAL_ONLY:-NO}" == "YES" ]]; then
  echo '[DR] Running real full-stack synthetic recovery on the installed signed commit.'
  bash "$INSTALL/repository/scripts/ephemeral-real-core-dr.sh" "$INSTALL/repository" "$SHA"
fi

if [[ "${GRC_CORE_REPLACEMENT_EPHEMERAL_ONLY:-NO}" == "YES" ]]; then
  echo '[REPL] Switching to a second signed install and clean Docker volumes.'
  bash "$INSTALL/repository/scripts/ephemeral-replacement-core-dr.sh" \
    "$INSTALL/repository" "$SIGNED" "$TMP/trusted-public.pem" \
    "$TMP/replacement" "$TMP/production.env" "$SHA"
fi
echo '[8/8] Recording CI-only evidence; cleaning synthetic environment.'
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Signed real-core runtime: PASS (ephemeral, non-production)'
    echo '- Actual Django, Next.js, PostgreSQL, Redis, SeaweedFS and Nginx images were signed and installed from local archives.'
    echo '- Normal datacenterctl install launched and verified the eight core services over runner-local TLS.'
    echo '- Ollama image is a deliberately synthetic placeholder; AI and model functionality were not exercised.'
    echo '- No real release security scan attestation, real network isolation, customer PKI/UAT, DR or RPO/RTO was established.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
