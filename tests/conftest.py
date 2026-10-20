import shutil
from pathlib import Path

import pytest

from hrabal.site import Site

# a small site in the spirit of Zola's test_site, see tests/test_site/
TEST_SITE = Path(__file__).parent / "test_site"


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    # a fresh copy for every test, so a test can add or break files without touching the original
    return shutil.copytree(TEST_SITE, tmp_path / "site")


@pytest.fixture(scope="session")
def public(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # built once for all the tests that only read the output
    root = shutil.copytree(TEST_SITE, tmp_path_factory.mktemp("built") / "site")
    Site(root).build()
    return root / "public"
