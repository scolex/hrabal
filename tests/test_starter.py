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


def test_starter_blog_is_paginated(starter_dir):
    Site(starter_dir).build()
    blog = starter_dir / "public" / "blog"

    listing = (blog / "index.html").read_text(encoding="utf-8")
    assert "Příliš hlučná samota" in listing
    assert "Older" not in listing  # just one pager, so nowhere to go
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

    assert [p.slug for p in blog.pages] == ["a-picture", "prilis-hlucna-samota"]
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
