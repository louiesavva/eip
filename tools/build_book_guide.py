#!/usr/bin/env python3
"""Build book-guide.html: which conversations each chapter of The Existential Files draws on.

Edit data/book-guide.json, run the script, commit both files.

    python3 tools/build_book_guide.py

Each moment in the JSON is an episode number, a time in seconds and a short
note. Times link to that point in the YouTube video (two seconds early, as on
the Conversations page) and episode numbers link to the episode's entry there.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_conversations import FOOT, esc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "data" / "book-guide.json"
EPISODES = ROOT / "data" / "episodes.json"
OUT = ROOT / "book-guide.html"
EPUB = "/assets/the_existential_files.epub"

DESCRIPTION = ("Chapter by chapter, the moments in The Existential Files conversations that the book "
               "draws on, each linked to that point in the recording.")

HEAD = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>The Existential Files: chapter guide | Everything Is Pointless</title>
  <meta name="description" content="{DESCRIPTION}" />
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon.png" />
  <link rel="stylesheet" href="style.css" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Everything Is Pointless" />
  <meta property="og:title" content="The Existential Files: chapter guide" />
  <meta property="og:description" content="{DESCRIPTION}" />
  <meta property="og:url" content="https://everythingispointless.com/book-guide.html" />
  <meta property="og:image" content="https://everythingispointless.com/assets/og-image.jpg" />
  <meta property="og:image:alt" content="Everything Is Pointless by Dr Louie Savva" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="The Existential Files: chapter guide" />
  <meta name="twitter:description" content="{DESCRIPTION}" />
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
        <a href="conversations.html">Conversations</a>
        <a href="index.html#resources">Resources</a>
        <a href="index.html#author">Author</a>
        <a href="index.html#contact">Contact</a>
      </nav>
    </header>

    <main>
      <section id="guide">
        <h1 class="page-title"><em>The Existential Files</em>: chapter guide</h1>
        <p class="meta">Where the book comes from</p>
"""


def clock(s):
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def who(ep):
    if ep.get("guest"):
        return ep["guest"]
    return "Louie and Matthew"


def chapter_html(ch, episodes, pdf, offset):
    n = ch["n"]
    label = "Intro" if n == 0 else str(n)
    anchor = "introduction" if n == 0 else f"chapter-{n}"
    title = ch["title"]
    page = ch["page"]
    items = []
    for m in ch["moments"]:
        ep = episodes[m["episode"]]
        t = max(0, m["t"] - 2)
        url = f"https://www.youtube.com/watch?v={esc(ep['youtube'])}&amp;t={t}s"
        items.append(
            f'                <li><a class="ts" href="{url}">{clock(m["t"])}</a> {esc(m["note"])}'
            f' <span class="moment-source">· <a href="conversations.html#ep-{ep["number"]}">#{ep["number"]}</a>'
            f' {esc(who(ep))}</span></li>\n')
    return f"""          <li class="episode chapter" id="{anchor}">
            <p class="ep-num">{label}</p>
            <div class="ep-body">
              <h2 class="chapter-title">{esc(title)}</h2>
              <p>{esc(ch["summary"])}</p>
              <p class="meta"><a href="{pdf}#page={page + offset}">Read it in the PDF</a>, from page {page}</p>
              <ul class="moments">
{"".join(items)}              </ul>
            </div>
          </li>
"""


def main():
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    episodes = {e["number"]: e for e in json.loads(EPISODES.read_text(encoding="utf-8"))["episodes"]}
    pdf, offset = guide["pdf"], guide["page_offset"]
    count = sum(len(c["moments"]) for c in guide["chapters"])
    eps = len({m["episode"] for c in guide["chapters"] for m in c["moments"]})

    parts = [HEAD]
    parts.append(f"""        <p>
          Matthew Smith and I turned more than sixty conversations into a book,
          <em>The Existential Files</em> (<a href="{pdf}">PDF</a> <span class="sep">|</span> <a href="{EPUB}">EPUB</a>).
          This guide goes through it chapter by chapter and points to the moments in the recordings each one
          draws on: {count} of them, from {eps} episodes. The times open the video at that point; the episode
          numbers lead to the <a href="conversations.html">Conversations</a> page, where you can also search
          everything that was said.
        </p>
        <ul class="chapter-contents">
""")
    for ch in guide["chapters"]:
        anchor = "introduction" if ch["n"] == 0 else f"chapter-{ch['n']}"
        num = "" if ch["n"] == 0 else f'<span class="ep-num">{ch["n"]}</span> '
        parts.append(f'          <li>{num}<a href="#{anchor}">{esc(ch["title"])}</a></li>\n')
    parts.append("        </ul>\n")
    parts.append('        <ol class="episode-list chapter-list">\n')
    parts.extend(chapter_html(ch, episodes, pdf, offset) for ch in guide["chapters"])
    parts.append("        </ol>\n")
    parts.append(FOOT.replace("{script}", ""))
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(guide['chapters'])} chapters and {count} moments")


if __name__ == "__main__":
    main()
