# Atom and RSS feeds, with the checks of Zola's can_build_feeds and a few more.
# The test site turns on both formats, a feed for the programming section and one per category.

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.site import Site

ATOM = {"a": "http://www.w3.org/2005/Atom"}


def atom_titles(file: Path) -> list[str]:
    root = ET.parse(file).getroot()
    return [entry.findtext("a:title", "", ATOM) for entry in root.findall("a:entry", ATOM)]


def rss_items(file: Path) -> list[ET.Element]:
    return ET.parse(file).getroot().findall("channel/item")


def configure(site_dir: Path, lines: str):
    config = site_dir / "config.toml"
    config.write_text(lines + "\n" + config.read_text())


def test_site_feed_has_every_dated_page_newest_first(public):
    assert atom_titles(public / "atom.xml") == [
        "Simple",  # 2017-04-01
        "Python",  # 2017-03-01
        "Rust",  # 2017-01-02, from the programming section
        "Fixed slug",  # 2017-01-01
        "Python",  # 2016-12-31, the programming one
        "Příliš žluťoučký kůň",  # 2016-12-24
        "A post with dates",  # 2016-10-08, from the file name
        "With assets",  # 2015-03-01
    ]


def test_atom_feed_describes_itself(public):
    root = ET.parse(public / "atom.xml").getroot()

    assert root.findtext("a:title", "", ATOM) == "Hrabal test site"
    assert root.findtext("a:id", "", ATOM) == "https://example.com/atom.xml"
    assert root.findtext("a:updated", "", ATOM) == "2018-01-15T00:00:00+00:00"  # python.md's edit, the latest
    assert root.findtext("a:author/a:name", "", ATOM) == "Test Author"
    self_link = root.find("a:link[@rel='self']", ATOM)
    assert self_link is not None
    assert self_link.get("href") == "https://example.com/atom.xml"


def test_atom_entries_carry_their_content(public):
    root = ET.parse(public / "atom.xml").getroot()
    python = root.findall("a:entry", ATOM)[1]

    assert python.findtext("a:id", "", ATOM) == "https://example.com/posts/python/"
    assert python.findtext("a:published", "", ATOM) == "2017-03-01T00:00:00+00:00"
    assert python.findtext("a:updated", "", ATOM) == "2018-01-15T00:00:00+00:00"
    assert python.findtext("a:summary", "", ATOM).strip() == "<p>Summary first.</p>"
    assert "print" in python.findtext("a:content", "", ATOM)  # escaped once, so it parses back to HTML


def test_rss_feed_has_the_same_pages(public):
    items = rss_items(public / "rss.xml")

    assert [item.findtext("title") for item in items] == atom_titles(public / "atom.xml")
    assert items[1].findtext("link") == "https://example.com/posts/python/"
    assert items[1].findtext("pubDate") == "Wed, 01 Mar 2017 00:00:00 +0000"


def test_rss_dates_stay_english_on_a_czech_site(site_dir):
    configure(site_dir, 'language = "cs"')
    Site(site_dir).build()

    pub_date = rss_items(site_dir / "public" / "rss.xml")[1].findtext("pubDate")
    assert pub_date == "Wed, 01 Mar 2017 00:00:00 +0000"


def test_section_feed_has_only_its_own_pages(public):
    feed = public / "posts" / "tutorials" / "programming" / "atom.xml"

    assert atom_titles(feed) == ["Rust", "Python"]  # by date, though the section sorts by weight
    assert (public / "posts" / "tutorials" / "programming" / "rss.xml").exists()
    assert not (public / "posts" / "atom.xml").exists()  # posts didn't ask for one


def test_every_term_gets_a_feed(public):
    assert atom_titles(public / "categories" / "a-category" / "atom.xml") == ["Python", "Příliš žluťoučký kůň"]
    assert (public / "categories" / "zlutoucky-kun" / "atom.xml").exists()
    assert not (public / "podcast-authors" / "some-person" / "atom.xml").exists()  # no feed = true there


def test_drafts_stay_out_of_the_feed(public):
    assert "A draft" not in atom_titles(public / "atom.xml")


def test_feeds_are_not_in_the_sitemap(public):
    assert "atom.xml" not in (public / "sitemap.xml").read_text()


def test_feed_limit(site_dir):
    configure(site_dir, "feed_limit = 2")
    Site(site_dir).build()

    assert atom_titles(site_dir / "public" / "atom.xml") == ["Simple", "Python"]


def test_site_feed_is_off_unless_asked_for(site_dir):
    config = site_dir / "config.toml"
    config.write_text(config.read_text().replace("generate_feeds = true\n", ""))
    Site(site_dir).build()

    assert not (site_dir / "public" / "atom.xml").exists()
    assert (site_dir / "public" / "posts" / "tutorials" / "programming" / "atom.xml").exists()


def test_site_can_bring_its_own_feed_template(site_dir):
    (site_dir / "templates" / "atom.xml").write_text("{{ pages | length }} pages in {{ title }}")
    Site(site_dir).build()

    assert (site_dir / "public" / "atom.xml").read_text() == "8 pages in Hrabal test site"


def test_feed_without_a_template_stops_the_build(site_dir):
    config = site_dir / "config.toml"
    text = config.read_text().replace('["atom.xml", "rss.xml"]', '["feed.json"]')
    config.write_text(text)
    with pytest.raises(HrabalError, match=r"feed\.json"):
        Site(site_dir).build()


def test_feed_limit_must_be_a_positive_number(site_dir):
    configure(site_dir, "feed_limit = -1")
    with pytest.raises(HrabalError, match="feed_limit must be a positive number"):
        Site(site_dir).load()
