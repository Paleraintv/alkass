#!/usr/bin/env python3
"""Fetch all Alkass endpoints and create one playlist file per channel."""
from __future__ import annotations

import os
import re
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = os.environ.get("PLAYLIST_SOURCE_URL", "https://alkass.aboozayed.web.id").rstrip("/")
OUTPUT = Path(os.environ.get("PLAYLIST_OUTPUT", "playlist.m3u"))
MAX_ENDPOINT = int(os.environ.get("PLAYLIST_MAX_ENDPOINT", "20"))


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "alkass-github-sync/3.1 (+GitHub Actions)",
            "Accept": "application/vnd.apple.mpegurl, audio/x-mpegurl, text/plain, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig", errors="strict")


def parse_entries(text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("not a valid M3U playlist")

    entries: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if line.startswith("#EXTINF:") and index + 1 < len(lines):
            stream_url = lines[index + 1]
            if not stream_url.startswith("#"):
                entries.append((line, stream_url))
    return entries


def channel_key(metadata: str) -> str:
    match = re.search(r'tvg-id="([^"]+)"', metadata)
    if match:
        return match.group(1).lower()
    return metadata.split(",", 1)[-1].strip().lower()


def write_single_channel_file(number: int, metadata: str, stream_url: str) -> None:
    Path(f"{number}.m3u8").write_text(
        f"#EXTM3U\n{metadata}\n{stream_url}\n", encoding="utf-8"
    )


def main() -> int:
    urls = [SOURCE_URL] + [f"{SOURCE_URL}/{number}" for number in range(1, MAX_ENDPOINT + 1)]
    merged: list[tuple[str, str]] = []
    seen_channels: set[str] = set()
    successful = 0

    for url in urls:
        try:
            entries = parse_entries(fetch(url))
        except Exception as exc:
            print(f"Skipping {url}: {exc}", file=sys.stderr)
            continue
        successful += 1
        for metadata, stream_url in entries:
            key = channel_key(metadata)
            if key not in seen_channels:
                seen_channels.add(key)
                merged.append((metadata, stream_url))
            else:
                # Keep the newest signed URL for this channel.
                for index, (old_metadata, _) in enumerate(merged):
                    if channel_key(old_metadata) == key:
                        merged[index] = (metadata, stream_url)
                        break
        print(f"Fetched {len(entries)} channel(s) from {url}")

    if not successful or not merged:
        print("No valid channels were fetched from any endpoint.", file=sys.stderr)
        return 1

    output_lines = ["#EXTM3U"]
    for number, (metadata, stream_url) in enumerate(merged, start=1):
        output_lines.extend((metadata, stream_url))
        write_single_channel_file(number, metadata, stream_url)

    OUTPUT.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"Updated {OUTPUT} and {len(merged)} per-channel m3u8 file(s) from {successful} endpoint(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
