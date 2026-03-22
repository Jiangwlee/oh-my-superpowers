#!/usr/bin/env bash
set -euo pipefail

# Install and start the ashare-platform Docker deployment.
# Responsibilities:
# 1. Validate local Docker prerequisites.
# 2. Prepare deployment-local runtime files.
# 3. Start or rebuild the Compose service.
# 4. Optionally initialize retained data inside the container.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE_FILE="${SCRIPT_DIR}/.env.example"
DATA_DIR="${SCRIPT_DIR}/data"
HEALTH_URL="http://127.0.0.1:8000/health"

WITH_INIT_DATA=0
INIT_DAYS=30
BUILD_IMAGE=1

usage() {
  cat <<'EOF'
Usage:
  bash deployment/docker/ashare-platform/install.sh [options]

Options:
  --with-init-data       Run `ashare-platform init-data` after the container is healthy.
  --init-days N          Number of trade days for init-data. Default: 30.
  --no-build             Skip `--build` during `docker compose up`.
  -h, --help             Show this help.

Behavior:
  - Preserves an existing .env file.
  - Creates .env from .env.example if missing.
  - Creates the deployment data directory if missing.
  - Verifies /health before exiting successfully.
EOF
}

log() {
  printf '[install] %s\n' "$1"
}

fail() {
  printf '[install][error] %s\n' "$1" >&2
  exit 1
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    fail "missing required command: ${cmd}"
  fi
}

wait_for_health() {
  local attempt=1
  local max_attempts=30
  while (( attempt <= max_attempts )); do
    if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
  return 1
}

ensure_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    log "using existing ${ENV_FILE}"
    return
  fi
  if [[ ! -f "${ENV_EXAMPLE_FILE}" ]]; then
    fail "missing ${ENV_EXAMPLE_FILE}"
  fi
  cp "${ENV_EXAMPLE_FILE}" "${ENV_FILE}"
  log "created ${ENV_FILE} from example"
}

run_init_data() {
  log "running init-data for the last ${INIT_DAYS} trade days"
  docker compose -f "${COMPOSE_FILE}" exec -T ashare-platform \
    ashare-platform init-data --days "${INIT_DAYS}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-init-data)
      WITH_INIT_DATA=1
      shift
      ;;
    --init-days)
      [[ $# -ge 2 ]] || fail "--init-days requires a value"
      INIT_DAYS="$2"
      shift 2
      ;;
    --no-build)
      BUILD_IMAGE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

if ! [[ "${INIT_DAYS}" =~ ^[0-9]+$ ]] || (( INIT_DAYS <= 0 )); then
  fail "--init-days must be a positive integer"
fi

require_command docker
require_command curl

if ! docker info >/dev/null 2>&1; then
  fail "docker daemon is not available"
fi

mkdir -p "${DATA_DIR}"
ensure_env_file

log "starting ashare-platform via Docker Compose"
if (( BUILD_IMAGE == 1 )); then
  docker compose -f "${COMPOSE_FILE}" up -d --build
else
  docker compose -f "${COMPOSE_FILE}" up -d
fi

log "waiting for ${HEALTH_URL}"
if ! wait_for_health; then
  fail "service did not become healthy in time"
fi

if (( WITH_INIT_DATA == 1 )); then
  run_init_data
fi

log "installation finished successfully"
log "health endpoint: ${HEALTH_URL}"
