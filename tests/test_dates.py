import datetime

import pytest

from hrabal import HrabalError
from hrabal.dates import format_date

# a Wednesday
DAY = datetime.date(2017, 3, 1)


@pytest.mark.parametrize(
    "format, locale, expected",
    [
        ("%d %B %Y", "en", "01 March 2017"),
        ("%-d. %B %Y", "cs", "1. března 2017"),
        ("%OB %Y", "cs", "březen 2017"),
        ("%-d. %-m. %Y", "cs", "1. 3. 2017"),
        ("%A %-d. %b", "cs", "středa 1. bře"),
        ("%a, %d %b %Y", "en", "Wed, 01 Mar 2017"),
        ("%a %-d.", "cs", "st 1."),
        ("%Y-%m-%d", "cs", "2017-03-01"),
        ("100 %% sure", "en", "100 % sure"),
    ],
)
def test_format_date(format, locale, expected):
    assert format_date(DAY, format, locale) == expected


@pytest.mark.parametrize("locale", ["cs", "cs_CZ", "cs-CZ", "CS"])
def test_locale_can_carry_a_country(locale):
    assert format_date(DAY, "%B", locale) == "března"


def test_all_czech_months_in_a_date():
    months = [format_date(datetime.date(2024, month, 1), "%B", "cs") for month in range(1, 13)]
    assert months == [
        "ledna", "února", "března", "dubna", "května", "června",
        "července", "srpna", "září", "října", "listopadu", "prosince",
    ]  # fmt: skip


def test_times_work_too():
    moment = datetime.datetime(2024, 5, 1, 9, 5)
    assert format_date(moment, "%-d. %B %Y, %-H:%M", "cs") == "1. května 2024, 9:05"


def test_unknown_locale_is_an_error():
    with pytest.raises(HrabalError, match="no month and day names for 'de'"):
        format_date(DAY, "%B", "de")
