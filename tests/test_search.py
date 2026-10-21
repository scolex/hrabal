import json
from pathlib import Path

from hrabal.search import TEXT_LIMIT, page_text
from hrabal.site import Site


def read_index(public: Path) -> dict[str, dict]:
    entries = json.loads((public / "search_index.json").read_text(encoding="utf-8"))
    return {entry["url"].removeprefix("https://example.com"): entry for entry in entries}


def test_every_built_page_is_in_the_index(public):
    index = read_index(public)

    assert len(index) == 24  # the test site builds 24 pages
    assert "/posts/python/" in index
    assert "/posts/draft/" not in index


def test_entry_has_what_the_search_box_needs(public):
    python = read_index(public)["/posts/python/"]

    assert python["title"] == "Python"
    assert python["url"] == "https://example.com/posts/python/"
    assert python["date"] == "2017-03-01"
    assert python["description"] == "Snakes"
    assert python["tags"] == ["A category", "Some Person"]
    assert python["text"].startswith("Summary first.")
    assert 'print("hello")' in python["text"]  # code is searchable too


def test_czech_stays_readable_in_the_file(public):
    raw = (public / "search_index.json").read_text(encoding="utf-8")
    assert "Příliš žluťoučký kůň" in raw  # not ří...


def test_undated_page_has_no_date(public):
    assert read_index(public)["/hello/"]["date"] is None


def test_text_is_without_html_or_diagram_source(public):
    hello = read_index(public)["/hello/"]["text"]

    assert "<" not in hello
    assert "Links to a page, a section and a nested section." in hello
    assert "flowchart" not in hello


def test_page_can_stay_out_of_the_index(site_dir):
    (site_dir / "content" / "secret.md").write_text('+++\ntitle = "Hidden"\nsearch = false\n+++\n', encoding="utf-8")
    Site(site_dir).build()

    assert "/secret/" not in read_index(site_dir / "public")
    assert (site_dir / "public" / "secret" / "index.html").exists()  # still built, just not searchable


def test_drafts_are_indexed_only_when_built(site_dir, tmp_path):
    output = tmp_path / "with-drafts"
    Site(site_dir, output_dir=output, drafts=True).build()

    assert "/posts/draft/" in read_index(output)


def test_long_pages_are_cut(site_dir):
    (site_dir / "content" / "long.md").write_text("+++\n+++\n" + "word " * 5000, encoding="utf-8")
    Site(site_dir).build()

    assert len(read_index(site_dir / "public")["/long/"]["text"]) == TEXT_LIMIT


def test_index_is_off_unless_asked_for(site_dir):
    config = site_dir / "config.toml"
    config.write_text(config.read_text(encoding="utf-8").replace("build_search_index = true\n", ""), encoding="utf-8")
    Site(site_dir).build()

    assert not (site_dir / "public" / "search_index.json").exists()


def test_page_text():
    html = "<h1>Title</h1>\n<p>Some <em>nice</em>\ntext.</p><script>alert(1)</script><style>p {}</style><p>End</p>"
    assert page_text(html) == "Title Some nice text. End"


def test_footnote_back_links_stay_out_of_the_text():
    html = '<p>Text<sup class="footnote-ref"><a href="#fn1">1</a></sup>.</p><section class="footnotes"><ol>'
    html += '<li><p>The note. <a href="#fnref1" class="footnote-backref">↩︎</a></p></li></ol></section>'
    assert page_text(html) == "Text1. The note."
