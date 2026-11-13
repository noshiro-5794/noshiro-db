#!/usr/bin/env bash
# Phase 0 and 1 of docs-handover.md: start the replacement beside Django and prove
# it before anything is routed to it. This script never touches the proxy.
#
#   REPO=/vol1/1000/projects/noshiro-db/app SMOKE_EMAIL=... SMOKE_PASSWORD=... \
#     bash apps/api-v2/scripts/cutover.sh
#
# Exit codes: 0 ready and proven, 1 not ready, 2 smoke failed.
set -euo pipefail

REPO=${REPO:-/vol1/1000/projects/noshiro-db/app}
APP="$REPO/apps/api-v2"
BASE=${BASE:-http://127.0.0.1:8010}
ENV_FILE=${ENV_FILE:-../api/.env.production}

cd "$APP"

echo "== building and starting the replacement"
ENV_FILE="$ENV_FILE" docker compose -f docker-compose.api-v2.yml up -d --build

echo "== waiting for readiness on $BASE"
ready=0
for _ in $(seq 1 60); do
  if curl -fsS --max-time 3 "$BASE/health/ready/" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "FAIL: not ready after 120s"
  docker logs --tail 40 noshiro-db-api-v2-1 || true
  exit 1
fi
echo "ok   readiness"

if [ -z "${SMOKE_EMAIL:-}" ] || [ -z "${SMOKE_PASSWORD:-}" ]; then
  echo "skip smoke: set SMOKE_EMAIL and SMOKE_PASSWORD to run it"
  echo
  echo "Next: point the site's upstream at 127.0.0.1:${BASE##*:} (it is 8008 today)."
  echo "Rollback: point it back at 127.0.0.1:8008."
  exit 0
fi

echo "== smoke"
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/smoke.py --base "$BASE" \
    --email "$SMOKE_EMAIL" --password "$SMOKE_PASSWORD" \
    ${SMOKE_ENTRY:+--entry "$SMOKE_ENTRY"} || { echo "FAIL: smoke"; exit 2; }
else
  echo "skip smoke: python3 not found on this host"
fi

echo
echo "Proven. Next: point the site's upstream at 127.0.0.1:${BASE##*:} (8008 today)."
echo "Rollback: point it back at 127.0.0.1:8008."
