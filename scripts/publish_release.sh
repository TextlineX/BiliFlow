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

: "${RELEASE_TAG:?RELEASE_TAG 未设置}"
: "${RELEASE_TITLE:?RELEASE_TITLE 未设置}"
: "${RELEASE_DIR:?RELEASE_DIR 未设置}"

if [[ ! -d "${RELEASE_DIR}" ]]; then
  echo "Release 目录不存在：${RELEASE_DIR}" >&2
  exit 1
fi

mapfile -t assets < <(find "${RELEASE_DIR}" -maxdepth 1 -type f | sort)

if [[ "${#assets[@]}" -eq 0 ]]; then
  echo "没有可上传的 Release 资源" >&2
  exit 1
fi

if gh release view "${RELEASE_TAG}" >/dev/null 2>&1; then
  echo "复用已有 Release：${RELEASE_TAG}"
else
  if [[ -n "${RELEASE_NOTES_FILE:-}" && -f "${RELEASE_NOTES_FILE}" ]]; then
    gh release create "${RELEASE_TAG}" "${assets[@]}" --title "${RELEASE_TITLE}" --notes-file "${RELEASE_NOTES_FILE}"
    uploaded_on_create=true
  else
    gh release create "${RELEASE_TAG}" "${assets[@]}" --title "${RELEASE_TITLE}" --notes ""
    uploaded_on_create=true
  fi
fi

if [[ "${uploaded_on_create:-false}" != "true" ]]; then
  gh release upload "${RELEASE_TAG}" "${assets[@]}" --clobber
fi

release_url="$(gh release view "${RELEASE_TAG}" --json url --jq .url)"
append_output "release_tag" "${RELEASE_TAG}"
append_output "release_url" "${release_url}"
echo "Release 已发布：${release_url}"

