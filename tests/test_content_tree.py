# How tests/test_site/content turns into sections and pages. Many cases follow Zola's own test site.
# Tests that break the site on purpose add their files to a copy of it, see site_dir in conftest.py.

import datetime
import os
import re
from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.content import slugify
from hrabal.site import Site


def write_files(root: Path, files: dict[str, str]):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def load(root: Path, **options) -> Site:
    site = Site(root, **options)
    site.load()
    return site


def titles(items) -> list[str]:
    return [item.title for item in items]


# sections and pages


def test_sections_are_nested_like_the_folders(site_dir):
    site = load(site_dir)

    assert len(site.sections) == 10
    # applying_page_template has no title
    assert titles(site.sections["_index.md"].subsections) == ["", "Paginated", "Posts", "Reverse paginated"]

    tutorials = site.sections["posts/tutorials/_index.md"]
    assert tutorials.pages == []
    assert titles(tutorials.subsections) == ["Programming", "DevOps"]  # by weight, not by name


def test_hidden_files_are_ignored(site_dir):
    site = load(site_dir)
    assert ".should-not-be-picked-up.md" not in site.pages
    assert titles(site.sections["_index.md"].pages) == ["Hello"]


def test_pages_are_sorted_by_the_section_rules(site_dir):
    site = load(site_dir)

    posts = site.sections["posts/_index.md"].pages
    assert titles(posts) == [
        "Simple",
        "Python",
        "Fixed slug",
        "Příliš žluťoučký kůň",
        "A post with dates",
        "With assets",
    ]
    assert titles(site.sections["posts/tutorials/programming/_index.md"].pages) == ["Python", "Rust"]
    assert titles(site.sections["posts/tutorials/devops/_index.md"].pages) == ["Docker", "Nix"]


def test_previous_and_next_follow_the_section_order(site_dir):
    simple, python, fixed_slug = load(site_dir).sections["posts/_index.md"].pages[:3]

    assert python.previous is simple
    assert python.next is fixed_slug


def test_first_and_last_pages_have_one_neighbour(site_dir):
    posts = load(site_dir).sections["posts/_index.md"].pages

    assert posts[0].previous is None
    assert posts[-1].next is None


def test_ancestors_go_from_the_home_page_down(site_dir):
    site = load(site_dir)
    docker = site.pages["posts/tutorials/devops/docker.md"]

    assert titles(docker.ancestors) == ["Home", "Posts", "Tutorials", "DevOps"]
    assert docker.ancestors[-1] is site.sections["posts/tutorials/devops/_index.md"]
    assert titles(site.sections["posts/tutorials/_index.md"].ancestors) == ["Home", "Posts"]
    assert titles(site.pages["hello.md"].ancestors) == ["Home"]
    assert site.sections["_index.md"].ancestors == []


def test_section_extra_is_available(site_dir):
    programming = load(site_dir).sections["posts/tutorials/programming/_index.md"]
    assert programming.extra == {"we_have_extra": "variables"}


def test_folder_names_get_slugified(site_dir):
    site = load(site_dir)
    assert site.sections["applying_page_template/_index.md"].path == "/applying-page-template/"
    assert site.pages["applying_page_template/another_section/post.md"].path == (
        "/applying-page-template/another-section/post/"
    )


def test_slug_from_front_matter_gets_slugified(site_dir):
    assert load(site_dir).pages["posts/fixed-slug.md"].path == "/posts/something-else/"


@pytest.mark.parametrize(
    "text, slug",
    [
        ("Hello World", "hello-world"),
        ("Příliš žluťoučký kůň", "prilis-zlutoucky-kun"),
        ("something-&-else", "something-else"),
        ("  --Spaces & symbols!-- ", "spaces-symbols"),
    ],
)
def test_slugify(text, slug):
    assert slugify(text) == slug


def test_folder_with_index_md_is_a_page_not_a_section(site_dir):
    site = load(site_dir)

    assert "posts/with-assets/_index.md" not in site.sections
    page = site.pages["posts/with-assets/index.md"]
    assert page.path == "/posts/with-assets/"
    assert [asset.name for asset in page.assets] == ["with.js", "zola.png"]  # no .hidden-note


def test_page_and_section_index_in_one_folder_is_an_error(site_dir):
    write_files(
        site_dir,
        {
            "content/both/_index.md": '+++\ntitle = "Section"\n+++\n',
            "content/both/index.md": '+++\ntitle = "Page"\n+++\n',
        },
    )
    with pytest.raises(HrabalError, match="content/both is a section"):
        load(site_dir)


def test_index_md_next_to_the_home_page_is_an_error(site_dir):
    write_files(site_dir, {"content/index.md": '+++\ntitle = "Oops"\n+++\n'})
    with pytest.raises(HrabalError, match="content is a section"):
        load(site_dir)


# drafts


def test_draft_pages_are_left_out_by_default(site_dir):
    assert "posts/draft.md" not in load(site_dir).pages
    assert "posts/draft.md" in load(site_dir, drafts=True).pages


def test_draft_section_hides_everything_inside(site_dir):
    site = load(site_dir)
    assert not any(key.startswith("secret_section/") for key in [*site.sections, *site.pages])

    site = load(site_dir, drafts=True)
    assert len(site.sections) == 12
    assert "secret_section/secret_sub_section/_index.md" in site.sections
    assert "secret_section/page.md" in site.pages
    assert "secret_section/secret_sub_section/hello.md" in site.pages


def test_home_page_cannot_be_a_draft(site_dir):
    write_files(site_dir, {"content/_index.md": "+++\ndraft = true\n+++\n"})
    with pytest.raises(HrabalError, match="home page can't be a draft"):
        load(site_dir)


# templates chosen for pages


def test_section_page_template_and_page_override(site_dir):
    section = load(site_dir).sections["applying_page_template/_index.md"]

    override, from_section = section.pages  # sorted by weight
    assert override.template == "page_template_override.html"
    assert from_section.template == "page_template.html"


def test_page_template_carries_into_subsections(site_dir):
    site = load(site_dir)

    inherited = site.pages["applying_page_template/another_section/post.md"]
    assert inherited.template == "page_template.html"

    # a subsection with its own page_template keeps it
    local = site.pages["applying_page_template/yet_another_section/post.md"]
    assert local.template == "page_template_child.html"


# dates


def test_date_and_slug_from_the_file_name(site_dir):
    page = load(site_dir).pages["posts/2016-10-08_a-post-with-dates.md"]
    assert page.date == datetime.date(2016, 10, 8)
    assert page.path == "/posts/a-post-with-dates/"


@pytest.mark.parametrize(
    "file, front_matter, date, path",
    [
        ("2020-02-02-dash-works-too.md", "", datetime.date(2020, 2, 2), "/notes/dash-works-too/"),
        (
            "2020-02-02_front-matter-wins.md",
            "date = 2021-01-01",
            datetime.date(2021, 1, 1),
            "/notes/front-matter-wins/",
        ),
        ("2020-02-02_own-slug.md", 'slug = "elsewhere"', datetime.date(2020, 2, 2), "/notes/elsewhere/"),
        ("2016-13-45_not-a-date.md", "", None, "/notes/2016-13-45-not-a-date/"),
        ("2019-05-05-a-trip/index.md", "", datetime.date(2019, 5, 5), "/notes/a-trip/"),
    ],
)
def test_dates_in_file_names(site_dir, file, front_matter, date, path):
    write_files(site_dir, {f"content/notes/{file}": f"+++\n{front_matter}\n+++\n"})
    page = load(site_dir).pages[f"notes/{file}"]
    assert page.date == date
    assert page.path == path


def test_quoted_date_is_an_error(site_dir):
    write_files(site_dir, {"content/quoted.md": '+++\ndate = "2024-05-01"\n+++\n'})
    with pytest.raises(HrabalError, match="without quotes"):
        load(site_dir)


# taxonomies


def test_terms_collect_their_pages_newest_first(site_dir):
    categories = load(site_dir).taxonomies["categories"]

    assert list(categories.terms) == ["a-category", "zlutoucky-kun"]
    assert titles(categories.terms["a-category"].pages) == ["Python", "Příliš žluťoučký kůň"]
    assert categories.terms["zlutoucky-kun"].name == "Žluťoučký kůň"


def test_unknown_taxonomy_is_an_error(site_dir):
    write_files(site_dir, {"content/wrong.md": "+++\n[taxonomies]\nwrong = []\n+++\n"})
    with pytest.raises(HrabalError, match="taxonomy 'wrong' is not listed"):
        load(site_dir)


# markdown and links


def test_summary_is_everything_before_more(site_dir):
    python = load(site_dir).pages["posts/python.md"]

    assert python.summary.strip() == "<p>Summary first.</p>"
    assert "print" in python.content


def test_internal_links_are_resolved(site_dir):
    hello = load(site_dir).pages["hello.md"].content

    assert 'href="https://example.com/posts/simple/#details"' in hello
    assert 'href="https://example.com/posts/"' in hello
    assert 'href="https://example.com/posts/tutorials/"' in hello


def test_links_to_page_files(site_dir):
    site = load(site_dir)
    page = site.pages["posts/with-assets/index.md"]
    url = "https://example.com/posts/with-assets/zola.png"

    assert f'href="{url}"' in page.content
    assert f'src="{url}"' in page.content
    assert site.get_url("@/posts/with-assets/zola.png") == url


@pytest.mark.parametrize("link", ["[nowhere](@/missing.md)", "![gone](@/posts/with-assets/missing.png)"])
def test_broken_internal_link_is_an_error(site_dir, link):
    write_files(site_dir, {"content/oops.md": link})
    with pytest.raises(HrabalError, match="broken internal link"):
        load(site_dir)


# config and front matter mistakes


def test_unknown_front_matter_is_an_error(site_dir):
    write_files(site_dir, {"content/typo.md": '+++\ntitel = "Typo"\n+++\n'})
    with pytest.raises(HrabalError, match="titel"):
        load(site_dir)


def test_unknown_config_key_is_an_error(site_dir):
    config = site_dir / "config.toml"
    config.write_text('colour = "red"\n' + config.read_text())
    with pytest.raises(HrabalError, match="unknown keys colour"):
        load(site_dir)


# heading anchors


def test_pages_know_their_heading_ids(site_dir):
    assert load(site_dir).pages["posts/simple.md"].heading_ids == ["details"]


def test_links_to_headings_are_checked(site_dir):
    write_files(site_dir, {"content/oops.md": "[gone](@/posts/simple.md#nothing-here)"})
    with pytest.raises(HrabalError, match=re.escape("oops.md: @/posts/simple.md#nothing-here points to a heading")):
        load(site_dir)


def test_get_url_checks_anchors_too(site_dir):
    (site_dir / "templates" / "page.html").write_text("{{ get_url('@/posts/simple.md#nope') }}")
    with pytest.raises(HrabalError, match="points to a heading that isn't there"):
        Site(site_dir).build()


def test_insert_anchor_links_must_be_known(site_dir):
    config = site_dir / "config.toml"
    config.write_text('insert_anchor_links = "top"\n' + config.read_text())
    with pytest.raises(HrabalError, match="insert_anchor_links must be one of none, left, right, heading"):
        load(site_dir)


def test_anchor_links_come_from_the_config(site_dir):
    config = site_dir / "config.toml"
    config.write_text('insert_anchor_links = "right"\n' + config.read_text())

    content = load(site_dir).pages["posts/simple.md"].content
    assert '<h2 id="details">Details <a class="anchor" href="#details"' in content


def test_summary_has_no_footnote_numbers(site_dir):
    write_files(
        site_dir,
        {"content/noted.md": "+++\n+++\nShort[^a] summary.\n\n<!-- more -->\n\nRest.\n\n[^a]: The note.\n"},
    )
    page = load(site_dir).pages["noted.md"]

    assert page.summary.strip() == "<p>Short summary.</p>"
    assert "footnote-ref" in page.content  # the page itself keeps it


# when a page was last edited


def test_updated_comes_from_the_front_matter(site_dir):
    python = load(site_dir).pages["posts/python.md"]

    assert python.updated == datetime.date(2018, 1, 15)
    assert python.last_changed() == datetime.date(2018, 1, 15)


def test_last_changed_is_the_later_of_date_and_updated(site_dir):
    site = load(site_dir)

    # conftest.py gives every file of the test site 2000-01-01, older than any date in it
    assert site.pages["posts/simple.md"].last_changed() == datetime.date(2017, 4, 1)
    assert site.pages["hello.md"].last_changed() == datetime.date(2000, 1, 1)  # no date, only the file's


def test_updated_falls_back_to_the_file_time(site_dir):
    hello = site_dir / "content" / "hello.md"
    moment = datetime.datetime(2023, 6, 7, 12, 0).timestamp()
    os.utime(hello, (moment, moment))

    site = load(site_dir)
    assert site.pages["hello.md"].updated == datetime.date(2023, 6, 7)
    assert site.pages["posts/python.md"].updated == datetime.date(2018, 1, 15)  # the front matter still wins


def test_quoted_updated_is_an_error(site_dir):
    write_files(site_dir, {"content/quoted.md": '+++\nupdated = "2024-05-01"\n+++\n'})
    with pytest.raises(HrabalError, match="write the updated without quotes"):
        load(site_dir)
