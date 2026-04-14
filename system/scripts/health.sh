#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

WARN_COUNT=0
FAIL_COUNT_H=0

_section() { echo ""; echo "── $* ──────────────────────────────────────────────────"; }
_pass()  { printf "  PASS  %s\n" "$*"; }
_warn()  { printf "  WARN  %s\n" "$*"; WARN_COUNT=$((WARN_COUNT+1)); }
_fail()  { printf "  FAIL  %s\n" "$*"; FAIL_COUNT_H=$((FAIL_COUNT_H+1)); }

echo "blctl health"
echo "project: ${PROJECT_ROOT}"
echo "time:    $(timestamp)"

# ── pytest baseline ────────────────────────────────────────────────────────────
_section "Test Baseline"
if command -v pytest &>/dev/null; then
  RESULT=$(cd "${PROJECT_ROOT}" && python -m pytest tests/ -q --tb=no 2>/dev/null | tail -2 || true)
  PASS_T=$(cd "${PROJECT_ROOT}" && python -m pytest tests/ -q --tb=no 2>/dev/null | grep -oE '^[0-9]+ passed' | grep -oE '^[0-9]+' || echo "0")
  FAIL_T=$(cd "${PROJECT_ROOT}" && python -m pytest tests/ -q --tb=no 2>/dev/null | grep -oE '[0-9]+ failed' | grep -oE '^[0-9]+' || echo "0")
  if [[ "${FAIL_T}" -eq 0 ]]; then
    _pass "${PASS_T} passing / 0 failing"
  else
    _fail "${FAIL_T} failing (${PASS_T} passing)"
  fi
else
  _warn "pytest not installed — skipping test baseline check"
fi

# ── Gate E: untracked TODOs ────────────────────────────────────────────────────
_section "Gate E — Untracked TODOs"
TODOS=$(git -C "${PROJECT_ROOT}" diff HEAD 2>/dev/null | grep -E '^\+.*\b(TODO|FIXME|HACK|XXX|PLACEHOLDER)\b' | grep -v '^+++' || true)
if [[ -z "${TODOS}" ]]; then
  _pass "No new untracked TODOs in uncommitted changes"
else
  _warn "Untracked TODOs found in uncommitted changes:"
  echo "${TODOS}" | sed 's/^/    /'
fi

# Full scan of production paths
PROD_TODOS=$(grep -rn --include="*.py" \
  -E '\b(TODO|FIXME|HACK|XXX|PLACEHOLDER)\b' \
  "${PROJECT_ROOT}/bitledger" 2>/dev/null \
  | grep -v "TASK-" | wc -l | tr -d ' ')
if [[ "${PROD_TODOS}" -gt 0 ]]; then
  _warn "${PROD_TODOS} TODO/FIXME markers in production paths (run: blctl todo-scan)"
else
  _pass "No untracked TODO markers in production paths"
fi

# ── Artifact hygiene ───────────────────────────────────────────────────────────
_section "Artifact Hygiene"
DS=$(git -C "${PROJECT_ROOT}" ls-files '*.DS_Store' 2>/dev/null | wc -l | tr -d ' ')
SQ=$(git -C "${PROJECT_ROOT}" ls-files '*.sqlite3' 2>/dev/null | wc -l | tr -d ' ')
[[ "${DS}" -eq 0 ]] && _pass "No .DS_Store tracked" || _fail "${DS} .DS_Store file(s) tracked in git"
[[ "${SQ}" -eq 0 ]] && _pass "No .sqlite3 tracked" || _fail "${SQ} .sqlite3 file(s) tracked in git"

# ── CLAUDE.md present ──────────────────────────────────────────────────────────
_section "Key Docs"
[[ -f "${PROJECT_ROOT}/CLAUDE.md" ]] && _pass "CLAUDE.md present" || _warn "CLAUDE.md missing from project root"
[[ -f "${PROJECT_ROOT}/system/TASKS.md" ]] && _pass "TASKS.md present" || _warn "system/TASKS.md missing"

# ── Active worktrees ───────────────────────────────────────────────────────────
_section "Active Worktrees"
TREES=$(git -C "${PROJECT_ROOT}" worktree list 2>/dev/null | grep "agent/" || true)
if [[ -z "${TREES}" ]]; then
  _pass "No active agent worktrees"
else
  NOW=$(date +%s)
  while IFS= read -r line; do
    path=$(echo "${line}" | awk '{print $1}')
    branch=$(echo "${line}" | grep -o '\[.*\]' | tr -d '[]')
    # Age from directory mtime
    if [[ -d "${path}" ]]; then
      mtime=$(stat -f "%m" "${path}" 2>/dev/null || stat -c "%Y" "${path}" 2>/dev/null || echo "${NOW}")
      age=$(( (NOW - mtime) / 86400 ))
      dirty=$(git -C "${path}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
      dirty_flag=""
      [[ "${dirty}" -gt 0 ]] && dirty_flag=" [${dirty} uncommitted]"
      if [[ "${age}" -gt 7 ]]; then
        _warn "${branch} — ${age}d old${dirty_flag}"
      else
        _pass "${branch} — ${age}d old${dirty_flag}"
      fi
    fi
  done <<< "${TREES}"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────────────────────"
echo "  warnings: ${WARN_COUNT}  failures: ${FAIL_COUNT_H}"
if [[ "${FAIL_COUNT_H}" -gt 0 ]]; then
  echo "  Status: UNHEALTHY — resolve failures"
  exit 1
elif [[ "${WARN_COUNT}" -gt 0 ]]; then
  echo "  Status: WARNINGS — review before proceeding"
else
  echo "  Status: HEALTHY"
fi
