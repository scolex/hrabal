# sitemap.xml, with the checks Zola's site tests make on its own sitemap

import xml.etree.ElementTree as ET
from pathlib import Path

from hrabal.site import Site

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def read_sitemap(public: Path) -> dict[str, str | None]:
    root = ET.parse(public / "sitemap.xml").getroot()
    return {url.findtext("s:loc", "", NS): url.findtext("s:lastmod", namespaces=NS) for url in root}


def test_pages_and_sections_are_in_the_sitemap(public):
    urls = read_sitemap(public)

    assert "https://example.com/" in urls
    assert "https://example.com/posts/" in urls
    assert "https://example.com/posts/simple/" in urls
    assert "https://example.com/posts/tutorials/devops/nix/" in urls


def test_every_built_page_is_listed_except_redirects(public):
    built = {path.parent.relative_to(public).as_posix() for path in public.rglob("index.html")}
    redirects = {path for path in built if path.endswith("page/1")}
    listed = {url.removeprefix("https://example.com/").rstrip("/") for url in read_sitemap(public)}

    assert redirects  # the test site does paginate
    assert listed == {"" if path == "." else path for path in built - redirects}


def test_pagers_and_taxonomies_are_in_the_sitemap(public):
    urls = read_sitemap(public)

    assert "https://example.com/posts/page/2/" in urls
    assert "https://example.com/posts/page/3/" in urls
    assert "https://example.com/posts/page/1/" not in urls  # only a redirect
    assert "https://example.com/categories/" in urls
    assert "https://example.com/categories/a-category/" in urls
    assert "https://example.com/categories/a-category/page/2/" in urls


def test_dated_pages_have_lastmod(public):
    urls = read_sitemap(public)

    assert urls["https://example.com/posts/python/"] == "2017-03-01"
    assert urls["https://example.com/posts/a-post-with-dates/"] == "2016-10-08"
    assert urls["https://example.com/hello/"] is None


def test_drafts_are_in_the_sitemap_only_when_built(public, site_dir, tmp_path):
    assert not any("draft" in url or "secret" in url for url in read_sitemap(public))

    output = tmp_path / "with-drafts"
    Site(site_dir, output_dir=output, drafts=True).build()
    urls = read_sitemap(output)
    assert "https://example.com/posts/draft/" in urls
    assert "https://example.com/secret-section/secret-sub-section/hello/" in urls


def test_sitemap_follows_the_base_url(site_dir, tmp_path):
    output = tmp_path / "dev"
    Site(site_dir, output_dir=output, base_url="http://localhost:1111").build()

    assert all(url.startswith("http://localhost:1111/") for url in read_sitemap(output))


def test_site_can_bring_its_own_sitemap_template(site_dir):
    (site_dir / "templates" / "sitemap.xml").write_text("{{ entries | length }} urls", encoding="utf-8")
    Site(site_dir).build()

    assert (site_dir / "public" / "sitemap.xml").read_text(encoding="utf-8") == "46 urls"


def test_sitemap_can_be_turned_off(site_dir):
    config = site_dir / "config.toml"
    config.write_text("generate_sitemap = false\n" + config.read_text(encoding="utf-8"), encoding="utf-8")
    Site(site_dir).build()

    assert not (site_dir / "public" / "sitemap.xml").exists()
