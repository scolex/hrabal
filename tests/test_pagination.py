# Pagination, following Zola's tests: the unit tests in components/render/src/pagination.rs
# and the can_build_site_with_pagination_* tests in components/site/tests/site.rs.

from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.content import Page
from hrabal.pagination import paginate
from hrabal.site import Site


def make_pages(*titles: str) -> list[Page]:
    return [
        Page(file=Path(f"{title}.md"), slug=title, path=f"/posts/{title}/", permalink=f"/posts/{title}/", title=title)
        for title in titles
    ]


def titles(pages: list[Page]) -> list[str]:
    return [page.title for page in pages]


def html(public: Path, path: str = "") -> str:
    return (public / path / "index.html").read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# the paginator on its own


def test_pages_are_split_into_pagers():
    first, second = paginate(make_pages("1", "2", "3"), 2, "/posts/", "https://example.com/posts/")

    assert first.current_index == 1
    assert titles(first.pages) == ["1", "2"]
    assert first.path == "/posts/"

    assert second.current_index == 2
    assert titles(second.pages) == ["3"]
    assert second.path == "/posts/page/2/"


def test_pages_can_be_paginated_in_reverse():
    first, second = paginate(make_pages("1", "2", "3"), 2, "/posts/", "https://example.com/posts/", reversed=True)

    assert titles(first.pages) == ["3", "2"]
    assert titles(second.pages) == ["1"]


def test_paginator_for_the_index():
    first, second = paginate(make_pages("1", "2", "3"), 2, "/", "https://example.com/")

    assert first.path == "/"
    assert first.first == "https://example.com/"
    assert second.path == "/page/2/"
    assert second.last == "https://example.com/page/2/"


def test_paginator_variables():
    first, second = paginate(make_pages("1", "2", "3"), 2, "/posts/", "https://example.com/posts/")

    assert first.paginate_by == 2
    assert first.number_pagers == 2
    assert first.total_pages == 3
    assert first.base_url == "https://example.com/posts/page/"
    assert first.first == "https://example.com/posts/"
    assert first.last == "https://example.com/posts/page/2/"
    assert first.previous is None
    assert first.next == "https://example.com/posts/page/2/"

    assert second.previous == "https://example.com/posts/"
    assert second.next is None
    assert second.first == first.first
    assert second.last == first.last


def test_empty_paginate_path():
    first, second = paginate(make_pages("1", "2", "3"), 2, "/posts/", "https://example.com/posts/", paginate_path="")

    assert first.path == "/posts/"
    assert second.path == "/posts/2/"
    assert first.base_url == "https://example.com/posts/"


def test_no_pages_still_make_one_pager():
    (only,) = paginate([], 10, "/posts/", "https://example.com/posts/")

    assert only.pages == []
    assert only.number_pagers == 1
    assert only.total_pages == 0
    assert only.first == only.last == "https://example.com/posts/"
    assert only.previous is None
    assert only.next is None


def test_last_pager_is_never_empty():
    pagers = paginate(make_pages("1", "2", "3", "4"), 2, "/posts/", "https://example.com/posts/")
    assert [titles(pager.pages) for pager in pagers] == [["1", "2"], ["3", "4"]]


# a paginated section in the built site


def test_section_is_written_once_per_pager(public):
    assert (public / "posts" / "index.html").exists()
    assert (public / "posts" / "page" / "2" / "index.html").exists()
    assert (public / "posts" / "page" / "3" / "index.html").exists()
    assert not (public / "posts" / "page" / "4").exists()


def test_page_1_redirects_to_the_first_pager(public):
    redirect = html(public, "posts/page/1")

    assert '<meta http-equiv="refresh" content="0; url=https://example.com/posts/">' in redirect
    assert '<link rel="canonical" href="https://example.com/posts/">' in redirect
    assert "<title>Redirect</title>" in redirect
    assert '<a href="https://example.com/posts/">Click here</a>' in redirect


@pytest.mark.parametrize(
    "path, index, has_prev, has_next",
    [
        ("posts", 1, False, True),
        ("posts/page/2", 2, True, True),
        ("posts/page/3", 3, True, False),
    ],
)
def test_every_pager_sees_the_whole_pagination(public, path, index, has_prev, has_next):
    pager = html(public, path)

    assert "Num pagers: 3" in pager
    assert "Page size: 2" in pager
    assert f"Current index: {index}" in pager
    assert "Total pages: 6" in pager
    assert "First: https://example.com/posts/" in pager
    assert "Last: https://example.com/posts/page/3/" in pager
    assert "Base url: https://example.com/posts/page/" in pager
    assert ("has_prev" in pager) == has_prev
    assert ("has_next" in pager) == has_next


def test_previous_and_next_point_to_the_neighbours(public):
    middle = html(public, "posts/page/2")

    assert "has_prev: https://example.com/posts/" in middle
    assert "has_next: https://example.com/posts/page/3/" in middle


def test_pagers_hold_their_share_of_pages(public):
    assert "Pager pages: Simple;Python;" in html(public, "posts")
    assert "Pager pages: Fixed slug;Příliš žluťoučký kůň;" in html(public, "posts/page/2")
    assert "Pager pages: A post with dates;With assets;" in html(public, "posts/page/3")


def test_section_keeps_all_its_pages_on_every_pager(public):
    # unlike in Zola, section.pages stays complete, so get_section() and friends see the same thing everywhere
    assert "Pages: 6" in html(public, "posts/page/2")


def test_section_without_pages_still_gets_one_pager(public):
    paginated = html(public, "paginated")

    assert "Num pagers: 1" in paginated
    assert "Current index: 1" in paginated
    assert "Pager pages: \n" in paginated
    assert "has_next" not in paginated
    assert (public / "paginated" / "page" / "1" / "index.html").exists()
    assert not (public / "paginated" / "page" / "2").exists()


def test_reversed_pagination(public):
    assert "Num pagers: 5" in html(public, "reverse-paginated")
    assert "Pager pages: Page number: 9;Page number: 8;" in html(public, "reverse-paginated")
    assert "Pager pages: Page number: 1;" in html(public, "reverse-paginated/page/5")


def test_paginator_exists_only_when_paginating(public):
    assert "Num pagers" not in html(public, "posts/tutorials")
    assert not (public / "posts" / "tutorials" / "page").exists()


# taxonomies, categories have paginate_by = 1 in the test site's config.toml


def test_taxonomy_terms_can_be_paginated(public):
    assert "Pager pages: Python;" in html(public, "categories/a-category")
    assert "Num pagers: 2" in html(public, "categories/a-category")
    assert "Pager pages: Příliš žluťoučký kůň;" in html(public, "categories/a-category/page/2")
    assert "url=https://example.com/categories/a-category/" in html(public, "categories/a-category/page/1")
    assert "Num pagers: 1" in html(public, "categories/zlutoucky-kun")


def test_list_of_terms_is_not_paginated(public):
    assert "Num pagers" not in html(public, "categories")
    assert not (public / "categories" / "page").exists()


def test_taxonomy_without_paginate_by_is_not_paginated(public):
    # podcast_authors is a plain name in config.toml
    assert "Num pagers" not in html(public, "podcast-authors/some-person")
    assert not (public / "podcast-authors" / "some-person" / "page").exists()


# settings


def test_index_can_be_paginated(site_dir):
    write(site_dir / "content" / "_index.md", '+++\ntitle = "Home"\npaginate_by = 1\n+++\n')
    write(site_dir / "content" / "second.md", '+++\ntitle = "Second"\n+++\n')
    write(site_dir / "content" / "third.md", '+++\ntitle = "Third"\n+++\n')
    Site(site_dir).build()
    public = site_dir / "public"

    assert "Num pagers: 3" in html(public)
    assert "Last: https://example.com/page/3/" in html(public)
    assert "Current index: 2" in html(public, "page/2")
    assert '<meta http-equiv="refresh" content="0; url=https://example.com/">' in html(public, "page/1")


@pytest.mark.parametrize("paginate_path, second_pager", [("strana", "posts/strana/2"), ("", "posts/2")])
def test_paginate_path_can_be_changed(site_dir, paginate_path, second_pager):
    write(
        site_dir / "content" / "posts" / "_index.md",
        f'+++\ntitle = "Posts"\npaginate_by = 2\npaginate_path = "{paginate_path}"\n+++\n',
    )
    Site(site_dir).build()

    assert "Current index: 2" in html(site_dir / "public", second_pager)


@pytest.mark.parametrize("value", ["-1", '"2"'])
def test_paginate_by_must_be_a_positive_number(site_dir, value):
    write(site_dir / "content" / "posts" / "_index.md", f"+++\npaginate_by = {value}\n+++\n")
    with pytest.raises(HrabalError, match="paginate_by must be a positive number"):
        Site(site_dir).load()


@pytest.mark.parametrize(
    "taxonomies, error",
    [
        ('[{ name = "tags", per_page = 5 }]', "unknown taxonomy settings per_page"),
        ("[{ paginate_by = 5 }]", "every taxonomy needs a name"),
        ('[{ name = "tags", paginate_by = -5 }]', "paginate_by of tags must be a positive number"),
    ],
)
def test_taxonomy_settings_are_checked(site_dir, taxonomies, error):
    write(site_dir / "config.toml", f'base_url = "https://example.com"\ntaxonomies = {taxonomies}\n')
    with pytest.raises(HrabalError, match=error):
        Site(site_dir).load()
