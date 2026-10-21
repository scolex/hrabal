# hrabal check and its links to other sites, tried against a small server of our own instead of the internet

import http.server
import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from hrabal.cli import main
from hrabal.links import check_url, external_links, find_broken


class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path == "/no-head":
            self.send_response(405)  # like servers that only answer GET
        else:
            self.answer()
        self.end_headers()

    def do_GET(self):
        self.answer()
        self.end_headers()

    def answer(self):
        if self.path in ("/ok", "/no-head"):
            self.send_response(200)
        elif self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/ok")
        else:
            self.send_response(404)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_external_links_come_from_links_and_images():
    html = '<a href="https://a.cz/">a</a> <img src="http://b.cz/x.png"> <a href="/inside/">c</a> <a href="#top">d</a>'
    assert external_links(html) == ["https://a.cz/", "http://b.cz/x.png"]


def test_working_links(server):
    assert check_url(f"{server}/ok") is None
    assert check_url(f"{server}/moved") is None  # redirects are followed
    assert check_url(f"{server}/ok#heading") is None


def test_server_without_head_gets_a_get(server):
    assert check_url(f"{server}/no-head") is None


def test_broken_links_say_why(server):
    assert check_url(f"{server}/missing") == "404 Not Found"
    assert check_url(f"http://127.0.0.1:{closed_port()}/") == "Connection refused"


def page(file: str, content: str):
    return SimpleNamespace(file=Path(file), content=content)


def test_find_broken_checks_every_link_once_and_names_every_page(server):
    missing = f'<a href="{server}/missing">x</a>'
    items = [
        page("content/a.md", missing + missing),
        page("content/b.md", missing + f'<a href="{server}/ok">ok</a>'),
    ]
    checked, broken = find_broken(items, skip_prefixes=[])

    assert checked == 2
    assert broken == [
        ("content/a.md", f"{server}/missing", "404 Not Found"),
        ("content/b.md", f"{server}/missing", "404 Not Found"),
    ]


def test_skip_prefixes(server):
    items = [page("content/a.md", f'<a href="{server}/missing">x</a>')]
    assert find_broken(items, skip_prefixes=[server]) == (0, [])


def make_site(root: Path, links: str, config: str = ""):
    (root / "content").mkdir(parents=True)
    (root / "config.toml").write_text(f'base_url = "https://example.com"\n{config}', encoding="utf-8")
    (root / "content" / "_index.md").write_text(links, encoding="utf-8")
    return root


def test_check_command_lists_broken_links(server, tmp_path, capsys):
    root = make_site(tmp_path / "site", f"[fine]({server}/ok) and [gone]({server}/missing)\n")

    with pytest.raises(SystemExit, match="1 broken of 2 links to other sites"):
        main(["-r", str(root), "check"])
    assert f"content/_index.md: {server}/missing (404 Not Found)" in capsys.readouterr().out
    assert not (root / "public").exists()  # only checked, nothing written


def test_check_command_is_happy_when_all_work(server, tmp_path, capsys):
    config = f'[link_checker]\nskip_prefixes = ["{server}/missing"]\n'
    root = make_site(tmp_path / "site", f"[fine]({server}/ok) and [skipped]({server}/missing)\n", config)

    main(["-r", str(root), "check"])
    assert "Checked 1 link to other sites, none is broken" in capsys.readouterr().out


def test_check_command_leaves_out_the_sites_own_links(server, tmp_path, capsys):
    (tmp_path / "site" / "content").mkdir(parents=True)
    (tmp_path / "site" / "content" / "about.md").write_text("About\n", encoding="utf-8")
    links = f"[about](@/about.md), [by hand](https://example.com/about/) and [gone]({server}/missing)\n"
    (tmp_path / "site" / "content" / "_index.md").write_text(links, encoding="utf-8")
    (tmp_path / "site" / "config.toml").write_text('base_url = "https://example.com"\n', encoding="utf-8")

    with pytest.raises(SystemExit, match="1 broken of 1 links"):
        main(["-r", str(tmp_path / "site"), "check"])
    assert "example.com" not in capsys.readouterr().out


def test_check_command_checks_internal_links_too(tmp_path):
    root = make_site(tmp_path / "site", "[nowhere](@/missing.md)\n")
    with pytest.raises(SystemExit, match=r"missing\.md"):
        main(["-r", str(root), "check"])


def test_link_checker_settings_are_checked(tmp_path):
    root = make_site(tmp_path / "site", "", '[link_checker]\nskip_prefixes = "https://"\n')
    with pytest.raises(SystemExit, match="skip_prefixes is a list of addresses"):
        main(["-r", str(root), "check"])
