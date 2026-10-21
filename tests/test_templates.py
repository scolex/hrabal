# What the built tests/test_site looks like. Its templates print plain "Label: value" lines,
# the same trick Zola's test site uses, so each test can check what a template got to see.

from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.site import Site


def html(public: Path, path: str = "") -> str:
    return (public / path / "index.html").read_text(encoding="utf-8")


def test_index_sees_config_and_template_functions(public):
    index = html(public)

    assert "Site: Hrabal test site" in index
    assert "Author: Test Author" in index
    assert "Sub-sections: 4" in index
    assert "Root pages: Hello;" in index
    assert "Latest post: Simple" in index
    assert "get_page: https://example.com/hello/" in index
    assert "get_url to a page: https://example.com/hello/" in index
    assert "get_url to a page file: https://example.com/posts/with-assets/zola.png" in index
    assert "get_url to a static file: https://example.com/site.css" in index
    assert "<h1>Welcome</h1>" in index


def test_templates_can_extend_each_other(public):
    index = html(public)
    assert index.startswith("<!doctype html>")
    assert '<link rel="stylesheet" href="https://example.com/site.css">' in index
    assert "<title>Hrabal test site</title>" in index
    assert "<title>Python</title>" in html(public, "posts/python")


def test_section_lists_its_pages_and_subsections(public):
    posts = html(public, "posts")

    assert "File: content/posts/_index.md" in posts
    assert "Path: /posts/" in posts
    assert "Description: Everything with a date" in posts
    assert "Pages: 6" in posts
    assert "Sub-sections: 1" in posts
    assert "Page: Fixed slug -> https://example.com/posts/something-else/" in posts
    assert "Subsection: Tutorials" in posts


def test_subsections_come_in_weight_order(public):
    tutorials = html(public, "posts/tutorials")

    assert "Pages: 0" in tutorials
    assert "Sub-sections: 2" in tutorials
    assert tutorials.index("Subsection: Programming") < tutorials.index("Subsection: DevOps")


def test_section_extra_reaches_the_template(public):
    assert "Extra: variables" in html(public, "posts/tutorials/programming")
    assert "Extra:" not in html(public, "posts/tutorials/devops")


def test_page_sees_its_metadata(public):
    python = html(public, "posts/python")

    assert "Title: Python" in python
    assert "File: content/posts/python.md" in python
    assert "Slug: python" in python
    assert "Description: Snakes" in python
    assert "Mood: curious" in python
    assert "Previous: Simple" in python
    assert "Next: Fixed slug" in python


def test_date_filter(public):
    python = html(public, "posts/python")

    assert "Date: 01. 03. 2017" in python
    assert "ISO date: 2017-03-01" in python
    assert "Date:" not in html(public, "hello")  # no date, nothing printed


def test_date_filter_speaks_czech(public):
    python = html(public, "posts/python")

    assert "Czech date: 1. března 2017" in python
    assert "Month in the site language: March" in python  # config.toml doesn't set a language


def test_date_filter_follows_the_site_language(site_dir, tmp_path):
    config = site_dir / "config.toml"
    config.write_text('language = "cs"\n' + config.read_text(encoding="utf-8"), encoding="utf-8")
    output = tmp_path / "czech"
    Site(site_dir, output_dir=output).build()

    assert "Month in the site language: března" in html(output, "posts/python")


def test_date_filter_with_an_unknown_locale_stops_the_build(site_dir):
    config = site_dir / "config.toml"
    config.write_text('language = "tlh"\n' + config.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(HrabalError, match="no month and day names for 'tlh'"):
        Site(site_dir).build()


def test_summary_and_content_are_rendered_apart(public):
    python = html(public, "posts/python")
    summary = python.split("Summary: ", 1)[1].split("\n", 1)[0]

    assert summary == "<p>Summary first.</p>"
    assert "print" in python


def test_page_links_to_its_terms(public):
    python = html(public, "posts/python")
    czech = html(public, "posts/czech")

    assert "Term: categories/A category -> https://example.com/categories/a-category/" in python
    assert "Term: podcast_authors/Some Person -> https://example.com/podcast-authors/some-person/" in python
    assert "Term: categories/Žluťoučký kůň -> https://example.com/categories/zlutoucky-kun/" in czech


def test_taxonomy_can_have_its_own_templates(public):
    categories = html(public, "categories")
    podcast_authors = html(public, "podcast-authors")

    assert "Categories, with their own template:" in categories
    assert "A category (2) -> https://example.com/categories/a-category/" in categories
    assert "Žluťoučký kůň (1) -> https://example.com/categories/zlutoucky-kun/" in categories

    # no podcast_authors/list.html, so the generic one is used
    assert "Generic list of podcast_authors:" in podcast_authors
    assert "Some Person (1)" in podcast_authors


def test_term_page_lists_pages_newest_first(public):
    term = html(public, "categories/a-category")

    assert "Category: A category" in term
    assert term.index("Page: Python") < term.index("Page: Příliš žluťoučký kůň")
    assert "Generic term Some Person in podcast_authors" in html(public, "podcast-authors/some-person")


def test_page_templates_are_used_for_rendering(public):
    pages = public / "applying-page-template"

    assert html(pages, "from-section-config") == "from section: From section config"
    assert html(pages, "override") == "overridden: Override"
    assert html(pages, "another-section/post") == "from section: Changed recursively"
    assert html(pages, "yet-another-section/post") == "from child section: Local section override"


def test_markdown_tables_and_strikethrough(public):
    hello = html(public, "hello")

    assert "<table>" in hello
    assert "<td>a</td>" in hello
    assert "<s>Struck out</s>" in hello


def test_code_blocks_are_highlighted(public):
    assert '<span style="color:' in html(public, "posts/python")


def test_page_files_are_copied_and_linked(public):
    bundle = public / "posts" / "with-assets"
    page = html(bundle)

    assert (bundle / "with.js").exists()
    assert (bundle / "zola.png").exists()
    assert not (bundle / ".hidden-note").exists()

    assert "Asset: with.js" in page
    assert "Asset: zola.png" in page
    assert 'href="with.js"' in page  # plain relative links stay as they are
    assert 'src="https://example.com/posts/with-assets/zola.png"' in page


def test_static_files_keep_their_folders(public):
    assert (public / "site.css").exists()
    assert (public / "nested" / "deep.txt").exists()


def test_drafts_and_hidden_files_are_not_built(public):
    assert not (public / "posts" / "draft").exists()
    assert not (public / "secret-section").exists()
    assert not (public / "should-not-be-picked-up").exists()


def test_drafts_are_built_when_asked(site_dir, tmp_path):
    output = tmp_path / "with-drafts"
    Site(site_dir, output_dir=output, drafts=True).build()

    assert (output / "posts" / "draft" / "index.html").exists()
    assert "Section: Drafted section" in html(output, "secret-section")
    assert (output / "secret-section" / "secret-sub-section" / "hello" / "index.html").exists()


def test_live_reload_is_only_injected_when_asked(public, site_dir, tmp_path):
    assert "reload-me" not in html(public)

    output = tmp_path / "dev"
    Site(site_dir, output_dir=output, inject_html="<!-- reload-me -->").build()
    assert "<!-- reload-me --></body>" in html(output)


def test_base_url_can_be_swapped_for_the_dev_server(site_dir, tmp_path):
    output = tmp_path / "dev"
    Site(site_dir, output_dir=output, base_url="http://localhost:1111").build()

    assert "get_page: http://localhost:1111/hello/" in html(output)
    assert "example.com" not in html(output, "posts/python")
