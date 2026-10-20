import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from hrabal import HrabalError


@dataclass
class Config:
    base_url: str
    title: str = ""
    description: str = ""
    language: str = "en"
    taxonomies: list[str] = field(default_factory=list)
    highlight_code: bool = True
    highlight_theme: str = "monokai"
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

    return Config(**data)
