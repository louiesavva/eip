#!/usr/bin/env python3
"""Build data/search-index.json from YouTube caption files.

Fetch the captions once (each file is named by its video ID):

    yt-dlp --skip-download --write-auto-subs --sub-langs en --convert-subs srt \
        -o "%(id)s" "https://www.youtube.com/@LouieSavva/videos"

Then point this script at the folder they landed in:

    python3 tools/build_search_index.py path/to/srt-folder
    python3 tools/build_conversations.py

The index keeps each episode's caption text with a timestamp every few
seconds, so a search result can link to the moment it was said.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "data" / "episodes.json"
OUT = ROOT / "data" / "search-index.json"

SEGMENT_SECONDS = 8  # how finely timestamps are kept

TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->")


def seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def normalise(text):
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = re.sub(r"\[[^\]]*\]", " ", text)          # [Music], [Laughter]
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def caption_lines(path):
    """Yield (start_seconds, line) for each new line of a rolling caption file.

    YouTube's automatic captions repeat the previous line at the top of each
    cue, so every line appears two or three times. Keep only its first
    appearance.
    """
    recent = []
    start = 0.0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TIME.match(raw.strip())
        if m:
            start = seconds(*m.groups())
            continue
        line = normalise(raw)
        if not line or line.isdigit():
            continue
        if line in recent:
            continue
        recent = (recent + [line])[-3:]
        yield start, line


def segments(path):
    """Group caption lines into segments of roughly SEGMENT_SECONDS."""
    segs, words, seg_start = [], [], None
    for start, line in caption_lines(path):
        if seg_start is None:
            seg_start = start
        elif start - seg_start >= SEGMENT_SECONDS:
            segs.append((int(seg_start), " ".join(words)))
            words, seg_start = [], start
        words.append(line)
    if words:
        segs.append((int(seg_start), " ".join(words)))
    return segs


def display_title(ep):
    if ep.get("guest"):
        title = ep["guest"]
    elif ep.get("solo"):
        title = "Louie and Matthew"
    else:
        title = f"Episode {ep['number']}"
    if ep.get("part"):
        title += f", {ep['part'].lower()}"
    return title


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    files = {p.name.split(".")[0]: p for p in folder.glob("*.srt")}

    episodes = json.loads(EPISODES.read_text(encoding="utf-8"))["episodes"]
    items, missing = [], []
    for ep in sorted(episodes, key=lambda e: e["number"]):
        videos = [(ep.get("youtube"), display_title(ep))]
        videos += [(x["youtube"], x["label"]) for x in ep.get("extras", [])]
        for video_id, title in videos:
            path = files.get(video_id)
            if not path:
                missing.append(ep["number"])
                continue
            segs = segments(path)
            if not segs:
                missing.append(ep["number"])
                continue
            # Store start times as gaps from the previous segment to keep the file small.
            gaps, prev = [], 0
            for t, _ in segs:
                gaps.append(t - prev)
                prev = t
            items.append({
                "n": ep["number"],
                "id": video_id,
                "title": title,
                "s": [text for _, text in segs],
                "t": gaps,
            })

    words = sum(len(" ".join(i["s"]).split()) for i in items)
    covered = sorted({i["n"] for i in items})
    index = {
        "episodes_covered": len(covered),
        "words": words,
        "items": items,
    }
    OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = OUT.stat().st_size / 1e6
    print(f"Indexed {len(items)} videos ({len(covered)} episodes, {words:,} words) -> "
          f"{OUT.relative_to(ROOT)} ({size:.1f} MB)")
    if missing:
        print("No captions for episodes:", ", ".join(f"#{n}" for n in sorted(set(missing))))


if __name__ == "__main__":
    main()
