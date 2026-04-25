#!/usr/bin/env bash
set -euo pipefail

: "${ROOM_ID:?ROOM_ID 未设置}"
: "${SESSION_ID:?SESSION_ID 未设置}"
: "${SEGMENT_INDEX:?SEGMENT_INDEX 未设置}"

next_segment="$((SEGMENT_INDEX + 1))"

gh workflow run record.yml \
  -f room_id="${ROOM_ID}" \
  -f session_id="${SESSION_ID}" \
  -f segment_index="${next_segment}" \
  -f live_title="${LIVE_TITLE:-}"

echo "已派发下一段录制：segment=${next_segment}"
