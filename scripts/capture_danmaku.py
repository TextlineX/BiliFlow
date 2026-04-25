#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import json
import os
import signal
import struct
import time
import urllib.request
import zlib
from hashlib import sha1

import brotli
import websockets


HEADERS = {
    "User-Agent": "BiliFlow/0.1 (+https://github.com)",
    "Accept": "application/json",
}


def http_get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def resolve_room(room_id: str) -> tuple[int, str, int]:
    room_init = http_get_json(
        f"https://api.live.bilibili.com/room/v1/Room/room_init?id={room_id}"
    )
    room_data = room_init.get("data") or {}
    real_room_id = int(room_data.get("room_id") or room_id)

    danmu_info = http_get_json(
        f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={real_room_id}&type=0"
    )
    danmu_data = danmu_info.get("data") or {}
    host_list = danmu_data.get("host_list") or []

    if not host_list:
        raise RuntimeError("未获取到弹幕服务器地址")

    host_info = host_list[0]
    host = host_info.get("host")
    port = host_info.get("wss_port") or host_info.get("ws_port")
    token = danmu_data.get("token")

    if not host or not port or not token:
        raise RuntimeError("弹幕服务器信息不完整")

    return real_room_id, f"wss://{host}:{port}/sub", token


def pack_packet(body: bytes, operation: int, version: int = 1, sequence: int = 1) -> bytes:
    header = struct.pack(">IHHII", 16 + len(body), 16, version, operation, sequence)
    return header + body


def iter_packets(blob: bytes):
    offset = 0
    while offset + 16 <= len(blob):
        packet_len, header_len, version, operation, sequence = struct.unpack(
            ">IHHII", blob[offset : offset + 16]
        )
        body_start = offset + header_len
        body_end = offset + packet_len
        yield version, operation, sequence, blob[body_start:body_end]
        offset += packet_len


def decode_payload(version: int, operation: int, body: bytes):
    if version == 2:
        for item in iter_packets(zlib.decompress(body)):
            yield from decode_payload(*item)
        return

    if version == 3:
        for item in iter_packets(brotli.decompress(body)):
            yield from decode_payload(*item)
        return

    if operation != 5:
        return

    try:
        text = body.decode("utf-8", errors="ignore")
        payload = json.loads(text)
    except Exception:
        return

    yield payload


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def normalize_timestamp_ms(value, fallback_ms: int) -> int:
    timestamp = safe_int(value, fallback_ms)
    if timestamp <= 0:
        return fallback_ms
    if timestamp < 10_000_000_000:
        return timestamp * 1000
    return timestamp


def write_json_line(handle, payload: dict) -> None:
    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    handle.flush()


def normalize_danmaku(payload: dict, start_ms: int, observed_ms: int) -> dict | None:
    cmd = str(payload.get("cmd") or "")
    base_cmd = cmd.split(":", 1)[0]
    if base_cmd != "DANMU_MSG":
        return None

    info = payload.get("info") or []
    meta = info[0] if len(info) > 0 else []
    message = info[1] if len(info) > 1 else ""
    user = info[2] if len(info) > 2 else []

    user_id = str(user[0]) if len(user) > 0 else ""
    user_name = str(user[1]) if len(user) > 1 else ""
    mode = safe_int(meta[1] if len(meta) > 1 else 1, 1)
    font_size = safe_int(meta[2] if len(meta) > 2 else 25, 25)
    color = safe_int(meta[3] if len(meta) > 3 else 16777215, 16777215)
    timestamp_ms = normalize_timestamp_ms(
        meta[4] if len(meta) > 4 else observed_ms,
        observed_ms,
    )
    user_hash = (
        str(meta[7])
        if len(meta) > 7 and meta[7]
        else sha1(user_id.encode("utf-8")).hexdigest()[:8]
    )
    row_id = str(meta[9]) if len(meta) > 9 else str(timestamp_ms)

    return {
        "kind": "danmaku",
        "cmd": cmd,
        "timestamp_ms": timestamp_ms,
        "offset_ms": max(0, timestamp_ms - start_ms),
        "user_id": user_id,
        "user_name": user_name,
        "message": str(message),
        "mode": mode,
        "font_size": font_size,
        "color": color,
        "user_hash": user_hash,
        "row_id": row_id,
    }


async def heartbeat(ws, stop_event: asyncio.Event, interval: int):
    while not stop_event.is_set():
        await asyncio.sleep(interval)
        if stop_event.is_set():
            break
        try:
            await ws.send(pack_packet(b"[object Object]", 2))
        except websockets.ConnectionClosed:
            break


def register_signal_handlers(loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            continue


def build_system_event(
    event: str,
    room_id: str,
    attempt: int,
    ws_url: str = "",
    detail: str = "",
) -> dict:
    payload = {
        "kind": "system",
        "event": event,
        "timestamp_ms": int(time.time() * 1000),
        "room_id": str(room_id),
        "attempt": attempt,
    }
    if ws_url:
        payload["ws_url"] = ws_url
    if detail:
        payload["detail"] = detail
    return payload


async def capture(room_id: str, output_path: str, heartbeat_interval: int, reconnect_delay: int):
    stop_event = asyncio.Event()
    start_ms = int(time.time() * 1000)

    loop = asyncio.get_running_loop()
    register_signal_handlers(loop, stop_event)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "a", encoding="utf-8") as handle:
        write_json_line(
            handle,
            {
                "kind": "session",
                "requested_room_id": str(room_id),
                "captured_at_ms": start_ms,
                "heartbeat_interval": heartbeat_interval,
                "reconnect_delay": reconnect_delay,
            },
        )

        attempt = 0
        while not stop_event.is_set():
            attempt += 1
            reconnect_needed = False
            disconnect_detail = ""
            real_room_id = room_id
            ws_url = ""

            try:
                real_room_id, ws_url, token = resolve_room(room_id)
                write_json_line(
                    handle,
                    build_system_event("connected", str(real_room_id), attempt, ws_url=ws_url),
                )

                auth_body = json.dumps(
                    {
                        "uid": 0,
                        "roomid": real_room_id,
                        "protover": 3,
                        "platform": "web",
                        "type": 2,
                        "key": token,
                    },
                    ensure_ascii=False,
                ).encode("utf-8")

                async with websockets.connect(ws_url, max_size=None, ping_interval=None) as ws:
                    await ws.send(pack_packet(auth_body, 7))
                    heartbeat_task = asyncio.create_task(
                        heartbeat(ws, stop_event, heartbeat_interval)
                    )

                    try:
                        while not stop_event.is_set():
                            try:
                                raw_message = await asyncio.wait_for(
                                    ws.recv(),
                                    timeout=heartbeat_interval + 10,
                                )
                            except asyncio.TimeoutError:
                                continue
                            except websockets.ConnectionClosed as exc:
                                reconnect_needed = not stop_event.is_set()
                                disconnect_detail = f"connection_closed:{exc.code}"
                                break

                            if not isinstance(raw_message, (bytes, bytearray)):
                                continue

                            observed_ms = int(time.time() * 1000)
                            for version, operation, _, body in iter_packets(raw_message):
                                for payload in decode_payload(version, operation, body):
                                    item = normalize_danmaku(payload, start_ms, observed_ms)
                                    if not item:
                                        continue
                                    write_json_line(handle, item)
                    finally:
                        heartbeat_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await heartbeat_task
            except Exception as exc:
                reconnect_needed = not stop_event.is_set()
                disconnect_detail = f"{type(exc).__name__}: {exc}"

            if stop_event.is_set():
                break

            if not reconnect_needed:
                break

            write_json_line(
                handle,
                build_system_event(
                    "disconnected",
                    str(real_room_id),
                    attempt,
                    ws_url=ws_url,
                    detail=disconnect_detail,
                ),
            )

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(1, reconnect_delay))
            except asyncio.TimeoutError:
                continue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--room-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--heartbeat", type=int, default=30)
    parser.add_argument("--reconnect-delay", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(
        capture(
            args.room_id,
            args.output,
            args.heartbeat,
            args.reconnect_delay,
        )
    )


if __name__ == "__main__":
    main()
