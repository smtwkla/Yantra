#!/bin/bash
# SessionStart hook for Claude Code cloud sessions only (no-op on dev machines).
# Brings up what the tests need: Docker, the yantra-dev MariaDB (3307) with the
# test/e2e grants, the uv and npm dependencies, and the Playwright browsers that
# match frontend/package.json. Idempotent: every step is a no-op when already done.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Hook stdout goes into the session's context: keep the detail in a log, print a summary.
LOG=/tmp/session-start.log
exec 3>&1 >"$LOG" 2>&1
trap 'echo "Session setup FAILED; see $LOG" >&3' ERR
BROWSERS="Playwright browsers installed"

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COMPOSE=(docker compose -f "$ROOT/tooling/dev/docker-compose.dev.yml")
ROOT_PW=dev-root-password   # dev-only password from the compose file

wait_for() {  # wait_for <seconds> <command...>
  local limit=$1; shift
  for _ in $(seq 1 "$limit"); do
    "$@" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

# 1. Docker daemon
if ! docker info >/dev/null 2>&1; then
  echo "Starting dockerd"
  nohup dockerd >/tmp/dockerd.log 2>&1 &
  wait_for 30 docker info || { echo "dockerd did not start; see /tmp/dockerd.log"; exit 1; }
fi

# 2. Dev DB container, then the grants the test runners make (same SQL as the .bat scripts)
"${COMPOSE[@]}" up -d
wait_for 60 "${COMPOSE[@]}" exec -T mariadb mariadb -uroot -p"$ROOT_PW" -e "SELECT 1" \
  || { echo "MariaDB did not become ready"; exit 1; }
"${COMPOSE[@]}" exec -T mariadb mariadb -uroot -p"$ROOT_PW" -e "
  GRANT ALL PRIVILEGES ON \`vel\\_yantra\\_test\\_%\`.* TO 'vel_yantra_master'@'%';
  GRANT ALL PRIVILEGES ON \`vel\\_yantra\\_upgrade\\_%\`.* TO 'vel_yantra_master'@'%';
  CREATE DATABASE IF NOT EXISTS vel_yantra_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  GRANT ALL PRIVILEGES ON vel_yantra_e2e.* TO 'vel_yantra_master'@'%';
  FLUSH PRIVILEGES;"

# 3. Python dependencies (root: tooling; backend: the app)
(cd "$ROOT" && uv sync)
(cd "$ROOT/backend" && uv sync)

# 4. Frontend dependencies; npm 10.9 crashes on vitest's optional peers (CLAUDE.md), so npm 11
(cd "$ROOT/frontend" && npx --yes npm@11 install --no-audit --no-fund)

# 5. Browsers for the pinned @playwright/test (the image's preinstalled build is older), plus WebKit's system libraries
# Not fatal: the browser CDN (cdn.playwright.dev) must be in the environment's allowed domains;
# without it everything else still works and only the e2e suite cannot run.
if ! (cd "$ROOT/frontend" && npx playwright install --with-deps chromium webkit); then
  BROWSERS="WARNING: Playwright browsers NOT installed (cdn.playwright.dev is not in the environment's allowed domains), so the e2e suite cannot run"
fi

echo "Session setup done: dev DB yantra-dev on 127.0.0.1:3307, uv and npm dependencies installed. $BROWSERS. Log: $LOG" >&3
