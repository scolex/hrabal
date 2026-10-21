import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from hrabal import HrabalError


@dataclass
class TaxonomyConfig:
    name: str
    paginate_by: int = 0
    paginate_path: str = "page"
    feed: bool = False  # an atom.xml (or whatever feed_filenames says) for every term


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
    generate_sitemap: bool = True
    generate_feeds: bool = False
    feed_filenames: list[str] = field(default_factory=lambda: ["atom.xml"])
    feed_limit: int = 0  # 0 puts every page with a date in the feed
    build_search_index: bool = False
    extra: dict = field(default_factory=dict)


def load_config(file: Path) -> Config:
    if not file.exists():
        raise HrabalError(f"{file} not found, is this a hrabal site?")

    try:
        data = tomllib.loads(file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise HrabalError(f"{file}: {e}") from None

    known = {f.name for f in fields(Config)}
    unknown = data.keys() - known
    if unknown:
        raise HrabalError(f"{file}: unknown keys {', '.join(sorted(unknown))} (put your own under [extra])")
    if "base_url" not in data:
        raise HrabalError(f"{file}: base_url is required")

    data["taxonomies"] = [load_taxonomy(file, entry) for entry in data.get("taxonomies", [])]
    config = Config(**data)
    if not isinstance(config.feed_limit, int) or config.feed_limit < 0:
        raise HrabalError(f"{file}: feed_limit must be a positive number, or 0 for no limit")
    return config


def load_taxonomy(file: Path, entry: str | dict) -> TaxonomyConfig:
    # either just a name, or a table with settings: {name = "tags", paginate_by = 10}
    if isinstance(entry, str):
        return TaxonomyConfig(entry)

    known = {f.name for f in fields(TaxonomyConfig)}
    unknown = entry.keys() - known
    if unknown:
        raise HrabalError(f"{file}: unknown taxonomy settings {', '.join(sorted(unknown))}")
    if "name" not in entry:
        raise HrabalError(f"{file}: every taxonomy needs a name")

    taxonomy = TaxonomyConfig(**entry)
    if not isinstance(taxonomy.paginate_by, int) or taxonomy.paginate_by < 0:
        raise HrabalError(f"{file}: paginate_by of {taxonomy.name} must be a positive number")
    return taxonomy
