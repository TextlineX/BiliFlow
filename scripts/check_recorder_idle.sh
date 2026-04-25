#!/usr/bin/env bash
set -euo pipefail

append_output() {
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      echo "$1<<__EOF__"
      printf '%s\n' "$2"
      echo "__EOF__"
    } >> "${GITHUB_OUTPUT}"
  fi
}

if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
  echo "GITHUB_REPOSITORY 未设置" >&2
  exit 1
fi

json_file="$(mktemp)"
trap 'rm -f "${json_file}"' EXIT

gh api "repos/${GITHUB_REPOSITORY}/actions/workflows/record.yml/runs?per_page=20" > "${json_file}"

readarray -t values < <(
  python - "${json_file}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

active_statuses = {"queued", "in_progress", "waiting", "requested", "pending"}
runs = payload.get("workflow_runs", [])
active_runs = [run for run in runs if run.get("status") in active_statuses]

print("true" if not active_runs else "false")
print(str(len(active_runs)))
PY
)

recorder_idle="${values[0]}"
active_run_count="${values[1]}"

echo "record workflow idle=${recorder_idle}, active_runs=${active_run_count}"
append_output "recorder_idle" "${recorder_idle}"
append_output "active_run_count" "${active_run_count}"

