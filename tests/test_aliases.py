# aliases in the front matter: old addresses of a page or section that send readers on to where it is now

import pytest

from hrabal import HrabalError
from hrabal.site import Site


def read(public, path: str) -> str:
    return (public / path).read_text(encoding="utf-8")


def test_alias_becomes_a_redirect_folder(public):
    redirect = read(public, "an-old-url/old-page/index.html")

    assert '<meta http-equiv="refresh" content="0; url=https://example.com/posts/something-else/">' in redirect
    assert '<link rel="canonical" href="https://example.com/posts/something-else/">' in redirect


def test_alias_ending_in_html_stays_a_file(public):
    redirect = read(public, "an-old-url/an-old-alias.html")
    assert "url=https://example.com/posts/something-else/" in redirect


def test_sections_can_have_aliases_too(public):
    assert "url=https://example.com/posts/tutorials/" in read(public, "learn/index.html")


def test_aliases_stay_out_of_the_sitemap(public):
    sitemap = read(public, "sitemap.xml")
    assert "an-old-url" not in sitemap
    assert "/learn/" not in sitemap


def write_page(site_dir, aliases: str):
    text = f'+++\ntitle = "Moved"\naliases = {aliases}\n+++\n'
    (site_dir / "content" / "moved.md").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("aliases", "error"),
    [
        ('"/old/"', "aliases is a list of addresses"),
        ("[1]", "aliases is a list of addresses"),
        ('["https://example.com/old/"]', "has to be an address on this site"),
        ('["/../outside/"]', "has to be an address on this site"),
        ('["/"]', "has to be an address on this site"),
    ],
)
def test_aliases_are_checked(site_dir, aliases, error):
    write_page(site_dir, aliases)
    with pytest.raises(HrabalError, match=error):
        Site(site_dir).load()


@pytest.mark.parametrize("alias", ["/posts/", "/posts/python", "/learn/"])
def test_alias_cannot_take_an_address_that_is_in_use(site_dir, alias):
    write_page(site_dir, f'["{alias}"]')
    with pytest.raises(HrabalError, match=f"alias {alias} is already the address of something else"):
        Site(site_dir).build()
