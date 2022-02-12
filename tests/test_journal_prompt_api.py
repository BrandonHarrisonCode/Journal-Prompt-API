"Tests the main journal prompt file"
from journal_prompt_api import __version__


def test_version() -> None:
    "Ensure that we are updating the version string"
    assert __version__ == "0.1.0"
