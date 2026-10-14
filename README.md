# Everything Is Pointless

A former blog. An ongoing worldview.

This repository contains the source for **everythingispointless.com** — a small, text-led website by **Dr Louie Savva**. It serves as a front door to a non-religious existential worldview, a short foundational book, a later quotation collection, and selected essays on mortality, meaning, consciousness, finitude, humour, and the strange business of being here at all.

## What this site is

This is not a content farm, a self-help funnel, or a motivational shrine.

It is a simple website for people willing to look directly at mortality, absurdity, suffering, freedom, and the human animal without false comfort. The tone is existential, secular, unsentimental, and humane.

## Contents

The site currently includes:

- **Homepage** with:
  - About
  - Books
  - Writing (Mortality, Meaning, and selected essays)
  - Conversations
  - Resources
  - Author
  - Contact
- **Conversations** (`conversations.html`): an index of *The Existential Files* podcast episodes
- **Selected essays**, including:
  - *When Syntax Becomes Skin*
- **Books**
  - *Everything Is Pointless*
  - *Against Certainty*
  - *The Existential Files* (with Dr Matthew Smith)
- **Curated resources** linking to writers such as Kafka, Camus, Dostoevsky, Kierkegaard, Sartre, Nietzsche, Darwin, and Heidegger

## Tech

The site is intentionally simple:

- Plain **HTML**
- Plain **CSS**
- No framework
- No build step
- No database
- No JavaScript required

This keeps the site easy to edit, portable, fast, and durable.

The one exception to hand-editing is `conversations.html`, which is generated from
`data/episodes.json` by a small helper script. The generated page is committed, so the
site itself still has no build step:

```sh
python3 tools/build_conversations.py
```

To add YouTube links, export the channel's video list and pass it in:

```sh
yt-dlp --flat-playlist --print "%(id)s %(title)s" \
    "https://www.youtube.com/@LouieSavva/videos" > episodes.tsv
python3 tools/build_conversations.py --youtube episodes.tsv
```

## Structure

```text
.
├── index.html
├── conversations.html        (generated; edit data/episodes.json)
├── style.css
├── essays/
│   └── when-syntax-becomes-skin.html
├── data/
│   └── episodes.json
├── tools/
│   └── build_conversations.py
└── assets/
    ├── og-image.jpg
    ├── EverythingIsPointless_LouieSavva.pdf
    ├── EverythingIsPointless_LouieSavva.epub
    ├── Against_Certainty_LouieSavva.pdf
    └── the_existential_files.pdf
```
