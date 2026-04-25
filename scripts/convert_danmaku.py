#!/usr/bin/env python3
import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def ass_time(ms: int) -> str:
    total_seconds = max(0, ms) / 1000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def srt_time(ms: int) -> str:
    total_seconds = max(0, ms) // 1000
    milliseconds = max(0, ms) % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def rgb_to_ass(color: int) -> str:
    color = safe_int(color, 16777215)
    red = (color >> 16) & 0xFF
    green = (color >> 8) & 0xFF
    blue = color & 0xFF
    return f"&H{blue:02X}{green:02X}{red:02X}&"


def load_events(path: Path) -> list[dict]:
    events = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("kind") != "danmaku":
                continue
            item["timestamp_ms"] = safe_int(item.get("timestamp_ms"))
            item["offset_ms"] = safe_int(item.get("offset_ms"))
            item["mode"] = safe_int(item.get("mode"), 1)
            item["font_size"] = safe_int(item.get("font_size"), 25)
            item["color"] = safe_int(item.get("color"), 16777215)
            item["user_id"] = str(item.get("user_id") or "")
            item["user_name"] = str(item.get("user_name") or "")
            item["message"] = str(item.get("message") or "")
            if not item.get("user_hash"):
                item["user_hash"] = sha1(item["user_id"].encode("utf-8")).hexdigest()[:8]
            if not item.get("row_id"):
                item["row_id"] = str(item["timestamp_ms"])
            events.append(item)
    events.sort(key=lambda item: (item["offset_ms"], item["timestamp_ms"], item["row_id"]))
    return events


def write_jsonl(events: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for item in events:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_csv_file(events: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "offset_ms",
                "offset_seconds",
                "timestamp_iso",
                "user_id",
                "user_name",
                "message",
                "mode",
                "font_size",
                "color",
            ]
        )
        for item in events:
            timestamp_iso = datetime.fromtimestamp(
                item["timestamp_ms"] / 1000, tz=timezone.utc
            ).isoformat()
            writer.writerow(
                [
                    item["offset_ms"],
                    f"{item['offset_ms'] / 1000:.3f}",
                    timestamp_iso,
                    item["user_id"],
                    item["user_name"],
                    item["message"],
                    item["mode"],
                    item["font_size"],
                    item["color"],
                ]
            )


def write_xml_file(events: list[dict], output_path: Path, room_id: str) -> None:
    root = Element("i")
    SubElement(root, "chatserver").text = "live.bilibili.com"
    SubElement(root, "chatid").text = str(room_id)
    SubElement(root, "mission").text = "0"
    SubElement(root, "maxlimit").text = str(len(events))
    SubElement(root, "state").text = "0"
    SubElement(root, "real_name").text = "0"
    SubElement(root, "source").text = "bilibili-live"

    for item in events:
        p_value = ",".join(
            [
                f"{item['offset_ms'] / 1000:.3f}",
                str(item["mode"]),
                str(item["font_size"]),
                str(item["color"]),
                str(item["timestamp_ms"] // 1000),
                "0",
                str(item["user_hash"]),
                str(item["row_id"]),
            ]
        )
        node = SubElement(root, "d")
        node.set("p", p_value)
        node.text = item["message"]

    ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)


def assign_lanes(events: list[dict], line_height: int, max_lanes: int) -> list[int]:
    lane_free_at = [0 for _ in range(max_lanes)]
    lanes = []
    for item in events:
        offset_ms = item["offset_ms"]
        lane_index = None
        for index, free_at in enumerate(lane_free_at):
            if free_at <= offset_ms:
                lane_index = index
                break
        if lane_index is None:
            lane_index = min(range(max_lanes), key=lambda idx: lane_free_at[idx])
        lane_free_at[lane_index] = offset_ms + 1200
        lanes.append(lane_index)
    return lanes


def write_ass_file(events: list[dict], output_path: Path) -> None:
    width = 1920
    height = 1080
    line_height = 42
    top_events = [item for item in events if item["mode"] == 5]
    bottom_events = [item for item in events if item["mode"] == 4]
    scroll_events = [item for item in events if item["mode"] not in (4, 5)]

    scroll_lanes = assign_lanes(scroll_events, line_height, 18)
    top_lanes = assign_lanes(top_events, line_height, 10)
    bottom_lanes = assign_lanes(bottom_events, line_height, 10)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Arial,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,0,0,0,0,100,100,0,0,1,1.5,0,2,20,20,20,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    def build_dialogue(item: dict, lane_index: int, position_type: str) -> str:
        start_ms = item["offset_ms"]
        end_ms = start_ms + (8000 if position_type == "scroll" else 5000)
        color = rgb_to_ass(item["color"])
        font_size = max(24, min(54, item["font_size"]))
        text = ass_escape(f"{item['user_name']}: {item['message']}")

        if position_type == "scroll":
            y = 40 + lane_index * line_height
            text_width = max(220, int(len(text) * font_size * 0.6))
            start_x = width + 40
            end_x = -text_width
            effect = f"{{\\fs{font_size}\\c{color}\\move({start_x},{y},{end_x},{y})}}{text}"
        elif position_type == "top":
            y = 40 + lane_index * line_height
            effect = f"{{\\an8\\fs{font_size}\\c{color}\\pos({width // 2},{y})}}{text}"
        else:
            y = height - 80 - lane_index * line_height
            effect = f"{{\\an2\\fs{font_size}\\c{color}\\pos({width // 2},{y})}}{text}"

        return f"Dialogue: 0,{ass_time(start_ms)},{ass_time(end_ms)},Default,,0,0,0,,{effect}"

    for item, lane in zip(scroll_events, scroll_lanes):
        lines.append(build_dialogue(item, lane, "scroll"))
    for item, lane in zip(top_events, top_lanes):
        lines.append(build_dialogue(item, lane, "top"))
    for item, lane in zip(bottom_events, bottom_lanes):
        lines.append(build_dialogue(item, lane, "bottom"))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt_file(events: list[dict], output_path: Path) -> None:
    buckets: dict[int, list[dict]] = defaultdict(list)
    for item in events:
        bucket_key = item["offset_ms"] // 2000
        buckets[bucket_key].append(item)

    lines = []
    cue_index = 1
    for bucket_key in sorted(buckets.keys()):
        group = buckets[bucket_key]
        start_ms = bucket_key * 2000
        end_ms = start_ms + 3500
        body_lines = [
            f"{item['user_name'] or item['user_id']}: {item['message']}"
            for item in group[:4]
        ]
        if len(group) > 4:
            body_lines.append("…")
        lines.append(str(cue_index))
        lines.append(f"{srt_time(start_ms)} --> {srt_time(end_ms)}")
        lines.append("\n".join(body_lines))
        lines.append("")
        cue_index += 1

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_search_index(
    events: list[dict],
    output_path: Path,
    room_id: str,
    session_id: str,
    segment_index: str,
    live_title: str,
    anchor_name: str,
) -> None:
    payload = {
        "room_id": str(room_id),
        "session_id": str(session_id),
        "segment_index": str(segment_index),
        "live_title": live_title,
        "anchor_name": anchor_name,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(events),
        "items": [
            {
                "offset_ms": item["offset_ms"],
                "offset_seconds": round(item["offset_ms"] / 1000, 3),
                "timestamp_ms": item["timestamp_ms"],
                "user_id": item["user_id"],
                "user_name": item["user_name"],
                "message": item["message"],
                "mode": item["mode"],
                "color": item["color"],
            }
            for item in events
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(
    events: list[dict],
    output_path: Path,
    room_id: str,
    session_id: str,
    segment_index: str,
    live_title: str,
    anchor_name: str,
) -> None:
    unique_users = len(
        {
            (item["user_id"], item["user_name"])
            for item in events
            if item["user_id"] or item["user_name"]
        }
    )
    summary = {
        "room_id": str(room_id),
        "session_id": str(session_id),
        "segment_index": str(segment_index),
        "live_title": live_title,
        "anchor_name": anchor_name,
        "count": len(events),
        "unique_users": unique_users,
        "duration_seconds": round((events[-1]["offset_ms"] / 1000) if events else 0, 3),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--room-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--segment-index", required=True)
    parser.add_argument("--live-title", default="")
    parser.add_argument("--anchor-name", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = load_events(input_path)

    write_jsonl(events, output_dir / "danmaku.jsonl")
    write_csv_file(events, output_dir / "danmaku.csv")
    write_xml_file(events, output_dir / "danmaku.xml", args.room_id)
    write_ass_file(events, output_dir / "danmaku.ass")
    write_srt_file(events, output_dir / "danmaku.srt")
    write_search_index(
        events,
        output_dir / "search-index.json",
        args.room_id,
        args.session_id,
        args.segment_index,
        args.live_title,
        args.anchor_name,
    )
    write_summary(
        events,
        output_dir / "summary.json",
        args.room_id,
        args.session_id,
        args.segment_index,
        args.live_title,
        args.anchor_name,
    )

    print(
        json.dumps(
            {
                "count": len(events),
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

