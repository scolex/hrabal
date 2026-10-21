# Simple internationalization: one language per site. hrabal brings its own strings for a few
# languages in hrabal/translations/, and a site adds or overrides strings under [translations.<language>]
# in config.toml. Whatever is missing stops the build and says where to add it.

import tomllib
from pathlib import Path

from hrabal import HrabalError

BUILT_IN = Path(__file__).parent / "translations"


def base_language(language: str) -> str:
    # "cs", "cs_CZ" and "cs-CZ" all mean Czech
    return language.replace("-", "_").split("_")[0].lower()


class Translations:
    def __init__(self, language: str, site: dict[str, dict] | None = None):
        self.language = base_language(language)
        built_in = BUILT_IN / f"{self.language}.toml"
        self.strings = tomllib.loads(built_in.read_text(encoding="utf-8")) if built_in.exists() else {}
        for name, strings in (site or {}).items():
            if base_language(name) == self.language:
                self.strings.update(strings)

    def __getitem__(self, key: str):
        if key not in self.strings:
            raise HrabalError(
                f"no translation for '{key}' in '{self.language}', add it under [translations.{self.language}]"
                " in config.toml"
            )
        return self.strings[key]


ENGLISH = Translations("en")  # what feeds use for their dates, whatever the site's language is
