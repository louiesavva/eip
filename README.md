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
- **Conversations** (`conversations.html`): an index of *The Existential Files* podcast episodes, with a search across the episode transcripts
- **Chapter guide** (`book-guide.html`): which moments in the conversations each chapter of *The Existential Files* draws on
- **Selected essays**, including:
  - *When Syntax Becomes Skin*
- **Books**, each as a PDF and an EPUB
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

The transcript search on the Conversations page is the only JavaScript on the site, and it is optional:
without JavaScript the search box simply doesn't appear and the episode list works as before. The search
reads `data/search-index.json`, built from YouTube's automatic captions:

```sh
yt-dlp --skip-download --write-auto-subs --sub-langs "en.*" --convert-subs srt --sleep-subtitles 5 \
    -o "%(id)s" "https://www.youtube.com/@LouieSavva/videos"
python3 tools/build_search_index.py path/to/srt-folder
python3 tools/build_conversations.py
```

The chapter guide is generated the same way, from `data/book-guide.json`, where each moment is an
episode number, a time in seconds and a short note:

```sh
python3 tools/build_book_guide.py
```

The EPUBs of *Against Certainty* and *The Existential Files* are made from their PDFs, which stay the
masters. After replacing a PDF, rebuild its EPUB and commit both (needs `pdftohtml` from poppler-utils
and `pandoc`; `pip install wordfreq` helps repair words hyphenated across lines):

```sh
python3 tools/make_epubs.py            # or: python3 tools/make_epubs.py against
```

## Structure

```text
.
├── index.html
├── conversations.html        (generated; edit data/episodes.json)
├── book-guide.html           (generated; edit data/book-guide.json)
├── style.css
├── essays/
│   └── when-syntax-becomes-skin.html
├── data/
│   ├── episodes.json
│   ├── book-guide.json
│   └── search-index.json     (generated from captions)
├── tools/
│   ├── build_conversations.py
│   ├── build_book_guide.py
│   ├── build_search_index.py
│   ├── make_epubs.py         (EPUBs from the PDFs)
│   ├── pdf2md.py
│   └── epub.css
└── assets/
    ├── search.js
    ├── og-image.jpg
    ├── EverythingIsPointless_LouieSavva.pdf
    ├── EverythingIsPointless_LouieSavva.epub
    ├── Against_Certainty_LouieSavva.pdf
    ├── Against_Certainty_LouieSavva.epub   (generated from the PDF)
    ├── the_existential_files.pdf
    └── the_existential_files.epub          (generated from the PDF)
```
