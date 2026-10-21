# hrabal's own look in hrabal/theme/: a site with just config.toml and content/ uses all of it,
# and its own templates/ and static/ replace single files of it.

import shutil
from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.cli import STARTER, init_site
from hrabal.site import BUILT_IN_TEMPLATES, THEME, Site


@pytest.fixture
def plain_site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    (root / "content" / "blog").mkdir(parents=True)
    (root / "config.toml").write_text('base_url = "https://example.com"\ntitle = "Plain"\n', encoding="utf-8")
    (root / "content" / "blog" / "_index.md").write_text('+++\ntitle = "Blog"\n+++\n', encoding="utf-8")
    (root / "content" / "blog" / "first.md").write_text(
        '+++\ntitle = "First"\ndate = 2024-05-01\n+++\n', encoding="utf-8"
    )
    return root


def build(root: Path) -> Path:
    Site(root).build()
    return root / "public"


def html(public: Path, path: str = "") -> str:
    return (public / path / "index.html").read_text(encoding="utf-8")


def configure(root: Path, text: str):
    config = root / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_site_without_templates_uses_the_theme(plain_site):
    public = build(plain_site)

    assert '<link rel="stylesheet" href="https://example.com/neat.css">' in html(public)
    assert "<time>May 1, 2024</time>" in html(public, "blog/first")  # date_long in English
    for name in ("neat.css", "style.css", "theme.js", "copy.js", "menu.js", "icon.svg"):
        assert (public / name).exists()


def test_theme_defaults(plain_site):
    index = html(build(plain_site))

    assert '<div class="menu-links" id="menu-links">\n      </div>' in index  # no menu until [theme] has one
    assert "<h2>" not in index  # no home_posts, no list of posts on the home page
    assert '<img src="https://example.com/icon.svg" alt="">' in index  # the bale comes with the theme


def test_theme_settings(plain_site):
    configure(
        plain_site,
        """
[theme]
menu = [{ title = "Posts", url = "@/blog/_index.md" }, { title = "Elsewhere", url = "https://example.org/" }]
home_posts = "blog/_index.md"
copyright_since = 2020
""",
    )
    index = html(build(plain_site))

    assert '<a href="https://example.com/blog/">Posts</a>' in index
    assert '<a href="https://example.org/">Elsewhere</a>' in index  # whole addresses stay as they are
    assert "<h2>Latest posts</h2>" in index
    assert "First" in index
    assert "© 2020–" in index  # noqa: RUF001, an en dash on purpose


def test_every_feed_gets_a_link_in_the_head(plain_site):
    configure(plain_site, 'generate_feeds = true\nfeed_filenames = ["atom.xml", "rss.xml"]\n')
    index = html(build(plain_site))

    assert 'type="application/atom+xml" title="Plain" href="https://example.com/atom.xml">' in index
    assert 'type="application/rss+xml" title="Plain" href="https://example.com/rss.xml">' in index


def test_site_template_replaces_the_themes(plain_site):
    (plain_site / "templates").mkdir()
    (plain_site / "templates" / "page.html").write_text("my own {{ page.title }}", encoding="utf-8")
    public = build(plain_site)

    assert html(public, "blog/first") == "my own First"
    assert "neat.css" in html(public, "blog")  # every other template still comes from the theme


def test_site_static_file_replaces_the_themes(plain_site):
    (plain_site / "static").mkdir()
    (plain_site / "static" / "style.css").write_text("body { color: red; }", encoding="utf-8")
    public = build(plain_site)

    assert (public / "style.css").read_text(encoding="utf-8") == "body { color: red; }"
    assert (public / "neat.css").read_text(encoding="utf-8") == (THEME / "static" / "neat.css").read_text(
        encoding="utf-8"
    )


def test_taxonomy_without_a_translation_still_gets_a_title(plain_site):
    configure(plain_site, 'taxonomies = ["categories"]\n')
    first = plain_site / "content" / "blog" / "first.md"
    first.write_text('+++\ntitle = "First"\n[taxonomies]\ncategories = ["Books"]\n+++\n', encoding="utf-8")
    public = build(plain_site)

    assert "<h1>Categories</h1>" in html(public, "categories")


@pytest.mark.parametrize(
    "theme, error",
    [
        ('theme = "fancy"\n', "theme settings go in a \\[theme\\] table"),
        ("[theme]\ncolours = 3\n", "unknown theme settings colours"),
        ('[theme]\nmenu = [{ title = "Blog" }]\n', "every menu item needs a title and a url"),
        ('[theme]\nbreadcrumbs = "yes"\n', "breadcrumbs is either true or false"),
    ],
)
def test_theme_settings_are_checked(plain_site, theme, error):
    config = plain_site / "config.toml"
    if theme.startswith("theme ="):
        config.write_text(theme + config.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        configure(plain_site, theme)
    with pytest.raises(HrabalError, match=error):
        Site(plain_site).load()


def test_theme_holds_the_look_and_hrabal_the_rest():
    for name in ("sitemap.xml", "atom.xml", "rss.xml", "robots.txt"):
        assert (BUILT_IN_TEMPLATES / name).exists()
        assert not (THEME / "templates" / name).exists()


def test_init_creates_only_config_and_content(tmp_path):
    init_site(tmp_path / "new")

    assert sorted(path.name for path in (tmp_path / "new").iterdir()) == ["config.toml", "content"]
    assert not (STARTER / "templates").exists()
    assert not (STARTER / "static").exists()


def test_starter_builds_from_a_copy(tmp_path):
    site = shutil.copytree(STARTER, tmp_path / "site")
    assert (build(site) / "blog" / "a-tour-of-hrabal" / "index.html").exists()


# the 404 page


def test_no_breadcrumbs_unless_asked_for(plain_site):
    assert "breadcrumbs" not in html(build(plain_site), "blog/first")


def test_breadcrumbs_lead_from_home_to_the_section(plain_site):
    configure(plain_site, "[theme]\nbreadcrumbs = true\n")
    post = html(build(plain_site), "blog/first")

    assert '<nav class="breadcrumbs" aria-label="Breadcrumbs">' in post
    assert '<li><a href="https://example.com/">Home</a></li>' in post
    assert '<li><a href="https://example.com/blog/">Blog</a></li>' in post
    assert "<li><a" not in post.split("<h1>")[1]  # the page's own title is the heading, not a crumb


def test_nested_sections_get_breadcrumbs_in_the_site_language(plain_site):
    configure(plain_site, 'language = "cs"\n[theme]\nbreadcrumbs = true\n')
    books = plain_site / "content" / "blog" / "books"
    books.mkdir()
    (books / "_index.md").write_text('+++\ntitle = "Knihy"\n+++\n', encoding="utf-8")
    page = html(build(plain_site), "blog/books")

    assert 'aria-label="Drobečková navigace"' in page
    assert '<a href="https://example.com/">Úvod</a>' in page
    assert '<a href="https://example.com/blog/">Blog</a>' in page


def test_no_breadcrumbs_right_under_the_home_page(plain_site):
    configure(plain_site, "[theme]\nbreadcrumbs = true\n")
    (plain_site / "content" / "about.md").write_text('+++\ntitle = "About"\n+++\n', encoding="utf-8")
    public = build(plain_site)

    for path in ("", "about", "blog"):
        assert "breadcrumbs" not in html(public, path)


def test_every_build_has_a_404_page(plain_site):
    public = build(plain_site)
    page = (public / "404.html").read_text(encoding="utf-8")

    assert "<h1>Page not found</h1>" in page
    assert '<a class="button" href="https://example.com/">Back to the home page</a>' in page
    assert "press /" not in page  # no search on this site
    assert "404" not in (public / "sitemap.xml").read_text(encoding="utf-8")


def test_404_page_speaks_the_site_language_and_mentions_search(plain_site):
    configure(plain_site, 'language = "cs"\nbuild_search_index = true\n')
    page = (build(plain_site) / "404.html").read_text(encoding="utf-8")

    assert "<h1>Stránka nenalezena</h1>" in page
    assert "stačí stisknout /" in page


def test_site_can_bring_its_own_404_page(plain_site):
    (plain_site / "templates").mkdir()
    (plain_site / "templates" / "404.html").write_text("lost", encoding="utf-8")

    assert (build(plain_site) / "404.html").read_text(encoding="utf-8") == "lost"
