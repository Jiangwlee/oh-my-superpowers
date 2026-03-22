#!/usr/bin/env bash
set -euo pipefail

# Project-level installer for packages, apps, and skills.
# Supported installation modes:
# - Python packages/apps via editable pip install into the repo virtualenv.
# - Skills via copy into project-level or global .agents/skills.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
PROJECT_SKILLS_DIR="${ROOT_DIR}/.agents/skills"
GLOBAL_SKILLS_DIR="${HOME}/.agents/skills"

PACKAGE_ITEMS=(
  "ashare-data:packages/ashare-data"
  "task-runner:packages/task-runner"
)

APP_ITEMS=(
  "ashare-platform:apps/ashare-platform/backend"
)

SKILL_ITEMS=(
  "agent-roundtable:skills/agent-roundtable"
  "ashare-assistant:skills/ashare-assistant"
  "bb-browser:skills/bb-browser"
  "code-insight:skills/code-insight"
  "explore-project:skills/explore-project"
  "github-researcher:skills/github-researcher"
  "markdown-to-anything:skills/markdown-to-anything"
  "openclaw-browser:skills/openclaw-browser"
  "openclaw-github-tracker:skills/openclaw-github-tracker"
  "skill-review:skills/skill-review"
  "unified-memory:skills/unified-memory"
  "website-operator:skills/website-operator"
)

LIST_ONLY=0
SKILL_DEST_MODE="project"
INSTALL_PACKAGES=()
INSTALL_APPS=()
INSTALL_SKILLS=()
ARG_COUNT=$#

usage() {
  cat <<'EOF'
Usage:
  bash install.sh [options]

Options:
  --list                  Show installable packages, apps, and skills.
  --package NAMES         Install comma-separated packages.
  --app NAMES             Install comma-separated apps.
  --skill NAMES           Install comma-separated skills.
  --all-packages          Install all packages.
  --all-apps              Install all apps.
  --all-skills            Install all skills.
  --project-skills        Install skills to ./.agents/skills (default).
  --global-skills         Install skills to ~/.agents/skills.
  -h, --help              Show this help.

Examples:
  bash install.sh --list
  bash install.sh --package ashare-data --app ashare-platform
  bash install.sh --skill ashare-assistant,unified-memory
  bash install.sh --all-skills --global-skills
  bash install.sh         # interactive mode
EOF
}

log() {
  printf '[install] %s\n' "$1"
}

fail() {
  printf '[install][error] %s\n' "$1" >&2
  exit 1
}

require_python_venv() {
  if [[ ! -x "${VENV_PYTHON}" ]]; then
    fail "missing project virtualenv python: ${VENV_PYTHON}"
  fi
}

item_path() {
  local target_name="$1"
  shift
  local item
  for item in "$@"; do
    local name="${item%%:*}"
    local rel_path="${item#*:}"
    if [[ "${name}" == "${target_name}" ]]; then
      printf '%s\n' "${rel_path}"
      return 0
    fi
  done
  return 1
}

parse_csv() {
  local raw="$1"
  local -n out_ref="$2"
  IFS=',' read -r -a out_ref <<<"${raw}"
}

print_group() {
  local title="$1"
  shift
  printf '%s\n' "${title}"
  local item
  for item in "$@"; do
    printf '  - %s\n' "${item%%:*}"
  done
}

collect_names() {
  local source_name="$1"
  local target_name="$2"
  local -n source_ref="${source_name}"
  local -n target_ref="${target_name}"
  target_ref=()
  local item
  for item in "${source_ref[@]}"; do
    target_ref+=("${item%%:*}")
  done
}

prompt_csv_selection() {
  local label="$1"
  local source_name="$2"
  local target_name="$3"
  local -n source_ref="${source_name}"
  local -n target_ref="${target_name}"
  local available=()
  collect_names "${source_name}" available

  printf '\n%s\n' "${label}"
  printf '  options: %s\n' "$(IFS=', '; printf '%s' "${available[*]}")"
  printf '  enter: all | none | comma-separated names\n'

  local raw
  read -r -p "> " raw
  raw="${raw// /}"
  if [[ -z "${raw}" || "${raw}" == "none" ]]; then
    target_ref=()
    return
  fi
  if [[ "${raw}" == "all" ]]; then
    collect_names "${source_name}" "${target_name}"
    return
  fi
  parse_csv "${raw}" target_ref
}

run_interactive_mode() {
  [[ -t 0 ]] || fail "interactive mode requires a TTY; use flags like --skill/--app/--package instead"

  printf 'OpenclawSkills installer\n'
  printf 'Press Enter for none, or type all / comma-separated names.\n'

  prompt_csv_selection "Select packages to install:" PACKAGE_ITEMS INSTALL_PACKAGES
  prompt_csv_selection "Select apps to install:" APP_ITEMS INSTALL_APPS
  prompt_csv_selection "Select skills to install:" SKILL_ITEMS INSTALL_SKILLS

  if (( ${#INSTALL_SKILLS[@]} > 0 )); then
    local skill_dest
    printf '\nInstall selected skills to which target?\n'
    printf '  1) project (%s)\n' "${PROJECT_SKILLS_DIR}"
    printf '  2) global  (%s)\n' "${GLOBAL_SKILLS_DIR}"
    read -r -p "> " skill_dest
    if [[ "${skill_dest}" == "2" ]]; then
      SKILL_DEST_MODE="global"
    else
      SKILL_DEST_MODE="project"
    fi
  fi
}

install_python_target() {
  local name="$1"
  local rel_path="$2"
  local abs_path="${ROOT_DIR}/${rel_path}"
  [[ -f "${abs_path}/pyproject.toml" ]] || fail "missing pyproject.toml for ${name}: ${abs_path}"
  log "installing ${name} from ${rel_path}"
  "${VENV_PYTHON}" -m pip install -e "${abs_path}"
}

install_skill_target() {
  local name="$1"
  local rel_path="$2"
  local source_dir="${ROOT_DIR}/${rel_path}"
  local dest_root
  if [[ "${SKILL_DEST_MODE}" == "global" ]]; then
    dest_root="${GLOBAL_SKILLS_DIR}"
  else
    dest_root="${PROJECT_SKILLS_DIR}"
  fi
  local dest_dir="${dest_root}/${name}"
  [[ -f "${source_dir}/SKILL.md" ]] || fail "missing SKILL.md for ${name}: ${source_dir}"
  mkdir -p "${dest_root}"
  rm -rf "${dest_dir}"
  cp -r "${source_dir}" "${dest_dir}"
  log "installed skill ${name} -> ${dest_dir}"
}

install_named_group() {
  local kind="$1"
  shift
  local -n requested_ref="$1"
  shift
  local items=("$@")
  local name
  for name in "${requested_ref[@]}"; do
    [[ -n "${name}" ]] || continue
    local rel_path
    rel_path="$(item_path "${name}" "${items[@]}")" || fail "unknown ${kind}: ${name}"
    if [[ "${kind}" == "skill" ]]; then
      install_skill_target "${name}" "${rel_path}"
    else
      install_python_target "${name}" "${rel_path}"
    fi
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      LIST_ONLY=1
      shift
      ;;
    --package)
      [[ $# -ge 2 ]] || fail "--package requires a comma-separated value"
      parse_csv "$2" INSTALL_PACKAGES
      shift 2
      ;;
    --app)
      [[ $# -ge 2 ]] || fail "--app requires a comma-separated value"
      parse_csv "$2" INSTALL_APPS
      shift 2
      ;;
    --skill)
      [[ $# -ge 2 ]] || fail "--skill requires a comma-separated value"
      parse_csv "$2" INSTALL_SKILLS
      shift 2
      ;;
    --all-packages)
      INSTALL_PACKAGES=()
      item=""
      for item in "${PACKAGE_ITEMS[@]}"; do
        INSTALL_PACKAGES+=("${item%%:*}")
      done
      shift
      ;;
    --all-apps)
      INSTALL_APPS=()
      item=""
      for item in "${APP_ITEMS[@]}"; do
        INSTALL_APPS+=("${item%%:*}")
      done
      shift
      ;;
    --all-skills)
      INSTALL_SKILLS=()
      item=""
      for item in "${SKILL_ITEMS[@]}"; do
        INSTALL_SKILLS+=("${item%%:*}")
      done
      shift
      ;;
    --project-skills)
      SKILL_DEST_MODE="project"
      shift
      ;;
    --global-skills)
      SKILL_DEST_MODE="global"
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

if (( ARG_COUNT == 0 )); then
  run_interactive_mode
fi

if (( LIST_ONLY == 1 )); then
  print_group "Packages:" "${PACKAGE_ITEMS[@]}"
  print_group "Apps:" "${APP_ITEMS[@]}"
  print_group "Skills:" "${SKILL_ITEMS[@]}"
  exit 0
fi

if (( ${#INSTALL_PACKAGES[@]} == 0 && ${#INSTALL_APPS[@]} == 0 && ${#INSTALL_SKILLS[@]} == 0 )); then
  if (( ARG_COUNT == 0 )); then
    log "nothing selected; exiting"
    exit 0
  fi
  usage
  exit 1
fi

if (( ${#INSTALL_PACKAGES[@]} > 0 || ${#INSTALL_APPS[@]} > 0 )); then
  require_python_venv
fi

if (( ${#INSTALL_PACKAGES[@]} > 0 )); then
  install_named_group "package" INSTALL_PACKAGES "${PACKAGE_ITEMS[@]}"
fi

if (( ${#INSTALL_APPS[@]} > 0 )); then
  install_named_group "app" INSTALL_APPS "${APP_ITEMS[@]}"
fi

if (( ${#INSTALL_SKILLS[@]} > 0 )); then
  install_named_group "skill" INSTALL_SKILLS "${SKILL_ITEMS[@]}"
fi

log "all requested installs completed"
