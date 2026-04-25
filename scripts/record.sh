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

: "${ROOM_ID:?ROOM_ID 未设置}"
: "${OUTPUT_DIR:?OUTPUT_DIR 未设置}"

BILIUP_BIN="${BILIUP_BIN:-$(pwd)/.tools/biliup}"
MAX_RECORD_SECONDS="${MAX_RECORD_SECONDS:-19800}"
ROOM_URL="${ROOM_URL:-https://live.bilibili.com/${ROOM_ID}}"
work_dir="${OUTPUT_DIR}/record-workdir"

mkdir -p "${work_dir}"

cookie_args=()
if [[ -n "${BILIUP_USER_COOKIE_JSON:-}" ]]; then
  cookie_file="${OUTPUT_DIR}/biliup.cookies.json"
  printf '%s' "${BILIUP_USER_COOKIE_JSON}" > "${cookie_file}"
  cookie_args=(-u "${cookie_file}")
fi

if [[ ! -x "${BILIUP_BIN}" ]]; then
  echo "找不到 biliup 二进制：${BILIUP_BIN}" >&2
  exit 1
fi

pushd "${work_dir}" >/dev/null
set +e
timeout --signal=INT "${MAX_RECORD_SECONDS}s" "${BILIUP_BIN}" "${cookie_args[@]}" download "${ROOM_URL}"
command_status=$?
set -e
popd >/dev/null

timed_out="false"
record_status="success"

case "${command_status}" in
  0)
    ;;
  124|130|143)
    timed_out="true"
    record_status="timeout"
    ;;
  *)
    record_status="failed"
    ;;
esac

source_file="$(find "${work_dir}" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.flv' -o -iname '*.ts' -o -iname '*.mkv' \) -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2- || true)"

if [[ -z "${source_file}" ]]; then
  echo "未找到录制输出文件" >&2
  append_output "record_status" "${record_status}"
  append_output "timed_out" "${timed_out}"
  exit 1
fi

video_path="${OUTPUT_DIR}/video.mp4"
source_ext="${source_file##*.}"

if [[ "${source_ext,,}" == "mp4" ]]; then
  mv -f "${source_file}" "${video_path}"
else
  if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -hide_banner -loglevel error -y -i "${source_file}" -c copy "${video_path}" || {
      video_path="${OUTPUT_DIR}/video.${source_ext}"
      mv -f "${source_file}" "${video_path}"
    }
  else
    video_path="${OUTPUT_DIR}/video.${source_ext}"
    mv -f "${source_file}" "${video_path}"
  fi
fi

append_output "record_status" "${record_status}"
append_output "timed_out" "${timed_out}"
append_output "video_path" "${video_path}"
append_output "video_name" "$(basename "${video_path}")"
append_output "source_path" "${source_file}"

if [[ "${record_status}" == "failed" ]]; then
  exit "${command_status}"
fi

