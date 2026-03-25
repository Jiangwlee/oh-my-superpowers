#!/usr/bin/env bash
# install.sh — Bootstrap oh-my-superpowers
#
# Two invocation modes (auto-detected, no flags needed):
#
#   Local  (dev symlink):  ./install.sh
#     - Creates ~/.oh-my-superpowers -> <this repo>
#     - Registers all bin/ executables to ~/.local/bin/
#
#   Remote (first install): curl -fsSL https://raw.githubusercontent.com/Jiangwlee/oh-my-superpowers/main/install.sh | bash
#     - Clones the repo to ~/.oh-my-superpowers/
#     - Registers all bin/ executables to ~/.local/bin/

set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────

GITHUB_REPO="Jiangwlee/oh-my-superpowers"
INSTALL_DIR="${HOME}/.oh-my-superpowers"
BIN_DIR="${HOME}/.local/bin"

# ── Coloured output ───────────────────────────────────────────────────────────

info()    { printf '\033[34m[INFO]\033[0m %s\n' "$1"; }
success() { printf '\033[32m[OK]\033[0m %s\n' "$1"; }
warn()    { printf '\033[33m[WARN]\033[0m %s\n' "$1"; }
fail()    { printf '\033[31m[ERROR]\033[0m %s\n' "$1" >&2; exit 1; }

# ── Mode detection ─────────────────────────────────────────────────────────────

detect_mode() {
  if [[ "${BASH_SOURCE[0]:-/dev/stdin}" == "/dev/stdin" || -z "${BASH_SOURCE[0]:-}" ]]; then
    echo "remote"
  else
    echo "local"
  fi
}

# ── Dependency check ──────────────────────────────────────────────────────────

check_deps() {
  local mode="$1"

  if [[ "${mode}" == "remote" ]]; then
    if ! command -v git &>/dev/null; then
      fail "git is required but not found. Install it first:\n  sudo apt install git  (Debian/Ubuntu)\n  brew install git      (macOS)"
    fi
  fi

  if ! command -v uv &>/dev/null; then
    fail "uv is required but not found. Install it first:\n  curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi
}

# ── Local install (symlink mode) ──────────────────────────────────────────────

install_local() {
  info "Mode: local (dev symlink)"

  local root_dir
  root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if [[ -L "${INSTALL_DIR}" ]]; then
    rm "${INSTALL_DIR}"
  elif [[ -e "${INSTALL_DIR}" ]]; then
    fail "${INSTALL_DIR} exists and is not a symlink. Remove it manually before running this script."
  fi

  ln -s "${root_dir}" "${INSTALL_DIR}"
  success "linked ${INSTALL_DIR} -> ${root_dir}"
}

# ── Remote install (clone mode) ───────────────────────────────────────────────

install_remote() {
  info "Mode: remote (clone from GitHub)"

  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    info "Repository found. Updating..."
    git -C "${INSTALL_DIR}" pull origin main
  else
    rm -rf "${INSTALL_DIR}"
    git clone "https://github.com/${GITHUB_REPO}.git" "${INSTALL_DIR}"
  fi

  success "code ready at ${INSTALL_DIR}"
}

# ── Register bin/ executables ─────────────────────────────────────────────────

register_bins() {
  mkdir -p "${BIN_DIR}"
  local count=0
  while IFS= read -r -d '' script; do
    local name
    name="$(basename "${script}")"
    ln -sf "${script}" "${BIN_DIR}/${name}"
    info "linked ${BIN_DIR}/${name} -> ${script}"
    (( count++ )) || true
  done < <(find "${INSTALL_DIR}/bin" -maxdepth 1 -type f -executable -print0 2>/dev/null)
  if [[ "${count}" -eq 0 ]]; then
    warn "No executable files found in bin/."
  else
    success "Registered ${count} command(s) to ${BIN_DIR}"
  fi
}

# ── PATH check ────────────────────────────────────────────────────────────────

check_path() {
  if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    warn "${BIN_DIR} is not in PATH."
    info "Add to your shell profile (~/.bashrc or ~/.zshrc):"
    info "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
}

# ── Entry point ───────────────────────────────────────────────────────────────

main() {
  echo ""
  echo "=================================================="
  echo "  oh-my-superpowers Bootstrap"
  echo "=================================================="
  echo ""

  local mode
  mode=$(detect_mode)
  check_deps "${mode}"

  if [[ "${mode}" == "remote" ]]; then
    install_remote
  else
    install_local
  fi

  register_bins
  check_path

  echo ""
  success "Bootstrap complete."
  info "Next: use \`omp install skill <name>\` to install individual skills."
}

main "$@"
