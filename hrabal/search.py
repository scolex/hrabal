import json
from html.parser import HTMLParser

from hrabal.content import Page

TEXT_LIMIT = 5000  # characters of text per page, plenty to find it by while the index stays small

# where words on either side shouldn't run together, unlike around <em> or a highlighted <span>
BLOCKS = {"p", "br", "li", "pre", "div", "blockquote", "table", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}


class TextOnly(HTMLParser):
    # keeps what a reader sees, minus scripts, styles and the source of mermaid diagrams
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style") or (tag == "pre" and ("class", "mermaid") in attrs):
            self.skipping += 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.skipping and tag in ("script", "style", "pre"):
            self.skipping -= 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def page_text(html: str) -> str:
    parser = TextOnly()
    parser.feed(html)
    return " ".join("".join(parser.parts).split())


def search_index(pages: list[Page]) -> str:
    entries = [
        {
            "title": page.title,
            "url": page.permalink,
            "date": page.date.isoformat()[:10] if page.date else None,
            "description": page.description,
            "tags": [term for terms in page.taxonomies.values() for term in terms],
            "text": page_text(page.content)[:TEXT_LIMIT],
        }
        for page in sorted(pages, key=lambda page: page.permalink)
        if page.search
    ]
    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
