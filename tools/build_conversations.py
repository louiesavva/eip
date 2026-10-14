#!/usr/bin/env python3
"""Build conversations.html from data/episodes.json.

The site itself stays plain HTML with no build step: this script is only an
authoring helper. Edit data/episodes.json, run the script, commit both files.

    python3 tools/build_conversations.py

To fill in YouTube links, export the channel's video list with yt-dlp and pass
it in. Each line is "<video id> <title>" (a tab or a space between them); the
episode number is read from the "#NN" in the title.

    yt-dlp --flat-playlist --print "%(id)s %(title)s" \
        "https://www.youtube.com/@LouieSavva/videos" > episodes.tsv
    python3 tools/build_conversations.py --youtube episodes.tsv
"""

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "episodes.json"
OUT = ROOT / "conversations.html"

BOOK_PDF = "/assets/the_existential_files.pdf"

HEAD = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Conversations | Everything Is Pointless</title>
  <meta name="description" content="The Existential Files: conversations on life, death, nihilism, the paranormal and the mind, with Dr Louie Savva, Dr Matthew Smith and guests." />
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon.png" />
  <link rel="stylesheet" href="style.css" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Everything Is Pointless" />
  <meta property="og:title" content="Conversations: The Existential Files" />
  <meta property="og:description" content="Conversations on life, death, nihilism, the paranormal and the mind, with Dr Louie Savva, Dr Matthew Smith and guests." />
  <meta property="og:url" content="https://everythingispointless.com/conversations.html" />
  <meta property="og:image" content="https://everythingispointless.com/assets/og-image.jpg" />
  <meta property="og:image:alt" content="Everything Is Pointless by Dr Louie Savva" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Conversations: The Existential Files" />
  <meta name="twitter:description" content="Conversations on life, death, nihilism, the paranormal and the mind, with Dr Louie Savva, Dr Matthew Smith and guests." />
  <meta name="twitter:image" content="https://everythingispointless.com/assets/og-image.jpg" />
</head>
<body>
  <div class="wrap" id="top">
    <header class="site-header">
      <p class="site-title"><a href="index.html">Everything Is Pointless</a></p>
      <p class="subtitle">A former blog. An ongoing worldview.</p>
      <nav aria-label="Primary">
        <a href="index.html#about">About</a>
        <a href="index.html#books">Books</a>
        <a href="index.html#writing">Writing</a>
        <a href="conversations.html" aria-current="page">Conversations</a>
        <a href="index.html#resources">Resources</a>
        <a href="index.html#author">Author</a>
        <a href="index.html#contact">Contact</a>
      </nav>
    </header>

    <main>
      <section id="conversations">
        <h1 class="page-title">Conversations</h1>
        <p class="meta">The Existential Files, 2017</p>
        <p>
          In 2017 Matthew Smith and I, two psychologists and long-time friends, recorded more than sixty
          conversations about life, the universe and everything. Some were just the two of us. Most had a guest:
          philosophers, psychologists, sceptics, writers and scientists, among them
          <a href="#ep-34">Susan Blackmore</a>, <a href="#ep-32">Chris French</a> and <a href="#ep-20">Taner Edis</a>. Sometimes funny, sometimes serious, sometimes profound even.
        </p>
        <p>
          The book <a href="{book}"><em>The Existential Files</em></a> grew out of these conversations.
          The recordings themselves are all on <a href="{channel}">YouTube</a>.
        </p>
"""

FOOT = """      </section>
    </main>

    <footer>
      <p><strong>Everything Is Pointless</strong> — books, essays, and existential resources by Dr Louie Savva.</p>
      <p><a href="#top">Back to top</a></p>
    </footer>
  </div>
</body>
</html>
"""


def esc(text):
    return html.escape(text, quote=True)


def nice_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def episode_html(ep):
    n = ep["number"]
    guest = ep.get("guest")
    role = ep.get("role")
    if guest:
        heading = f'<span class="ep-guest">{esc(guest)}</span>'
        if role:
            heading += f' <span class="ep-role">{esc(role)}</span>'
    elif ep.get("solo"):
        heading = '<span class="ep-guest">Louie and Matthew</span> <span class="ep-role">no guest</span>'
    else:
        heading = f'<span class="ep-guest">Episode {n}</span>'

    meta = []
    if ep.get("part"):
        meta.append(esc(ep["part"]))
    if ep.get("note"):
        meta.append(esc(ep["note"]))
    if ep.get("date"):
        meta.append(f'<time datetime="{esc(ep["date"])}">{nice_date(ep["date"])}</time>')
    if ep.get("youtube"):
        url = f'https://www.youtube.com/watch?v={esc(ep["youtube"])}'
        meta.append(f'<a href="{url}">Watch on YouTube</a>')
    for extra in ep.get("extras", []):
        url = f'https://www.youtube.com/watch?v={esc(extra["youtube"])}'
        meta.append(f'<a href="{url}">{esc(extra["label"])}</a>')
    meta_html = ' <span class="sep">|</span> '.join(meta)
    topic = ep.get("topic")
    topic_html = f"              <p>{esc(topic)}</p>\n" if topic else ""

    if not (guest or ep.get("solo") or topic):
        # No notes yet for this episode: just a one-line link.
        return f"""          <li class="episode stub" id="ep-{n}">
            <p class="ep-num">#{n}</p>
            <div class="ep-body">
              <p class="meta">{meta_html}</p>
            </div>
          </li>
"""

    return f"""          <li class="episode" id="ep-{n}">
            <p class="ep-num">#{n}</p>
            <div class="ep-body">
              <h2>{heading}</h2>
{topic_html}              <p class="meta">{meta_html}</p>
            </div>
          </li>
"""


def missing_note(numbers, channel):
    """Say which episodes before the first listed one are not here yet."""
    first = min(numbers)
    if first <= 1:
        return ""
    span = "#1" if first == 2 else f"#1–#{first - 1}"
    return (
        f'        <p class="small-note">Earlier episodes ({span}) are on the '
        f'<a href="{channel}">YouTube channel</a>.</p>\n'
    )


def apply_youtube_ids(data, tsv_path):
    by_number = {ep["number"]: ep for ep in data["episodes"]}
    matched = 0
    for line in Path(tsv_path).read_text(encoding="utf-8").splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        video_id, title = fields
        m = re.search(r"#\s*(\d+)", title)
        if not m:
            continue
        number = int(m.group(1))
        ep = by_number.get(number)
        if ep is None:
            # An episode we have no notes for yet: add a stub so it still gets
            # listed and linked. Fill in its guest and topic by hand later.
            g = re.search(r"special guests?\s+(.+)$", title, re.IGNORECASE)
            ep = {"number": number, "guest": g.group(1).strip() if g else None,
                  "role": None, "topic": None, "youtube": None}
            data["episodes"].append(ep)
            by_number[number] = ep
        video_id = video_id.strip()
        extra = re.search(r"\b(addendum|extra|bonus)\b.*$", title, re.IGNORECASE)
        if extra:
            # A short follow-up to an episode, e.g. "Episode #12 - Addendum on
            # Coincidences": list it as an extra link on that episode.
            label = extra.group(0).strip()
            label = label[0].upper() + label[1:].lower()
            extras = [x for x in ep.get("extras", []) if x["youtube"] != video_id]
            extras.append({"label": label, "youtube": video_id})
            ep["extras"] = extras
        else:
            ep["youtube"] = video_id
        matched += 1
    data["episodes"].sort(key=lambda e: e["number"])
    return matched


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--youtube", help="yt-dlp output: one '<video id> <title>' per line")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))

    if args.youtube:
        matched = apply_youtube_ids(data, args.youtube)
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Matched {matched} YouTube videos to episodes; saved {DATA.relative_to(ROOT)}")

    # Oldest first: the conversation runs in order, and later episodes refer back.
    episodes = sorted(data["episodes"], key=lambda e: e["number"])
    channel = data["youtube_channel"]

    parts = [HEAD.replace("{book}", BOOK_PDF).replace("{channel}", esc(channel))]
    parts.append(missing_note([e["number"] for e in episodes], esc(channel)))
    parts.append('        <ol class="episode-list">\n')
    parts.extend(episode_html(ep) for ep in episodes)
    parts.append("        </ol>\n")
    parts.append(FOOT)

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(episodes)} episodes")


if __name__ == "__main__":
    main()
