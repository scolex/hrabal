import datetime
import os
import shutil
from pathlib import Path

import pytest

from hrabal.site import Site

# a small site in the spirit of Zola's test_site, see tests/test_site/
TEST_SITE = Path(__file__).parent / "test_site"

# pages without updated in their front matter take their file's modification date, which would otherwise
# be whenever the repository was cloned, so every copy gets this one instead
FILE_TIME = datetime.datetime(2000, 1, 1, 12, 0).timestamp()


def copy_test_site(target: Path) -> Path:
    shutil.copytree(TEST_SITE, target)
    for file in target.rglob("*"):
        os.utime(file, (FILE_TIME, FILE_TIME))
    return target


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    # a fresh copy for every test, so a test can add or break files without touching the original
    return copy_test_site(tmp_path / "site")


@pytest.fixture(scope="session")
def public(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # built once for all the tests that only read the output
    root = copy_test_site(tmp_path_factory.mktemp("built") / "site")
    Site(root).build()
    return root / "public"
