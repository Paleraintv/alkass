#!/usr/bin/env python3
"""Fetch the current Alkass playlist and write it to playlist.m3u."""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = os.environ.get(
    "PLAYLIST_SOURCE_URL",
    "https://alkass.aboozayed.web.id",
)
OUTPUT = Path(os.environ.get("PLAYLIST_OUTPUT", "playlist.m3u"))


def main() -> int:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "alkass-github-sync/1.0 (+GitHub Actions)",
            "Accept": "application/vnd.apple.mpegurl, audio/x-mpegurl, text/plain, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except Exception as exc:
        print(f"Failed to fetch {SOURCE_URL}: {exc}", file=sys.stderr)
        return 1

    text = body.decode("utf-8-sig", errors="strict").replace("\r\n", "\n").strip() + "\n"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        print("Fetched content is not a valid M3U playlist (missing #EXTM3U).", file=sys.stderr)
        return 1
    if not any(line.startswith("#EXTINF:") for line in lines):
        print("Fetched playlist contains no channel entries.", file=sys.stderr)
        return 1

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    channels = sum(line.startswith("#EXTINF:") for line in lines)
    print(f"Updated {OUTPUT} with {channels} channel(s) from {SOURCE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
