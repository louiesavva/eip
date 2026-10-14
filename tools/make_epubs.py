#!/usr/bin/env python3
"""Make EPUB editions of the books from their PDFs.

The PDFs are the masters. This rebuilds an EPUB next to each one, so run it
again whenever a PDF changes, then commit the PDF and the EPUB together.

    python3 tools/make_epubs.py            # all books
    python3 tools/make_epubs.py against    # just the ones whose file name matches

Needs pdftohtml (poppler-utils) and pandoc. The Python package `wordfreq`
improves the repair of words hyphenated across lines, but is optional:
    pip install wordfreq
"""

import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
ASSETS = ROOT / "assets"
SITE = "https://everythingispointless.com"

BOOKS = [
    {
        "pdf": "Against_Certainty_LouieSavva.pdf",
        "first_page": 5,  # after the title page and contents
        "cover": "against-certainty-cover.jpg",
        "title": "Against Certainty",
        "subtitle": "Quotations on Chance, Science, Error, and Wonder",
        "authors": ["Dr Louie Savva"],
        "lang": "en",
        "date": "2026-04-09",
        "rights": None,
        "afterword": (
            f"This ebook was made from the PDF edition of *Against Certainty*. "
            f"Both are free at [everythingispointless.com]({SITE}/#books)."
        ),
    },
    {
        "pdf": "the_existential_files.pdf",
        "first_page": 5,
        "cover": "the-existential-files-cover.jpg",
        "title": "The Existential Files",
        "subtitle": "A Guide to Living in a Meaningless Universe",
        "authors": ["Dr Louie Savva", "Dr Matthew Smith"],
        "lang": "en-GB",
        "date": "2026-04-09",
        "rights": "Copyright © Dr Louie Savva and Dr Matthew Smith. All rights reserved.",
        "afterword": (
            f"This ebook was made from the PDF edition of *The Existential Files*. "
            f"Both are free at [everythingispointless.com]({SITE}/#books).\n\n"
            f"The book grew out of sixty-two recorded conversations. To hear the moments each "
            f"chapter draws on, see the [chapter guide]({SITE}/book-guide.html), or "
            f"[search everything that was said]({SITE}/conversations.html)."
        ),
    },
]


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def metadata(book):
    lines = [
        "title:",
        "  - type: main",
        f"    text: {yaml_str(book['title'])}",
        "  - type: subtitle",
        f"    text: {yaml_str(book['subtitle'])}",
        "creator:",
    ]
    for a in book["authors"]:
        lines += ["  - role: author", f"    text: {yaml_str(a)}"]
    ident = uuid.uuid5(uuid.NAMESPACE_URL, f"{SITE}/assets/{book['pdf']}")
    lines += [
        f"identifier: urn:uuid:{ident}",
        f"lang: {book['lang']}",
        f"date: {book['date']}",
    ]
    if book["rights"]:
        lines.append(f"rights: {yaml_str(book['rights'])}")
    return "\n".join(lines) + "\n"


def build(book):
    pdf = ASSETS / book["pdf"]
    out = pdf.with_suffix(".epub")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        subprocess.run(["pdftohtml", "-xml", "-i", "-q", str(pdf), str(tmp / "book")], check=True)
        md = subprocess.run(
            [sys.executable, str(TOOLS / "pdf2md.py"), str(tmp / "book.xml"), str(book["first_page"])],
            check=True, capture_output=True, text=True).stdout
        md += "\n# About this edition {.unnumbered .afterword}\n\n" + book["afterword"] + "\n"
        (tmp / "book.md").write_text(md, encoding="utf-8")
        (tmp / "meta.yaml").write_text(metadata(book), encoding="utf-8")
        subprocess.run([
            "pandoc", str(tmp / "book.md"), "--from", "markdown", "--to", "epub3",
            "--metadata-file", str(tmp / "meta.yaml"),
            "--css", str(TOOLS / "epub.css"),
            "--epub-cover-image", str(ASSETS / book["cover"]),
            "--toc-depth", "1", "--split-level", "1",
            "-o", str(out),
        ], check=True)
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def main():
    wanted = [a.lower() for a in sys.argv[1:]]
    for book in BOOKS:
        if not wanted or any(w in book["pdf"].lower() for w in wanted):
            build(book)


if __name__ == "__main__":
    main()
