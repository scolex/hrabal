import functools
import http.server
import threading
import urllib.request
from pathlib import Path

import pytest

from hrabal.server import Handler


@pytest.fixture
def server_url(tmp_path: Path):
    (tmp_path / "style.css").write_text("body { color: black; }", encoding="utf-8")
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
