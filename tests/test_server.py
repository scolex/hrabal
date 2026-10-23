import functools
import http.server
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from hrabal.server import Handler


@pytest.fixture
def server_url(tmp_path: Path):
    (tmp_path / "style.css").write_text("body { color: black; }")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=tmp_path))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_files_are_not_cached(server_url):
    with urllib.request.urlopen(f"{server_url}/style.css") as response:
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.read() == b"body { color: black; }"


def test_version_tells_pages_when_to_reload(server_url, monkeypatch):
    monkeypatch.setattr(Handler, "version", 7)
    with urllib.request.urlopen(f"{server_url}/__hrabal/version") as response:
        assert response.read() == b"7"
        assert response.headers["Cache-Control"] == "no-cache"


def test_missing_page_gets_the_sites_404_page(server_url, tmp_path):
    (tmp_path / "404.html").write_text("<h1>Page not found</h1>")

    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(f"{server_url}/nowhere/")
    assert error.value.code == 404
    assert error.value.read() == b"<h1>Page not found</h1>"


def test_without_a_404_page_the_plain_error_stays(server_url):
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(f"{server_url}/nowhere/")
    assert error.value.code == 404
    assert b"Page not found" not in error.value.read()
