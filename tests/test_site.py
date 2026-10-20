import shutil
from pathlib import Path

import pytest

from hrabal import HrabalError
from hrabal.cli import STARTER
from hrabal.content import slugify
from hrabal.site import Site


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    shutil.copytree(STARTER, tmp_path / "site")
    return tmp_path / "site"


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_starter_site_builds(site_dir):
    Site(site_dir).build()
    public = site_dir / "public"

    assert (public / "index.html").exists()
    assert (public / "about" / "index.html").exists()
    assert (public / "blog" / "prilis-hlucna-samota" / "index.html").exists()
    assert (public / "blog" / "a-picture" / "drawing.svg").exists()
    assert (public / "tags" / "hrabal" / "index.html").exists()
    assert (public / "style.css").exists()


def test_drafts_are_skipped_unless_asked_for(site_dir):
    site = Site(site_dir)
    site.load()
    assert "blog/unfinished.md" not in site.pages

    site = Site(site_dir, drafts=True)
    site.load()
    assert "blog/unfinished.md" in site.pages


def test_pages_are_sorted_newest_first(site_dir):
    site = Site(site_dir)
    site.load()
    blog = site.sections["blog/_index.md"]

    assert [p.slug for p in blog.pages] == ["a-picture", "prilis-hlucna-samota"]
    assert blog.pages[0].next is blog.pages[1]
    assert blog.pages[1].previous is blog.pages[0]


def test_internal_links_are_resolved(site_dir):
    site = Site(site_dir)
    site.load()

    about = site.pages["about.md"]
    assert 'href="https://example.com/blog/prilis-hlucna-samota/"' in about.content


def test_broken_internal_link_stops_the_build(site_dir):
    write(site_dir / "content" / "oops.md", "[nowhere](@/missing.md)")

    with pytest.raises(HrabalError, match="broken internal link"):
        Site(site_dir).load()


def test_unknown_front_matter_is_an_error(site_dir):
    write(site_dir / "content" / "typo.md", '+++\ntitel = "Typo"\n+++\n')

    with pytest.raises(HrabalError, match="titel"):
        Site(site_dir).load()


def test_summary_is_everything_before_more(site_dir):
    site = Site(site_dir)
    site.load()
    post = site.pages["blog/prilis-hlucna-samota.md"]

    assert "summary shown in post lists" in post.summary
    assert "Pygments" not in post.summary


@pytest.mark.parametrize(
    "text, slug",
    [
        ("Hello World", "hello-world"),
        ("Příliš žluťoučký kůň", "prilis-zlutoucky-kun"),
        ("  --Spaces & symbols!-- ", "spaces-symbols"),
    ],
)
def test_slugify(text, slug):
    assert slugify(text) == slug
