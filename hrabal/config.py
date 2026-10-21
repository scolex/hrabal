import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from hrabal import HrabalError
from hrabal.anchors import ANCHOR_LINKS


@dataclass
class TaxonomyConfig:
    name: str
    paginate_by: int = 0
    paginate_path: str = "page"
    feed: bool = False  # an atom.xml (or whatever feed_filenames says) for every term


@dataclass
class MenuItem:
    title: str
    url: str  # @/about.md, /tags/ or a whole https:// address


@dataclass
class ThemeConfig:
    # settings of hrabal's own look, the [theme] table in config.toml
    menu: list[MenuItem] = field(default_factory=list)
    home_posts: str = ""  # the section whose newest posts the home page lists, like "blog/_index.md"
    icon: str = "icon.svg"  # a file in static/, shown before the title and as the favicon, "" for none
    copyright_since: int = 0  # the first year in the footer, 0 shows just this year
    breadcrumbs: bool = False  # the sections above a page, over its heading


@dataclass
class LinkCheckerConfig:
    # for hrabal check, the [link_checker] table like in Zola
    skip_prefixes: list[str] = field(default_factory=list)  # links starting with one of these aren't checked


@dataclass
class Config:
    base_url: str
    title: str = ""
    description: str = ""
    author: str = ""
    language: str = "en"
    taxonomies: list[TaxonomyConfig] = field(default_factory=list)
    highlight_code: bool = True
    highlight_theme: str = "monokai"
    insert_anchor_links: str = "none"  # or left, right, heading: a link next to or around every heading
    generate_sitemap: bool = True
    generate_robots_txt: bool = True
    generate_feeds: bool = False
    feed_filenames: list[str] = field(default_factory=lambda: ["atom.xml"])
    feed_limit: int = 0  # 0 puts every page with a date in the feed
    build_search_index: bool = False
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    link_checker: LinkCheckerConfig = field(default_factory=LinkCheckerConfig)
    translations: dict[str, dict] = field(default_factory=dict)  # [translations.cs] and so on, see i18n.py
    extra: dict = field(default_factory=dict)


def load_config(file: Path) -> Config:
    if not file.exists():
        raise HrabalError(f"{file} not found, is this a hrabal site?")

    try:
        data = tomllib.loads(file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise HrabalError(f"{file}: {e}") from None

    check_keys(file, data, Config, "keys", hint=" (put your own under [extra])")
    if "base_url" not in data:
        raise HrabalError(f"{file}: base_url is required")

    data["taxonomies"] = [load_taxonomy(file, entry) for entry in data.get("taxonomies", [])]
    data["theme"] = load_theme(file, data.get("theme", {}))
    data["link_checker"] = load_link_checker(file, data.get("link_checker", {}))
    config = Config(**data)
    if not all(isinstance(strings, dict) for strings in config.translations.values()):
        raise HrabalError(f"{file}: translations go in a table per language, like [translations.cs]")
    if config.insert_anchor_links not in ANCHOR_LINKS:
        raise HrabalError(f"{file}: insert_anchor_links must be one of {', '.join(ANCHOR_LINKS)}")
    if not isinstance(config.feed_limit, int) or config.feed_limit < 0:
        raise HrabalError(f"{file}: feed_limit must be a positive number, or 0 for no limit")
    return config


def check_keys(file: Path, table: dict, settings, what: str, hint: str = ""):
    # settings is the dataclass the table turns into, its fields are the keys it may have
    unknown = table.keys() - {f.name for f in fields(settings)}
    if unknown:
        raise HrabalError(f"{file}: unknown {what} {', '.join(sorted(unknown))}{hint}")


def load_theme(file: Path, table) -> ThemeConfig:
    if not isinstance(table, dict):
        raise HrabalError(f"{file}: theme settings go in a [theme] table")
    check_keys(file, table, ThemeConfig, "theme settings")

    menu = []
    for item in table.get("menu", []):
        if not isinstance(item, dict) or item.keys() != {"title", "url"}:
            raise HrabalError(
                f'{file}: every menu item needs a title and a url, like {{ title = "Blog", url = "/blog/" }}'
            )
        menu.append(MenuItem(**item))
    if not isinstance(table.get("breadcrumbs", False), bool):
        raise HrabalError(f"{file}: breadcrumbs is either true or false")
    return ThemeConfig(**(table | {"menu": menu}))


def load_link_checker(file: Path, table) -> LinkCheckerConfig:
    if not isinstance(table, dict):
        raise HrabalError(f"{file}: link checker settings go in a [link_checker] table")
    check_keys(file, table, LinkCheckerConfig, "link checker settings")
    skip = table.get("skip_prefixes", [])
    if not isinstance(skip, list) or not all(isinstance(prefix, str) for prefix in skip):
        raise HrabalError(f'{file}: skip_prefixes is a list of addresses, like ["https://example.com/"]')
    return LinkCheckerConfig(skip)


def load_taxonomy(file: Path, entry: str | dict) -> TaxonomyConfig:
    # either just a name, or a table with settings: {name = "tags", paginate_by = 10}
    if isinstance(entry, str):
        return TaxonomyConfig(entry)
    if not isinstance(entry, dict):
        raise HrabalError(f'{file}: a taxonomy is a name or a table, like {{ name = "tags", paginate_by = 10 }}')

    check_keys(file, entry, TaxonomyConfig, "taxonomy settings")
    if "name" not in entry:
        raise HrabalError(f"{file}: every taxonomy needs a name")

    taxonomy = TaxonomyConfig(**entry)
    if not isinstance(taxonomy.paginate_by, int) or taxonomy.paginate_by < 0:
        raise HrabalError(f"{file}: paginate_by of {taxonomy.name} must be a positive number")
    return taxonomy
