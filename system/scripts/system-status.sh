#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

echo "BitLedger Dev System — Status"
echo "  devsystem: ${CODEX_ROOT}"
echo "  project:   ${PROJECT_ROOT}"
echo "  time:      $(timestamp)"
echo ""

# ── Core Files ─────────────────────────────────────────────────────────────────
echo "Core Files"
for f in \
  "${CODEX_ROOT}/CLAUDE.md" \
  "${CODEX_ROOT}/fragility-register.md" \
  "${CODEX_ROOT}/config/gates.yaml" \
  "${CODEX_ROOT}/config/roles.yaml" \
  "${CODEX_ROOT}/config/test-baseline.yaml"; do
  if [[ -f "${f}" ]]; then
    printf "  OK      %s\n" "$(basename "${f}")"
  else
    printf "  MISSING %s\n" "${f}"
  fi
done

# ── Key Project Files ──────────────────────────────────────────────────────────
echo ""
echo "Key Project Files"
for f in \
  "${PROJECT_ROOT}/CLAUDE.md" \
  "${PROJECT_ROOT}/system/TASKS.md"; do
  if [[ -f "${f}" ]]; then
    printf "  OK   %s\n" "${f#${PROJECT_ROOT}/}"
  else
    printf "  --   %s\n" "${f#${PROJECT_ROOT}/}"
  fi
done

# ── Task Cards ─────────────────────────────────────────────────────────────────
echo ""
echo "Task Cards"
CARDS_DIR="${CODEX_ROOT}/tasks/cards"
ALL_CARDS="$(find "${CARDS_DIR}" -name "TASK-*.md" 2>/dev/null | sort)"
if [[ -z "${ALL_CARDS}" ]]; then
  echo "  (none)"
else
  while IFS= read -r card; do
    STATUS="$(grep "^Status:" "${card}" 2>/dev/null | awk '{print $2}' || echo "unknown")"
    GOAL="$(grep "^Goal:" "${card}" 2>/dev/null | sed 's/^Goal: *//' | cut -c1-60 || echo "")"
    printf "  %-12s %-12s %s\n" "$(basename "${card}" .md)" "[${STATUS}]" "${GOAL}"
  done <<< "${ALL_CARDS}"
fi

# ── Explorer Outputs ───────────────────────────────────────────────────────────
echo ""
echo "Audit Outputs"
AUDITS="$(find "${CODEX_ROOT}/audits" -name "*.md" 2>/dev/null | sort)"
OUTPUTS="$(find "${CODEX_ROOT}/outputs" -name "*.md" 2>/dev/null | sort)"
ALL_AUDIT_OUTPUTS="$(printf "%s\n%s\n" "${AUDITS}" "${OUTPUTS}" | sed '/^$/d' | sort -u)"
if [[ -z "${ALL_AUDIT_OUTPUTS}" ]]; then
  echo "  (none — Explorer A and B not yet run)"
else
  while IFS= read -r f; do
    printf "  %s\n" "$(basename "${f}")"
  done <<< "${ALL_AUDIT_OUTPUTS}"
fi

# ── Active Worktrees ───────────────────────────────────────────────────────────
echo ""
echo "Active Worktrees"
WORKTREES="$(git -C "${PROJECT_ROOT}" worktree list 2>/dev/null | grep "agent/" || true)"
if [[ -z "${WORKTREES}" ]]; then
  echo "  (none)"
else
  echo "${WORKTREES}" | sed 's/^/  /'
fi

# ── Phase 1 Quick Check ────────────────────────────────────────────────────────
echo ""
echo "Phase 1 Quick Check"
[[ -f "${PROJECT_ROOT}/CLAUDE.md" ]] && echo "  OK  Root CLAUDE.md present" || echo "  --  Root CLAUDE.md not yet created"
[[ -n "$(find "${CODEX_ROOT}/audits" "${CODEX_ROOT}/outputs" -name "*explorer-a*" 2>/dev/null)" ]] && echo "  OK  Explorer A complete" || echo "  --  Explorer A pending"
[[ -n "$(find "${CODEX_ROOT}/audits" "${CODEX_ROOT}/outputs" -name "*explorer-b*" 2>/dev/null)" ]] && echo "  OK  Explorer B complete" || echo "  --  Explorer B pending"
[[ -f "${PROJECT_ROOT}/system/TASKS.md" ]] && echo "  OK  TASKS.md present" || echo "  --  TASKS.md not yet created"
