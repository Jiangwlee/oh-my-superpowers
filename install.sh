#!/usr/bin/env bash
# install.sh — Bootstrap oh-my-superpowers
#
# Installs the project to ~/.oh-my-superpowers/ (symlink) and registers
# the omp CLI to ~/.local/bin/omp.
#
# Run once after cloning. Re-run to update the symlink after moving the repo.
# After bootstrap, use `omp` to install individual skills and agents.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.oh-my-superpowers"
BIN_DIR="${HOME}/.local/bin"
OMP_LINK="${BIN_DIR}/omp"
OMP_BIN="${INSTALL_DIR}/bin/omp"

log()  { printf '[install] %s\n' "$1"; }
warn() { printf '[install] WARNING: %s\n' "$1"; }
fail() { printf '[install] ERROR: %s\n' "$1" >&2; exit 1; }

# ── 1. Install to ~/.oh-my-superpowers ────────────────────────────────────────

if [[ -L "${INSTALL_DIR}" ]]; then
  rm "${INSTALL_DIR}"
elif [[ -e "${INSTALL_DIR}" ]]; then
  fail "${INSTALL_DIR} exists and is not a symlink. Remove it manually before running this script."
fi

ln -s "${ROOT_DIR}" "${INSTALL_DIR}"
log "linked ${INSTALL_DIR} -> ${ROOT_DIR}"

# ── 2. Register all bin/ commands to PATH ────────────────────────────────────

mkdir -p "${BIN_DIR}"

count=0
while IFS= read -r -d '' script; do
  name="$(basename "${script}")"
  ln -sf "${script}" "${BIN_DIR}/${name}"
  log "linked ${BIN_DIR}/${name} -> ${script}"
  (( count++ )) || true
done < <(find "${INSTALL_DIR}/bin" -maxdepth 1 -type f -executable -print0 2>/dev/null)

if [[ "${count}" -eq 0 ]]; then
  warn "No executable files found in bin/. Re-run this script after adding commands."
fi

# ── 3. PATH check ─────────────────────────────────────────────────────────────

if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  warn "${BIN_DIR} is not in PATH."
  log  "Add the following to your shell profile (~/.bashrc or ~/.zshrc):"
  log  "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

log "Bootstrap complete."
log "Next: use \`omp install skill <name>\` to install individual skills."
