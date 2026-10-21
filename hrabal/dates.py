import datetime
import re

from hrabal.i18n import ENGLISH, Translations

# %B, %OB, %-d and friends: a minus drops the leading zero, O asks for the standalone month
DIRECTIVE = re.compile(r"%(-?)(O?)([a-zA-Z%])")


def format_date(value: datetime.date, format: str, translations: Translations) -> str:
    # month and day names come from the translations, not from the system locales,
    # which are rarely installed and switch the whole process; they're only looked up when the format needs them
    def replace(match: re.Match) -> str:
        no_padding, standalone, letter = match.groups()
        if letter == "B":
            return translations["standalone_months" if standalone else "months"][value.month - 1]
        if letter == "b":
            return translations["short_months"][value.month - 1]
        if letter == "A":
            return translations["days"][value.weekday()]
        if letter == "a":
            return translations["short_days"][value.weekday()]

        text = value.strftime("%" + letter)
        return (text.lstrip("0") or "0") if no_padding else text

    return DIRECTIVE.sub(replace, format)


def as_moment(value: datetime.date) -> datetime.datetime:
    # feeds want a full moment in time: a plain date counts as midnight, a time without a zone as UTC
    if not isinstance(value, datetime.datetime):
        value = datetime.datetime.combine(value, datetime.time())
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.UTC)
    return value


def rfc3339(value: datetime.date | None) -> str:
    # for Atom: 2024-05-01T00:00:00+00:00
    return as_moment(value).isoformat() if value else ""


def rfc822(value: datetime.date | None) -> str:
    # for RSS: Wed, 01 May 2024 00:00:00 +0000, always with English names whatever the site's language is
    return format_date(as_moment(value), "%a, %d %b %Y %H:%M:%S %z", ENGLISH) if value else ""
