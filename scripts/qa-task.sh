#!/usr/bin/env bash
# qa-task.sh — Durable log/status wrapper for concept2mqtt QA tasks.
#
# Usage:
#   bash scripts/qa-task.sh <task-name> [extra-args...]
#
# Built-in implementations exist for every named QA task.  Extra args are
# forwarded to tasks that accept them (test:file).  For unknown task names,
# extra args are treated as the command to execute directly.
#
# Environment overrides:
#   QA_LOG_DIR      directory for log/status files  (default: /tmp)
#   QA_TAIL_LINES   lines to tail on completion      (default: 160)
#   QA_TIMEOUT      overall deadline, e.g. "10m"     (default: per-task)
#   QA_NO_WRAP      if non-empty, run impl directly without log/status/timeout
#   PKG             package root relative to repo    (default: packages)
#   MODULE_NAME     Python module name               (default: concept2mqtt)
#
# Backward-compat env aliases honoured for pre-pr:
#   PRE_PR_LOG / PRE_PR_STATUS / PRE_PR_TAIL_LINES
#
# Top-level invocations get a durable log, a .status file, and an overall
# timeout.  Composite tasks (security:audit, complexity, check, etc.) call
# run_raw_task() which sets QA_NO_WRAP=1 — child processes skip the wrapper
# entirely, streaming directly into the parent log.  This prevents nested
# durable wrappers and the "stuck inside child wrapper" failure mode.

# Guard: if sourced instead of executed, re-run as a child process so that
# set -euo pipefail cannot pollute the caller's shell and a failing task
# cannot terminate it.  The exit status is still captured by the wrapper.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
    bash "${BASH_SOURCE[0]}" "$@"
    return $?
fi

set -euo pipefail

TASK_NAME="${1:?Usage: qa-task.sh <task-name> [extra-args...]}"
shift || true

_PKG="${PKG:-packages}"
_MOD="${MODULE_NAME:-concept2mqtt}"

# ---------------------------------------------------------------------------
# run_raw_task: invoke a sub-task's built-in implementation with QA_NO_WRAP=1
# so no nested log/status/timeout wrapper is created.  Used by composite arms.
# ---------------------------------------------------------------------------
run_raw_task() {
    QA_NO_WRAP=1 bash "${BASH_SOURCE[0]}" "$@"
}

# ---------------------------------------------------------------------------
# Per-task default timeouts — KEEP IN SYNC with the _run_impl arms below.
# When adding a new task, add both a case arm and a timeout entry here.
# ---------------------------------------------------------------------------
_task_timeout() {
    case "${TASK_NAME}" in
        pre-pr)                                              echo "60m" ;;
        test|test:unit|test:integration|test:cov)            echo "20m" ;;
        *)                                                   echo "10m" ;;
    esac
}

# ---------------------------------------------------------------------------
# Built-in implementations — one case arm per supported QA task.
# When adding a new task, also add a timeout entry in _task_timeout() above.
# ---------------------------------------------------------------------------
_run_impl() {
    case "${TASK_NAME}" in

        test)
            # Run unit tests if they exist, then integration tests if present.
            # Track the worst pytest exit code across runs so a genuine failure
            # still fails the task, but every stage (and the summary) still runs.
            # Note: `cmd || rc_test=$?` only assigns on failure, so a later
            # passing stage cannot reset an earlier recorded failure.
            rc_test=0
            if [ -d "${_PKG}/tests/unit/" ]; then
                uv run pytest "${_PKG}/tests/unit/" \
                    -v --tb=short \
                    --junitxml=results-unit.xml \
                    --cov="${_MOD}" --cov-branch --cov-report=json \
                    || rc_test=$?
            else
                echo "test: no unit tests found — skipping"
            fi

            # Run pytest integration tests (only present if integration tests exist)
            if [ -d "${_PKG}/tests/integration/" ]; then
                uv run pytest "${_PKG}/tests/integration/" \
                    -v --tb=short -m integration \
                    --junitxml=results-integration.xml || rc_test=$?
            fi

            # Only run the summary when pytest actually produced results
            if [ -f coverage.json ]; then
                uv run python "${_PKG}/tests/scripts/summarize_tests.py" \
                    --coverage-file=coverage.json
            else
                echo "test: no coverage.json produced — skipping summary"
            fi
            return "${rc_test}"
            ;;

        test:unit)
            uv run pytest "${_PKG}/tests/unit/" \
                -v --tb=short --junitxml=results-unit.xml
            ;;

        test:file)
            if [ "$#" -eq 0 ]; then
                printf 'usage: qa-task.sh test:file <file_or_pattern...>\n' >&2
                return 1
            fi
            uv run pytest "$@" -v --tb=short
            ;;

        test:integration)
            uv run pytest "${_PKG}/tests/integration/" \
                -v --tb=short -m integration \
                --junitxml=results-integration.xml
            ;;

        test:cov)
            uv run pytest "${_PKG}/tests/" \
                --cov="${_MOD}" --cov-branch \
                --cov-report=term-missing --cov-report=xml
            ;;

        lint)
            uv run ruff check "${_PKG}/src/" "${_PKG}/tests/" || return
            uv run ruff format --check "${_PKG}/src/" "${_PKG}/tests/"
            ;;

        typecheck)
            uv run ty check "${_PKG}/src/"
            ;;

        check)
            run_raw_task lint || return
            run_raw_task typecheck || return
            run_raw_task test
            ;;

        pre-pr)
            bash scripts/pre-pr.sh
            ;;

        complexity)
            run_raw_task complexity:cyclomatic || return
            run_raw_task complexity:cognitive || return
            run_raw_task similarity
            ;;

        complexity:cyclomatic)
            uv run radon cc "${_PKG}/src/${_MOD}" \
                --average --show-complexity || return
            uv run xenon "${_PKG}/src/${_MOD}" \
                --max-absolute B --max-modules A --max-average A
            ;;

        complexity:cognitive)
            uv run flake8 --select=CCR001 "${_PKG}/src/${_MOD}/"
            ;;

        similarity)
            FILE_COUNT=$(find "${_PKG}/src/${_MOD}" -name '*.py' | wc -l)
            if [ "${FILE_COUNT}" -gt 150 ]; then
                printf 'similarity: %d files — scan time grows O(n²) above 150; consider scoping\n' \
                    "${FILE_COUNT}" >&2
            fi
            OUTPUT=$(find "${_PKG}/src/${_MOD}" -name '*.py' -print0 \
                | xargs -0 uv run symilar -d 8 \
                    --ignore-imports --ignore-signatures) || return
            echo "$OUTPUT"
            DUPES=$(printf '%s\n' "$OUTPUT" \
                | sed -n 's/.*duplicates=\([0-9][0-9]*\).*/\1/p' \
                | head -n1)
            if [ "${DUPES:-0}" -gt 0 ]; then
                echo "❌ Found $DUPES duplicate lines" >&2
                return 1
            fi
            ;;

        security:audit)
            run_raw_task security:deps || return
            run_raw_task security:secrets || return
            run_raw_task security:python || return
            run_raw_task security:actions
            ;;

        security:deps)
            uv export --format requirements-txt \
                --all-extras --all-groups --no-emit-project \
                | uv run pip-audit -r /dev/stdin \
                    --strict --progress-spinner off
            ;;

        security:secrets)
            if [ "${CI:-}" = "true" ]; then
                # CI fast path: scan only files changed relative to the merge base.
                # Fetch main into FETCH_HEAD (no local branch or tracking-ref
                # assumptions) so merge-base works on a shallow single-branch checkout.
                git fetch --depth=1 origin main 2>/dev/null || true
                _base=$(git merge-base HEAD FETCH_HEAD 2>/dev/null || echo HEAD~1)
                _changed_nul=$(git diff --name-only -z "${_base}" HEAD 2>/dev/null || true)
                if [ -n "${_changed_nul}" ]; then
                    printf '%s' "${_changed_nul}" \
                        | xargs -0 uv run detect-secrets-hook \
                            --baseline .secrets.baseline --
                else
                    echo "security:secrets: no changed files — skipping hook"
                fi
            else
                # Local full scan: check all tracked and untracked (non-ignored) files.
                # git ls-files -z gives portable null-delimited output and honours
                # .gitignore, so build artefacts and vendored dirs are never scanned.
                { git ls-files -z; git ls-files --others --exclude-standard -z; } \
                    | xargs -0 uv run detect-secrets-hook \
                        --baseline .secrets.baseline --
            fi
            ;;

        security:python)
            uv run ruff check --select S "${_PKG}/src/${_MOD}"
            ;;

        security:actions)
            uv run actionlint || return
            uv run zizmor --min-severity high --min-confidence high \
                --no-progress .github/workflows .github/actions
            ;;

        docker:lint)
            # Lint Dockerfiles with hadolint via Docker (no install required).
            # Pinned to specific version for reproducibility; update via Renovate.
            # failure-threshold=warning: exit on warning-level and above (error, warning)
            # but not info-level messages.
            HADOLINT_VERSION="${HADOLINT_VERSION:-2.15.1}"
            if ! command -v docker >/dev/null 2>&1; then
                echo "docker:lint: Docker not available — skipping" >&2
                return 0
            fi
            docker run --rm -i \
                "ghcr.io/hadolint/hadolint:v${HADOLINT_VERSION}" \
                hadolint --no-color --failure-threshold warning - < .devcontainer/Dockerfile
            ;;

        *)
            if [ "$#" -eq 0 ]; then
                printf 'qa-task.sh: no built-in for %s and no command given\n' \
                    "${TASK_NAME}" >&2
                return 1
            fi
            "$@"
            ;;
    esac
}

# ---------------------------------------------------------------------------
# QA_NO_WRAP mode: run impl directly, streaming to the caller's stdout/stderr.
# Used internally by run_raw_task() and composite task arms to prevent nesting
# durable wrappers inside other durable wrappers.
# ---------------------------------------------------------------------------
if [[ -n "${QA_NO_WRAP:-}" ]]; then
    rc=0
    _run_impl "$@" || rc=$?
    exit "${rc}"
fi

_qa_timeout="${QA_TIMEOUT:-$(_task_timeout)}"

# Sanitize task name for filenames: replace :, /, and space with -
SAFE_NAME="${TASK_NAME//[:\/ ]/-}"

_qa_log_dir="${QA_LOG_DIR:-/tmp}"
_qa_tail="${QA_TAIL_LINES:-160}"


if [ "${TASK_NAME}" = "pre-pr" ]; then
    _log="${PRE_PR_LOG:-${_qa_log_dir}/concept2mqtt-pre-pr.log}"
    _status="${PRE_PR_STATUS:-${_qa_log_dir}/concept2mqtt-pre-pr.status}"
    _qa_tail="${PRE_PR_TAIL_LINES:-${_qa_tail}}"
else
    _log="${_qa_log_dir}/concept2mqtt-${SAFE_NAME}.log"
    _status="${_qa_log_dir}/concept2mqtt-${SAFE_NAME}.status"
fi

# Prefer gtimeout (GNU coreutils on macOS via Homebrew) over BSD timeout.
# If neither is available, run the task without a deadline and warn.
if command -v gtimeout >/dev/null 2>&1; then
    _tc="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
    _tc="timeout"
else
    _tc=""
fi

# ---------------------------------------------------------------------------
# Wrapper: run impl under timeout with QA_NO_WRAP=1 (prevents re-entry),
# capture output, write status file, tail log.
# ---------------------------------------------------------------------------
# Private per-run log directory: umask 077 ensures other local users cannot
# read or write the log/status files, mitigating predictable-/tmp-path risks.
(umask 077; mkdir -p "$(dirname "${_log}")" "$(dirname "${_status}")")
printf '%s: log -> %s | status -> %s | timeout -> %s\n' \
    "${TASK_NAME}" "${_log}" "${_status}" "${_qa_timeout}"

rc=0
if [ -n "${_tc}" ]; then
    "${_tc}" --foreground --kill-after=30s "${_qa_timeout}" \
        env QA_NO_WRAP=1 PYTHONUNBUFFERED=1 bash "${BASH_SOURCE[0]}" "${TASK_NAME}" "$@" \
        >"${_log}" 2>&1 || rc=$?
else
    printf 'WARNING: gtimeout/timeout not found — running %s without a deadline\n' \
        "${TASK_NAME}" >&2
    env QA_NO_WRAP=1 PYTHONUNBUFFERED=1 bash "${BASH_SOURCE[0]}" "${TASK_NAME}" "$@" \
        >"${_log}" 2>&1 || rc=$?
fi

printf '%s\n' "${rc}" >"${_status}"

if [ "${rc}" -eq 124 ] || [ "${rc}" -eq 137 ]; then
    printf '%s: TIMEOUT after %s\n' "${TASK_NAME}" "${_qa_timeout}" >&2
fi
printf '%s: exit %s -- last %s lines of %s:\n' \
    "${TASK_NAME}" "${rc}" "${_qa_tail}" "${_log}"
tail -n "${_qa_tail}" "${_log}"

# Propagate the real exit code — timeout (124/137) and tool-specific codes
# (pytest returns 2 for interrupts, 5 for no-tests-collected) are preserved.
exit "${rc}"
