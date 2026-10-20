import contextlib
import functools
import http.server
import shutil
import tempfile
import threading
import time
from pathlib import Path

from hrabal import HrabalError
from hrabal.site import Site

WATCHED = ["content", "templates", "static"]

# every page asks the server for the build number and reloads itself when it changes
LIVE_RELOAD = """<script>
(() => {
  let version;
  setInterval(async () => {
    try {
      const current = await (await fetch("/__hrabal/version")).text();
      if (version && current !== version) location.reload();
      version = current;
    } catch {}
  }, 500);
})();
</script>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    version = 0  # bumped after every successful rebuild

    def do_GET(self):
        if self.path != "/__hrabal/version":
            return super().do_GET()

        body = str(self.version).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # without this a browser can keep an old stylesheet after the live reload
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # one line per request is too noisy, the reload polling alone would flood the terminal


def serve(root: Path, interface: str, port: int, drafts: bool, base_url: str | None = None):
    # build somewhere else than public/, so a dev build with localhost urls never gets deployed by accident
    output = Path(tempfile.mkdtemp(prefix="hrabal-"))
    if not base_url:
        host = "localhost" if interface in ("0.0.0.0", "::") else interface
        base_url = f"http://{host}:{port}"
    base_url = base_url.rstrip("/")

    def build():
        started = time.perf_counter()
        Site(root, output_dir=output, drafts=drafts, base_url=base_url, inject_html=LIVE_RELOAD).build()
        return (time.perf_counter() - started) * 1000

    try:
        print(f"Built in {build():.0f} ms")
        try:
            server = http.server.ThreadingHTTPServer((interface, port), functools.partial(Handler, directory=output))
        except OSError as e:
            raise HrabalError(f"cannot listen on port {port}: {e.strerror}") from None
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Serving at {base_url}/, press Ctrl+C to stop")

        watch(root, build)
    except KeyboardInterrupt:
        print()
    finally:
        shutil.rmtree(output, ignore_errors=True)


def watch(root: Path, build):
    last = snapshot(root)
    while True:
        time.sleep(0.3)
        current = snapshot(root)
        if current == last:
            continue
        last = current

        try:
            took = build()
        except HrabalError as e:
            print(f"error: {e}")
            continue
        Handler.version += 1
        print(f"Rebuilt in {took:.0f} ms")


def snapshot(root: Path) -> dict[Path, int]:
    files = [root / "config.toml"]
    for name in WATCHED:
        files.extend((root / name).rglob("*"))

    mtimes = {}
    for file in files:
        with contextlib.suppress(FileNotFoundError):  # deleted while we were looking
            mtimes[file] = file.stat().st_mtime_ns
    return mtimes
