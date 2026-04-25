#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ROOM_ID:-}" ]]; then
  echo "ROOM_ID 未设置" >&2
  exit 1
fi

python - <<'PY'
import json
import os
import sys
import urllib.request

room_id = os.environ["ROOM_ID"].strip()

headers = {
    "User-Agent": "BiliFlow/0.1 (+https://github.com)",
    "Accept": "application/json",
}


def http_get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def set_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}<<__EOF__\n{value}\n__EOF__\n")


room_init = http_get_json(
    f"https://api.live.bilibili.com/room/v1/Room/room_init?id={room_id}"
)

if room_init.get("code") != 0:
    raise SystemExit(f"room_init 调用失败：{room_init}")

room_data = room_init.get("data") or {}
real_room_id = str(room_data.get("room_id") or room_id)

room_info = http_get_json(
    f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={real_room_id}"
)

if room_info.get("code") != 0:
    raise SystemExit(f"get_info 调用失败：{room_info}")

info_data = room_info.get("data") or {}
live_status = str(info_data.get("live_status", room_data.get("live_status", 0)))
anchor_name = info_data.get("uname") or ""
live_title = info_data.get("title") or ""

result = {
    "is_live": "true" if live_status == "1" else "false",
    "live_status": live_status,
    "room_id_real": real_room_id,
    "short_id": str(room_data.get("short_id") or ""),
    "uid": str(room_data.get("uid") or info_data.get("uid") or ""),
    "anchor_name": anchor_name,
    "live_title": live_title,
    "room_url": f"https://live.bilibili.com/{real_room_id}",
}

for key, value in result.items():
    set_output(key, value)

print(json.dumps(result, ensure_ascii=False))
PY

