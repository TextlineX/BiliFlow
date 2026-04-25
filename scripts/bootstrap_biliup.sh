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

target_bin="${BILIUP_BIN:-$(pwd)/.tools/biliup}"
mkdir -p "$(dirname "${target_bin}")"

if [[ -x "${target_bin}" ]]; then
  echo "使用现有 biliup 二进制：${target_bin}"
  append_output "biliup_bin" "${target_bin}"
  exit 0
fi

work_dir="$(mktemp -d)"
archive_path="${work_dir}/biliup.asset"

cleanup() {
  rm -rf "${work_dir}"
}
trap cleanup EXIT

asset_url="${BILIUP_DOWNLOAD_URL:-}"

if [[ -z "${asset_url}" ]]; then
  asset_url="$(
    python - <<'PY'
import json
import urllib.request

with urllib.request.urlopen(
    "https://api.github.com/repos/biliup/biliup-rs/releases/latest"
) as response:
    payload = json.load(response)

assets = payload.get("assets", [])

def score(name: str) -> tuple[int, int, int]:
    lower = name.lower()
    linux_score = int(
        any(token in lower for token in ("linux", "unknown-linux", "gnu", "musl"))
    )
    arch_score = int(any(token in lower for token in ("x86_64", "amd64")))
    archive_score = 2 if lower.endswith((".tar.gz", ".tgz")) else 1 if lower.endswith(".zip") else 0
    gnu_bonus = int("gnu" in lower)
    return linux_score, arch_score, archive_score + gnu_bonus

candidates = sorted(
    assets,
    key=lambda item: score(item.get("name", "")),
    reverse=True,
)

if not candidates:
    raise SystemExit("未找到 biliup-rs 发布资源，请手动设置 BILIUP_DOWNLOAD_URL")

best = candidates[0]
print(best["browser_download_url"])
PY
  )"
fi

echo "下载 biliup-rs：${asset_url}"
curl -fsSL "${asset_url}" -o "${archive_path}"

case "${asset_url}" in
  *.tar.gz|*.tgz)
    tar -xzf "${archive_path}" -C "${work_dir}"
    ;;
  *.zip)
    unzip -qo "${archive_path}" -d "${work_dir}"
    ;;
  *)
    ;;
esac

candidate_bin="$(find "${work_dir}" -type f \( -name 'biliup' -o -name 'biliup-cli' \) | head -n 1 || true)"

if [[ -z "${candidate_bin}" ]]; then
  candidate_bin="${archive_path}"
fi

install -m 0755 "${candidate_bin}" "${target_bin}"
echo "已安装 biliup 到 ${target_bin}"
append_output "biliup_bin" "${target_bin}"

