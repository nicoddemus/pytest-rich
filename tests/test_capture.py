from datetime import datetime
from datetime import timezone

import pytest
from freezegun import freeze_time

from pytest_rich.capture import _get_filename_from_arg

NOW = datetime.now(timezone.utc)
TIMESTAMP = NOW.strftime("%Y%m%d_%H%M%S")


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
@freeze_time(NOW)
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


def test_capture_includes_progress_output(rich_pytester):
    """Collect and runtest progress must appear in the --rich-capture export (#51).

    The Progress bars used to render to Rich's global console instead of the
    reporter's recording console, so those sections came out blank in the
    exported file.
    """
    rich_pytester.makepyfile("""
        def test_pass():
            pass
    """)
    result = rich_pytester.runpytest("--rich-capture=out.txt")
    assert result.ret == 0
    captured = (rich_pytester.path / "out.txt").read_text(encoding="utf-8")
    assert "Collected 1 items" in captured
    assert "test_capture_includes_progress_output.py" in captured
    assert "100%" in captured
