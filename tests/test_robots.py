# robots.txt, with the checks Zola's site tests make on its own

from pathlib import Path

from hrabal.site import Site


def configure(site_dir: Path, line: str):
    config = site_dir / "config.toml"
    config.write_text(line + "\n" + config.read_text())


def test_robots_txt_lets_everyone_in_and_points_at_the_sitemap(public):
    assert (public / "robots.txt").read_text() == (
        "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
    )


def test_sitemap_line_follows_the_base_url(site_dir, tmp_path):
    output = tmp_path / "dev"
    Site(site_dir, output_dir=output, base_url="http://localhost:1111").build()

    assert "Sitemap: http://localhost:1111/sitemap.xml" in (output / "robots.txt").read_text()


def test_no_sitemap_no_sitemap_line(site_dir):
    configure(site_dir, "generate_sitemap = false")
    Site(site_dir).build()

    assert "Sitemap" not in (site_dir / "public" / "robots.txt").read_text()


def test_site_can_bring_its_own_robots_txt(site_dir):
    (site_dir / "templates" / "robots.txt").write_text(
        "User-agent: hrabal\nDisallow: /secret/\nSitemap: {{ get_url('sitemap.xml') }}\n"
    )
    Site(site_dir).build()

    robots = (site_dir / "public" / "robots.txt").read_text()
    assert robots.startswith("User-agent: hrabal\nDisallow: /secret/\n")
    assert "Sitemap: https://example.com/sitemap.xml" in robots


def test_robots_txt_can_be_turned_off(site_dir):
    configure(site_dir, "generate_robots_txt = false")
    Site(site_dir).build()

    assert not (site_dir / "public" / "robots.txt").exists()


def test_robots_txt_is_not_in_the_sitemap(public):
    assert "robots.txt" not in (public / "sitemap.xml").read_text()
