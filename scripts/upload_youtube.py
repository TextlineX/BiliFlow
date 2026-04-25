#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def append_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}<<__EOF__\n{value}\n__EOF__\n")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description-file")
    parser.add_argument("--privacy-status", default="public")
    parser.add_argument("--category-id", default="20")
    parser.add_argument("--tags", default="")
    return parser.parse_args()


def build_credentials() -> Credentials:
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    credentials.refresh(Request())
    return credentials


def upload_video(args) -> dict:
    description = ""
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")

    tags = [item.strip() for item in args.tags.split(",") if item.strip()]

    youtube = build("youtube", "v3", credentials=build_credentials())

    body = {
        "snippet": {
            "title": args.title,
            "description": description,
            "categoryId": args.category_id,
        },
        "status": {
            "privacyStatus": args.privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if tags:
        body["snippet"]["tags"] = tags

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(args.file, chunksize=8 * 1024 * 1024, resumable=True),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    return {
        "video_id": video_id,
        "video_url": video_url,
        "title": args.title,
        "privacy_status": args.privacy_status,
    }


def main():
    args = parse_args()
    result = upload_video(args)
    append_output("youtube_video_id", result["video_id"])
    append_output("youtube_video_url", result["video_url"])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

