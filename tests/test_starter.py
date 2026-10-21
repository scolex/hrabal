import datetime
import os
import shutil
from pathlib import Path

import pytest

from hrabal.cli import STARTER
from hrabal.site import Site

# the site `hrabal init` copies has to keep working, the rest lives in test_content_tree.py and test_templates.py


@pytest.fixture
def starter_dir(tmp_path: Path) -> Path:
    return shutil.copytree(STARTER, tmp_path / "site")


def test_starter_builds(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    assert (public / "index.html").exists()
    assert (public / "about" / "index.html").exists()
    assert (public / "blog" / "prilis-hlucna-samota" / "index.html").exists()
    assert (public / "blog" / "a-picture" / "drawing.svg").exists()
    assert (public / "tags" / "hrabal" / "index.html").exists()
    assert (public / "style.css").exists()


def test_starter_is_styled_with_neat_css(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    index = (public / "index.html").read_text(encoding="utf-8")
    assert index.index("neat.css") < index.index("style.css")  # our rules come after Neat's
    # Neat is MIT licensed, the notice has to travel with the file
    assert "Copyright (c) 2021-2026 by Dare Companies Dotcom LLC" in (public / "neat.css").read_text(encoding="utf-8")


def test_starter_has_a_theme_switch(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    index = (public / "index.html").read_text(encoding="utf-8")
    assert 'class="theme-switch"' in index
    assert index.index("theme.js") < index.index("</head>")  # early, so the page doesn't flash
    assert (public / "theme.js").exists()
    assert ':root[data-theme="dark"]' in (public / "style.css").read_text(encoding="utf-8")


def test_starter_can_draw_diagrams_and_math_on_every_page(starter_dir):
    # the scripts themselves fetch Mermaid and KaTeX only when there's something to draw,
    # so a summary with a formula gets drawn in the list of posts as well
    Site(starter_dir).build()
    public = starter_dir / "public"

    for path in ("", "blog", "about", "tags/hrabal"):
        page = (public / path / "index.html").read_text(encoding="utf-8")
        assert '<script type="module" src="https://example.com/mermaid.js">' in page
        assert '<script type="module" src="https://example.com/math.js">' in page
    assert (public / "mermaid.js").exists()
    assert (public / "math.js").exists()

    tour = (public / "blog" / "a-tour-of-hrabal" / "index.html").read_text(encoding="utf-8")
    assert '<pre class="mermaid">' in tour
    assert '<span class="math inline">e^{i\\pi} + 1 = 0</span>' in tour
    assert "$5 and $10" in tour


def test_starter_has_a_feed(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    index = (public / "index.html").read_text(encoding="utf-8")
    assert (
        '<link rel="alternate" type="application/atom+xml" title="My site" href="https://example.com/atom.xml">'
        in index
    )
    feed = (public / "atom.xml").read_text(encoding="utf-8")
    assert "<name>Your Name</name>" in feed
    assert "Příliš hlučná samota" in feed
    assert "Not ready yet" not in feed  # the draft


def test_starter_icon_shows_next_to_the_title_and_as_favicon(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    index = (public / "index.html").read_text(encoding="utf-8")
    assert '<link rel="icon" href="https://example.com/icon.svg" type="image/svg+xml">' in index
    assert '<img src="https://example.com/icon.svg" alt="">' in index
    assert (public / "icon.svg").exists()


def test_starter_icon_can_be_left_out(starter_dir):
    config = starter_dir / "config.toml"
    config.write_text(config.read_text(encoding="utf-8").replace('icon = "icon.svg"', 'icon = ""'), encoding="utf-8")
    Site(starter_dir).build()

    index = (starter_dir / "public" / "index.html").read_text(encoding="utf-8")
    assert 'rel="icon"' not in index
    assert "<img" not in index


def test_starter_has_a_search_page(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    page = (public / "search" / "index.html").read_text(encoding="utf-8")
    assert '<div class="search search-page" data-index="https://example.com/search_index.json"' in page

    index = (public / "search_index.json").read_text(encoding="utf-8")
    assert "Příliš hlučná samota" in index
    assert '"title":"Search"' not in index  # the search page keeps itself out
    assert (public / "search.js").exists()


def test_starter_opens_search_from_a_magnifying_glass(starter_dir):
    Site(starter_dir).build()
    index = (starter_dir / "public" / "index.html").read_text(encoding="utf-8")

    # a real link to the search page, which search.js turns into the overlay
    assert '<a class="search-open" href="https://example.com/search/"' in index
    assert index.index("search-open") < index.index("theme-switch")  # right before the theme switch
    assert '<dialog class="search-dialog">' in index
    assert (starter_dir / "public" / "search.svg").exists()  # the icon itself, style.css uses it as a mask
    assert '<script type="module" src="https://example.com/search.js">' in index


def test_starter_without_search_has_no_magnifying_glass(starter_dir):
    config = starter_dir / "config.toml"
    config.write_text(config.read_text(encoding="utf-8").replace("build_search_index = true\n", ""), encoding="utf-8")
    Site(starter_dir).build()
    index = (starter_dir / "public" / "index.html").read_text(encoding="utf-8")

    assert "search-open" not in index
    assert "<dialog" not in index
    assert "search.js" not in index


def test_starter_footer_has_a_copyright_line(starter_dir):
    Site(starter_dir).build()
    index = (starter_dir / "public" / "index.html").read_text(encoding="utf-8")

    assert f"© 2024–{datetime.date.today().year} Your Name" in index  # noqa: RUF001, an en dash on purpose


def test_copyright_line_without_a_start_year_has_just_this_one(starter_dir):
    config = starter_dir / "config.toml"
    config.write_text(config.read_text(encoding="utf-8").replace("copyright_since = 2024", "#"), encoding="utf-8")
    Site(starter_dir).build()
    index = (starter_dir / "public" / "index.html").read_text(encoding="utf-8")

    assert f"© {datetime.date.today().year} Your Name" in index


def test_starter_adds_copy_buttons_to_code(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    post = (public / "blog" / "prilis-hlucna-samota" / "index.html").read_text(encoding="utf-8")
    assert '<script defer src="https://example.com/copy.js" data-copy="Kopírovat" data-copied="Zkopírováno"' in post
    for name in ("copy.js", "copy.svg", "check.svg"):
        assert (public / name).exists()


def test_starter_tour_shows_off_what_a_post_can_hold(starter_dir):
    Site(starter_dir).build()
    folder = starter_dir / "public" / "blog" / "a-tour-of-hrabal"
    tour = (folder / "index.html").read_text(encoding="utf-8")

    assert "<time>20. července 2024</time>" in tour  # the date comes from the folder name
    for kind in ("note", "tip", "important", "warning", "caution"):
        assert f'<div class="markdown-alert markdown-alert-{kind}">' in tour
    assert '<p class="markdown-alert-title">Varování</p>' not in tour  # the warning brings its own title
    assert '<p class="markdown-alert-title">Before you deploy</p>' in tour
    assert '<p class="markdown-alert-title">Poznámka</p>' in tour  # the others speak the starter's Czech
    assert '<th style="text-align:right">Default</th>' in tour
    assert '<pre class="highlight"' in tour
    assert tour.count('<pre class="mermaid">') == 2
    assert '<img src="https://example.com/blog/a-tour-of-hrabal/bale.svg"' in tour
    assert (folder / "bale.svg").exists()
    assert "<details>" in tour
    assert '<h2 id="tables">Tables <a class="anchor" href="#tables"' in tour
    assert 'href="https://example.com/blog/a-tour-of-hrabal/#code"' in tour
    assert tour.count('class="footnote-item"') == 2


def test_starter_has_an_icon_for_every_alert(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"
    css = (public / "style.css").read_text(encoding="utf-8")

    for kind in ("note", "tip", "important", "warning", "caution"):
        assert (public / "alerts" / f"{kind}.svg").exists()
        assert f'url("alerts/{kind}.svg")' in css


def test_starter_says_when_a_post_was_last_edited(starter_dir):
    post = starter_dir / "content" / "blog" / "prilis-hlucna-samota.md"
    edited = datetime.datetime(2025, 3, 9, 12, 0).timestamp()
    os.utime(post, (edited, edited))
    Site(starter_dir).build()
    blog = starter_dir / "public" / "blog"

    tour = (blog / "a-tour-of-hrabal" / "index.html").read_text(encoding="utf-8")
    assert '<p class="updated">Naposledy upraveno <time>2. srpna 2024</time></p>' in tour  # from its front matter
    samota = (blog / "prilis-hlucna-samota" / "index.html").read_text(encoding="utf-8")
    assert "Naposledy upraveno <time>9. března 2025</time>" in samota  # from the file


def test_no_edit_date_when_nothing_changed_after_publishing(starter_dir):
    post = starter_dir / "content" / "blog" / "prilis-hlucna-samota.md"
    published = datetime.datetime(2024, 5, 1, 12, 0).timestamp()  # the post's own date
    os.utime(post, (published, published))
    Site(starter_dir).build()

    samota = (starter_dir / "public" / "blog" / "prilis-hlucna-samota" / "index.html").read_text(encoding="utf-8")
    assert "Naposledy upraveno" not in samota


def test_starter_header_folds_its_links_into_a_menu(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"
    index = (public / "index.html").read_text(encoding="utf-8")
    links = index.split('<div class="menu-links" id="menu-links">')[1].split("</div>")[0]

    assert ">Blog</a>" in links
    assert ">O webu</a>" in links
    assert "search-open" not in links  # the icons stay outside the menu
    assert "theme-switch" not in links
    assert '<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="menu-links"' in index
    assert 'aria-label="Nabídka"' in index
    assert index.index("theme-switch") < index.index("menu-toggle")  # the sandwich comes last
    assert '<script defer src="https://example.com/menu.js">' in index
    for name in ("menu.js", "menu.svg", "close.svg"):
        assert (public / name).exists()


def test_menu_only_folds_when_scripts_run(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    assert 'root.classList.add("js")' in (public / "theme.js").read_text(encoding="utf-8")
    css = (public / "style.css").read_text(encoding="utf-8")
    assert "@media (max-width: 600px)" in css
    assert ":root.js .menu-links {\n    display: none;" in css


def test_starter_blog_is_paginated(starter_dir):
    Site(starter_dir).build()
    blog = starter_dir / "public" / "blog"

    listing = (blog / "index.html").read_text(encoding="utf-8")
    assert "Příliš hlučná samota" in listing
    assert "Starší" not in listing  # just one pager, so nowhere to go
    assert (blog / "page" / "1" / "index.html").exists()


def test_starter_uses_descriptions_in_meta_tags(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"

    blog = (public / "blog" / "index.html").read_text(encoding="utf-8")
    about = (public / "about" / "index.html").read_text(encoding="utf-8")
    assert '<meta name="description" content="Notes about books, now and then">' in blog
    assert '<meta name="description" content="A site made with hrabal">' in about  # falls back to config


def test_starter_draft_is_skipped(starter_dir):
    site = Site(starter_dir)
    site.load()
    assert "blog/unfinished.md" not in site.pages

    site = Site(starter_dir, drafts=True)
    site.load()
    assert "blog/unfinished.md" in site.pages


def test_starter_blog_is_newest_first(starter_dir):
    site = Site(starter_dir)
    site.load()
    blog = site.sections["blog/_index.md"]

    assert [p.slug for p in blog.pages] == ["a-tour-of-hrabal", "a-picture", "prilis-hlucna-samota"]
    assert blog.pages[0].next is blog.pages[1]
    assert blog.pages[1].previous is blog.pages[0]


def test_starter_internal_link(starter_dir):
    site = Site(starter_dir)
    site.load()

    about = site.pages["about.md"]
    assert 'href="https://example.com/blog/prilis-hlucna-samota/"' in about.content


def test_starter_summary(starter_dir):
    site = Site(starter_dir)
    site.load()
    post = site.pages["blog/prilis-hlucna-samota.md"]

    assert "summary shown in post lists" in post.summary
    assert "Pygments" not in post.summary


def test_starter_speaks_czech(starter_dir):
    Site(starter_dir).build()
    public = starter_dir / "public"
    index = (public / "index.html").read_text(encoding="utf-8")

    assert '<html lang="cs">' in index
    assert ">Štítky</a>" in index
    assert "<h2>Nejnovější příspěvky</h2>" in index
    assert 'placeholder="Hledat…"' in index
    assert "<time>20. července 2024</time>" in index  # date_long from hrabal's own Czech
    assert "<h1>Štítky</h1>" in (public / "tags" / "index.html").read_text(encoding="utf-8")


def test_starter_switches_to_english_with_one_line(starter_dir):
    config = starter_dir / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace('language = "cs"', 'language = "en"'), encoding="utf-8"
    )
    Site(starter_dir).build()
    public = starter_dir / "public"
    index = (public / "index.html").read_text(encoding="utf-8")

    assert '<html lang="en">' in index
    assert ">Štítky</a>" in index  # the menu says what [theme] says, everything hrabal writes itself switches
    assert "<h1>Tags</h1>" in (public / "tags" / "index.html").read_text(encoding="utf-8")
    assert "<h2>Latest posts</h2>" in index
    assert "<time>July 20, 2024</time>" in index
    tour = (public / "blog" / "a-tour-of-hrabal" / "index.html").read_text(encoding="utf-8")
    assert '<p class="markdown-alert-title">Note</p>' in tour
