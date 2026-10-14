"""Turn one of the site's LaTeX-made PDFs back into Markdown for pandoc.

Used by make_epubs.py. Reads `pdftohtml -xml` output, which keeps each text
run's position and font, so paragraphs, headings, italics, quotations,
attributions, verse and footnotes can be rebuilt.

    pdftohtml -xml -i -q book.pdf book
    python3 tools/pdf2md.py book.xml FIRST_PAGE > book.md

FIRST_PAGE skips the title and contents pages. Line-end hyphens are removed
unless the hyphenated word appears elsewhere in the book or the joined word
isn't a word (checked with the optional `wordfreq` package).
"""
import html
import re
import sys
from collections import Counter

try:
    from wordfreq import zipf_frequency
except ImportError:  # without it, line-end hyphens are simply removed
    def zipf_frequency(word, lang):
        return 1

xml_path, first_page = sys.argv[1], int(sys.argv[2])
src = open(xml_path, encoding="utf-8").read()

fonts = {}
for fid, size, fam in re.findall(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)"', src):
    fonts[fid] = {"size": int(size), "italic": bool(re.search(r"Italic|SFTI", fam)),
                  "bold": bool(re.search(r"Bold|SFBX", fam))}

pages = []
for num, body in re.findall(r'<page number="(\d+)"[^>]*>(.*?)</page>', src, re.S):
    if int(num) < first_page:
        continue
    runs = []
    for top, left, width, height, font, text in re.findall(
            r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)" font="(\d+)">(.*?)</text>', body):
        italic = fonts[font]["italic"] or "<i>" in text
        bold = fonts[font]["bold"] or "<b>" in text
        text = html.unescape(re.sub(r"</?[ib]>", "", text))
        runs.append(dict(top=int(top), left=int(left), right=int(left) + int(width),
                         bottom=int(top) + int(height), size=fonts[font]["size"],
                         italic=italic, bold=bold, text=text))
    pages.append((int(num), runs))


def spaced(rs):
    parts, prev = [], None
    for r in rs:
        if prev is not None and r["left"] > prev["right"] + 1 and parts and not parts[-1].endswith(" ") and not r["text"].startswith(" "):
            parts.append(" ")
        parts.append(r["text"])
        prev = r
    return "".join(parts).strip()


def group_lines(runs):
    lines = []
    for r in sorted(runs, key=lambda r: (r["bottom"], r["left"])):
        for ln in lines:
            if abs(ln["bottom"] - r["bottom"]) <= 5:
                ln["runs"].append(r)
                break
        else:
            lines.append({"bottom": r["bottom"], "runs": [r]})
    out = []
    for ln in sorted(lines, key=lambda l: l["bottom"]):
        rs = sorted(ln["runs"], key=lambda r: r["left"])
        size = Counter(r["size"] for r in rs if r["text"].strip()).most_common(1)[0][0] if any(r["text"].strip() for r in rs) else 0
        out.append(dict(top=min(r["top"] for r in rs), bottom=ln["bottom"], left=rs[0]["left"],
                        right=max(r["right"] for r in rs), size=size, runs=rs,
                        bold=all(r["bold"] for r in rs if r["text"].strip()),
                        italic=all(r["italic"] for r in rs if r["text"].strip()),
                        plain=spaced(rs)))
    return out


def md_text(line):
    """Line text with *italics*, spaces restored between runs."""
    parts, prev = [], None
    for r in line["runs"]:
        t = r["text"].replace("*", r"\*").replace("_", r"\_")
        if prev is not None and r["left"] > prev["right"] + 1 and not parts[-1].endswith(" ") and not t.startswith(" "):
            parts.append(" ")
        if r["italic"] and not line["italic"] and t.strip():
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            t = f"{lead}*{t.strip()}*{trail}"
        parts.append(t)
        prev = r
    return "".join(parts).strip()


BODY_SIZE = Counter(l["size"] for _, runs in pages for l in group_lines(runs)).most_common(1)[0][0]

def typical_right(lines, default):
    """The justified right edge: the most common right edge of long lines."""
    rights = Counter(l["right"] for l in lines if l["right"] - l["left"] > 250)
    if not rights:
        return default
    top = max(rights.values())
    return max(r for r, c in rights.items() if c >= top / 2 and r <= min(rights, key=lambda x: -rights[x]) + 6)


# Classify every line into a stream of (kind, text, info).
stream = []
for num, runs in pages:
    lines = group_lines(runs)
    body = [l for l in lines if l["size"] == BODY_SIZE and l["left"] < 100]
    margin = min((l["left"] for l in body), default=76)
    body_right = typical_right(body, 554)
    quote = [l for l in lines if l["size"] == BODY_SIZE and 110 <= l["left"] <= 130]
    quote_right = typical_right(quote, 509)
    prev_bottom = None
    for l in lines:
        text = l["plain"]
        if not text:
            continue
        # Page numbers and running heads.
        if re.fullmatch(r"[0-9]+|[ivxlc]+", text) and (l["top"] < 60 or l["top"] > 820):
            continue
        gap = (l["top"] - prev_bottom) if prev_bottom is not None else 0
        prev_bottom = l["bottom"]
        if re.fullmatch(r"\*( \*)+|\*\s*\*\s*\*", text) or text.replace(" ", "") == "***":
            stream.append(("break", "", {}))
            continue
        if l["size"] >= 30:
            stream.append(("h1", text, {}))
            continue
        if l["size"] >= 20 and l["bold"]:
            stream.append(("h2", text, {}))
            continue
        if text.startswith("—") and l["italic"]:
            stream.append(("attrib", md_text(l), {}))
            continue
        if l["size"] != BODY_SIZE:
            if re.fullmatch(r"\d+", text):
                stream.append(("fnmark", text, {}))
            elif l["size"] < BODY_SIZE - 2 and l["top"] > 700:
                stream.append(("fntext", md_text(l), {}))
            else:
                stream.append(("small", md_text(l), {"gap": gap, "short": True}))
            continue
        if 110 <= l["left"] <= 130:
            stream.append(("quote", md_text(l), {"gap": gap, "short": l["right"] < quote_right - 12}))
            continue
        if l["left"] > 200:
            stream.append(("sign", md_text(l), {}))
            continue
        indent = l["left"] >= margin + 15
        stream.append(("p", md_text(l), {"gap": gap, "indent": indent, "short": l["right"] < body_right - 12}))

# Words seen anywhere, to decide whether a line-end hyphen is real.
all_text = " ".join(t for _, t, _ in stream)
hyphenated = set(re.findall(r"\b[\w’']+-[\w’']+\b", all_text))
words = Counter(re.findall(r"[\w’']+", all_text.lower()))


def join(a, b):
    if not a:
        return b
    # A hyphenated word broken across two italic runs: "Associ-*" + "*ation*"
    if re.search(r"[A-Za-z]-\*$", a) and b.startswith("*") and b[1:2].islower():
        return join(a[:-1], b[1:])
    if re.search(r"[A-Za-z]-$", a) and b[:1].isupper():
        return a + b
    m = re.search(r"([\w’']+)-$", a)
    if m and b[:1].islower():
        first = m.group(1)
        nxt = re.match(r"[\w’']+", b)
        second = nxt.group(0) if nxt else ""
        if f"{first}-{second}" in hyphenated:
            return a + b
        z = lambda w: zipf_frequency(w.lower(), "en")
        if z(first + second) == 0 and z(first) > 2 and z(second) > 2:
            return a + b
        return a[:-1] + b
    if a.endswith("—") and not a.endswith(" —"):
        return a + b
    if a.endswith("/"):
        return a + b
    return a + " " + b


def tidy(s):
    s = re.sub(r"\.\s?\.\s?\.", "…", s)
    s = re.sub(r"\*(\s+)\*", r"\1", s)           # *The Existential* *Files* -> one span
    s = re.sub(r"\*\*", "", s)                     # adjacent italic runs
    s = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", s)     # not a numbered list
    s = re.sub(r"^([-+>#])", r"\\\1", s)
    return s


# Build Markdown blocks.
out, para, kind_open, quote_buf, sign_buf, h1_buf, list_mode = [], "", None, "", [], [], False


def flush_para():
    global para
    if para:
        out.append(tidy(para) + "\n")
        para = ""


def flush_h1():
    global h1_buf
    if h1_buf:
        title = ""
        for t in h1_buf:
            title = join(title, t)
        m = re.match(r"Chapter (\d+)$", h1_buf[0])
        if m and len(h1_buf) > 1:
            rest = ""
            for t in h1_buf[1:]:
                rest = join(rest, t)
            title = f"Chapter {m.group(1)}: {rest}"
        out.append(f"# {title}\n")
        h1_buf = []


def flush_quote():
    global quote_buf, quote_short
    quote_short = False
    if quote_buf:
        out.append(tidy(quote_buf) + "\n")
        quote_buf = ""


in_quote_div = False
last_short = True
quote_short = False
footnote_no, footnotes = [0], {}
section = ""
ENTRY = re.compile(r"^[A-Z][\w’'.-]+(?: [A-Z][\w’'.-]+)*(?:, [^.]{1,60})?\.(?: |$)")
for kind, text, info in stream:
    if kind != "h1":
        flush_h1()
    if kind != "sign" and sign_buf:
        flush_para()
        out.append("::: signature\n" + "\n".join(f"| {s}" for s in sign_buf) + "\n:::\n")
        sign_buf = []
    if kind == "h1":
        flush_para(); flush_quote()
        if in_quote_div:
            out.append(":::\n"); in_quote_div = False
        h1_buf.append(text)
        list_mode = text.startswith("Index of")
        section = text
        continue
    if kind == "h2":
        flush_para(); flush_quote()
        if in_quote_div:
            out.append(":::\n"); in_quote_div = False
        out.append(f"## {tidy(text)}\n")
        last_short = True
        continue
    if kind == "break":
        flush_para()
        out.append("* * *\n")
        last_short = True
        continue
    if kind == "quote":
        flush_para()
        if not in_quote_div:
            out.append("::: quotation\n"); in_quote_div = True
        if quote_buf and (info["gap"] > 14):
            flush_quote()
        if quote_buf and quote_short:
            quote_buf += "\\\n" + text          # verse: keep the line break
        else:
            quote_buf = join(quote_buf, text)
        quote_short = info["short"]
        continue
    if kind == "fnmark":
        if out and out[-2:-1] and out[-1] == ":::\n" and "{.attribution}" in out[-2]:
            footnote_no[0] += 1
            out[-2] = out[-2].replace("]{.attribution}", f"[^{footnote_no[0]}]]{{.attribution}}")
        continue
    if kind == "fntext":
        footnotes.setdefault(footnote_no[0], "")
        footnotes[footnote_no[0]] = join(footnotes[footnote_no[0]], text)
        continue
    if kind == "attrib":
        flush_para()
        flush_quote()
        if not in_quote_div:
            out.append("::: quotation\n")
        out.append(f"[{tidy(text)}]{{.attribution}}\n")
        out.append(":::\n")
        in_quote_div = False
        continue
    if kind == "sign":
        flush_para()
        sign_buf.append(text)
        continue
    if sign_buf:
        out.append("::: signature\n" + "\n".join(f"| {s}" for s in sign_buf) + "\n:::\n")
        sign_buf = []
    if kind == "small" and list_mode:
        flush_para()
        out.append(f"- {tidy(text)}")
        continue
    # body paragraph line
    new = info.get("indent") or last_short or info.get("gap", 0) > 14
    if section.startswith("Sources") and para.endswith((".", ".”")) and ENTRY.match(text):
        new = True
    if new:
        flush_para()
    para = join(para, text)
    last_short = info.get("short", False)

flush_h1(); flush_para(); flush_quote()
if sign_buf:
    out.append("::: signature\n" + "\n".join(f"| {s}" for s in sign_buf) + "\n:::\n")
if in_quote_div:
    out.append(":::\n")

md = "\n".join(out)
for k, v in footnotes.items():
    md += f"\n\n[^{k}]: {tidy(v)}\n"
md = re.sub(r"(\n- [^\n]+)\n\n(?=- )", r"\1\n", md)  # keep list items together
print(md)
