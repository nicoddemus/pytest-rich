from datetime import datetime

import pytest

from pytest_rich.capture import _get_filename_from_arg

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


@pytest.mark.parametrize(
    "arg, expected",
    [
        ("", (f"pytest_rich-{TIMESTAMP}", "svg")),
        (".html", (f"pytest_rich-{TIMESTAMP}", "html")),
        ("html", (f"pytest_rich-{TIMESTAMP}", "html")),
        ("out", ("out", "svg")),
        ("out.txt", ("out", "txt")),
    ],
)
def test_get_filename_from_arg(arg: str, expected: str) -> None:
    """Test _get_filename_from_arg."""
    assert _get_filename_from_arg(arg) == expected


@pytest.mark.parametrize(
    "arg",
    [
        "out.pdf",
        ".pdf",
    ],
)
def test_get_filename_from_arg_invalid_filetype(arg: str) -> None:
    """Test _get_filename_from_arg with invalid file type."""
    with pytest.raises(ValueError):
        _get_filename_from_arg(arg)
