import datetime
import re
from dataclasses import dataclass

from hrabal import HrabalError


@dataclass
class Names:
    months: list[str]  # %B, the form used inside a date: "1. května"
    standalone_months: list[str]  # %OB, the month on its own: "květen"
    short_months: list[str]  # %b
    days: list[str]  # %A, starting on Monday
    short_days: list[str]  # %a


# our own names instead of the system locales, which are rarely installed and change the whole process
NAMES = {
    "en": Names(
        months=[
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        standalone_months=[
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        short_months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        short_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    ),
    "cs": Names(
        months=[
            "ledna", "února", "března", "dubna", "května", "června",
            "července", "srpna", "září", "října", "listopadu", "prosince",
        ],
        standalone_months=[
            "leden", "únor", "březen", "duben", "květen", "červen",
            "červenec", "srpen", "září", "říjen", "listopad", "prosinec",
        ],
        short_months=["led", "úno", "bře", "dub", "kvě", "čvn", "čvc", "srp", "zář", "říj", "lis", "pro"],
        days=["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"],
        short_days=["po", "út", "st", "čt", "pá", "so", "ne"],
    ),
}  # fmt: skip

# %B, %OB, %-d and friends: a minus drops the leading zero, O asks for the standalone month
DIRECTIVE = re.compile(r"%(-?)(O?)([a-zA-Z%])")


def format_date(value: datetime.date, format: str, locale: str) -> str:
    language = locale.replace("-", "_").split("_")[0].lower()  # "cs", "cs_CZ" and "cs-CZ" all mean Czech
    names = NAMES.get(language)
    if names is None:
        raise HrabalError(f"no month and day names for '{locale}', hrabal knows {', '.join(NAMES)}")

    def replace(match: re.Match) -> str:
        no_padding, standalone, letter = match.groups()
        if letter == "B":
            return (names.standalone_months if standalone else names.months)[value.month - 1]
        if letter == "b":
            return names.short_months[value.month - 1]
        if letter == "A":
            return names.days[value.weekday()]
        if letter == "a":
            return names.short_days[value.weekday()]

        text = value.strftime("%" + letter)
        return (text.lstrip("0") or "0") if no_padding else text

    return DIRECTIVE.sub(replace, format)
