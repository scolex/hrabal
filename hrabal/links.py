# hrabal check: do the links to other sites still work? Internal links are checked by every build,
# these only when asked, since it takes the network and a while, and someone else's server being down
# shouldn't stop anyone from publishing.

import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

from hrabal import __version__

TIMEOUT = 10  # seconds per request
WORKERS = 8  # links checked at once
HEADERS = {"User-Agent": f"hrabal/{__version__} (link checker)"}


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value and value.startswith(("http://", "https://")):
                self.links.append(value)


def external_links(html: str) -> list[str]:
    # every link and image going to another site, from markdown and from HTML written by hand alike
    collector = LinkCollector()
    collector.feed(html)
    return collector.links


def check_url(url: str) -> str | None:
    # None when the link works, otherwise what went wrong
    problem = None
    for method in ("HEAD", "GET"):  # plenty of servers don't like HEAD, so they get a second, ordinary try
        try:
            fetch(url, method)
            return None
        except urllib.error.HTTPError as e:
            problem = f"{e.code} {e.reason}"
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            return describe(e)  # no server, or no answer, asking again won't help
    return problem


def fetch(url: str, method: str):
    request = urllib.request.Request(url, method=method, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT):
        pass  # redirects are followed, getting here means the page is there


def describe(error: Exception) -> str:
    reason = getattr(error, "reason", error)  # a URLError carries what really happened
    if isinstance(reason, TimeoutError):
        return "timed out"
    return getattr(reason, "strerror", None) or str(reason)


def find_broken(items, skip_prefixes: list[str]) -> tuple[int, list[tuple[str, str, str]]]:
    # items are pages and sections, gives back how many links were checked and (file, url, problem)
    # for each broken one. A link used on many pages is checked only once.
    used_in: dict[str, list[str]] = {}
    for item in items:
        for url in external_links(item.content):
            if url.startswith(tuple(skip_prefixes)):
                continue
            files = used_in.setdefault(url, [])
            if str(item.file) not in files:
                files.append(str(item.file))

    with ThreadPoolExecutor(WORKERS) as pool:
        problems = dict(zip(used_in, pool.map(check_url, used_in), strict=True))

    broken = [(file, url, problem) for url, problem in problems.items() if problem for file in used_in[url]]
    return len(used_in), sorted(broken)
