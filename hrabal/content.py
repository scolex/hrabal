import datetime
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from hrabal import HrabalError
from hrabal.dates import as_moment

PAGE_KEYS = {
    "title",
    "description",
    "date",
    "updated",
    "slug",
    "weight",
    "draft",
    "template",
    "search",
    "taxonomies",
    "extra",
}
SECTION_KEYS = {
    "title",
    "description",
    "weight",
    "draft",
    "sort_by",
    "template",
    "page_template",
    "paginate_by",
    "paginate_path",
    "paginate_reversed",
    "generate_feeds",
    "extra",
}
SORT_OPTIONS = ("date", "title", "weight", "none")
DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})[_-](.+)")


@dataclass(eq=False)
class Page:
    file: Path
    slug: str
    path: str
    permalink: str
    title: str = ""
    description: str = ""
    date: datetime.date | None = None
    updated: datetime.date | None = None  # the last edit: from the front matter, or else the file's modification date
    weight: int = 0
    template: str = "page.html"
    search: bool = True  # false keeps the page out of search_index.json
    taxonomies: dict[str, list[str]] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    raw_content: str = field(default="", repr=False)
    content: str = field(default="", repr=False)
    summary: str = field(default="", repr=False)
    heading_ids: list[str] = field(default_factory=list, repr=False)  # the ids links can point to with #
    has_mermaid: bool = False  # so a template loads mermaid only where a diagram needs it
    assets: list[Path] = field(default_factory=list)
    previous: Page | None = field(default=None, repr=False)
    next: Page | None = field(default=None, repr=False)
    ancestors: list[Section] = field(default_factory=list, repr=False)  # the sections above, the home page first

    def last_changed(self) -> datetime.date | None:
        # the later of date and updated, what sitemaps and feeds call the last update
        moments = [moment for moment in (self.date, self.updated) if moment]
        return max(moments, key=as_moment) if moments else None


@dataclass(eq=False)
class Section:
    file: Path
    path: str
    permalink: str
    title: str = ""
    description: str = ""
    weight: int = 0
    sort_by: str = "date"
    template: str = "section.html"
    page_template: str = "page.html"
    paginate_by: int = 0  # 0 means one long list, no pagination
    paginate_path: str = "page"
    paginate_reversed: bool = False
    generate_feeds: bool = False  # a feed of just this section's pages
    extra: dict = field(default_factory=dict)
    raw_content: str = field(default="", repr=False)
    content: str = field(default="", repr=False)
    heading_ids: list[str] = field(default_factory=list, repr=False)
    has_mermaid: bool = False
    pages: list[Page] = field(default_factory=list, repr=False)
    subsections: list[Section] = field(default_factory=list, repr=False)
    ancestors: list[Section] = field(default_factory=list, repr=False)


@dataclass(eq=False)
class Term:
    name: str
    slug: str
    path: str
    permalink: str
    pages: list[Page] = field(default_factory=list, repr=False)


@dataclass(eq=False)
class Taxonomy:
    name: str
    path: str
    permalink: str
    paginate_by: int = 0  # for the term pages, the list of all terms is never paginated
    paginate_path: str = "page"
    feed: bool = False
    terms: dict[str, Term] = field(default_factory=dict, repr=False)


def read_markdown(file: Path, allowed_keys: set[str]) -> tuple[dict, str]:
    text = file.read_text(encoding="utf-8")
    if not text.startswith("+++"):
        return {}, text

    parts = text.split("+++", 2)
    if len(parts) < 3:
        raise HrabalError(f"{file}: front matter is missing the closing +++")

    try:
        meta = tomllib.loads(parts[1])
    except tomllib.TOMLDecodeError as e:
        raise HrabalError(f"{file}: {e}") from None

    unknown = meta.keys() - allowed_keys
    if unknown:
        raise HrabalError(f"{file}: unknown front matter {', '.join(sorted(unknown))} (put your own under [extra])")

    return meta, parts[2]


def sort_pages(pages: list[Page], sort_by: str) -> list[Page]:
    if sort_by == "date":
        # isoformat() lets plain dates and datetimes sort together, undated pages end up last
        return sorted(pages, key=lambda p: p.date.isoformat() if p.date else "", reverse=True)
    if sort_by == "title":
        return sorted(pages, key=lambda p: p.title.casefold())
    if sort_by == "weight":
        return sorted(pages, key=lambda p: p.weight)
    return pages


def split_date(name: str) -> tuple[datetime.date | None, str]:
    # "2016-10-08_a-post" -> (2016-10-08, "a-post"), a dash works as the separator too
    match = DATE_IN_NAME.fullmatch(name)
    if not match:
        return None, name
    try:
        return datetime.date.fromisoformat(match[1]), match[2]
    except ValueError:
        return None, name  # looks like a date, but isn't one, like 2016-13-45


def slugify(text: str) -> str:
    # "Příliš hlučná samota" -> "prilis-hlucna-samota"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
