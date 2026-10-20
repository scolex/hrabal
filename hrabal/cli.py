import argparse
import shutil
import sys
import time
from pathlib import Path

from hrabal import HrabalError, __version__
from hrabal.server import serve
from hrabal.site import Site

STARTER = Path(__file__).parent / "starter"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hrabal", description="A small static site generator.")
    parser.add_argument("--version", action="version", version=f"hrabal {__version__}")
    parser.add_argument("-r", "--root", type=Path, default=Path("."), help="site directory (default: current one)")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a new site")
    init.add_argument("directory", type=Path)

    build = commands.add_parser("build", help="build the site into public/")
    build.add_argument("--drafts", action="store_true", help="include draft pages")

    serve_ = commands.add_parser("serve", help="serve the site and rebuild it on every change")
    serve_.add_argument("-i", "--interface", default="127.0.0.1", help="use 0.0.0.0 inside docker")
    serve_.add_argument("-p", "--port", type=int, default=1111)
    serve_.add_argument("-u", "--base-url", help="the address you open in the browser, if it isn't localhost")
    serve_.add_argument("--drafts", action="store_true", help="include draft pages")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init_site(args.directory)
        elif args.command == "build":
            build_site(args.root, args.drafts)
        elif args.command == "serve":
            serve(args.root, args.interface, args.port, args.drafts, args.base_url)
    except HrabalError as e:
        sys.exit(f"error: {e}")


def init_site(directory: Path):
    if directory.exists() and any(directory.iterdir()):
        raise HrabalError(f"{directory} is not empty")

    shutil.copytree(STARTER, directory, dirs_exist_ok=True)
    print(f"Created a new site in {directory}, try:")
    print(f"  cd {directory}")
    print("  hrabal serve")


def build_site(root: Path, drafts: bool):
    started = time.perf_counter()
    site = Site(root, drafts=drafts)
    site.build()
    took = (time.perf_counter() - started) * 1000
    print(f"Built {len(site.pages)} pages and {len(site.sections)} sections in {took:.0f} ms")
