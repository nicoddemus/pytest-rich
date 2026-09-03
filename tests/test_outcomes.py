from __future__ import annotations

import pytest


def test_outcomes(pytester):
    """Sanity check: the example file produces the expected outcomes."""
    pytester.copy_example("test_basic.py")
    result = pytester.runpytest()
    result.assert_outcomes(
        passed=3,
        skipped=4,
        failed=4,
        errors=2,
        xpassed=1,
        xfailed=3,
    )


def test_outcomes_rich(rich_pytester, assert_rich_outcomes):
    """The Rich panel must report the same outcomes as the stock reporter."""
    rich_pytester.copy_example("test_basic.py")
    result = rich_pytester.runpytest()
    assert_rich_outcomes(
        result, passed=3, failed=4, skipped=4, xfailed=3, xpassed=1
    )


def test_outcomes_rich_shows_errors(rich_pytester, assert_rich_outcomes):
    rich_pytester.copy_example("test_basic.py")
    result = rich_pytester.runpytest()
    assert_rich_outcomes(result, errors=2)


def test_collect_error_outcomes(pytester):
    """Stock pytest must report collection errors as errors in outcomes."""
    pytester.makepyfile("""
    raise Exception("collect error")
    """)
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)


@pytest.mark.parametrize(
    "k_expr, expected_outcomes, expected_ret",
    [
        pytest.param("test_skip_decorator", {"skipped": 1}, 0, id="skip-decorator"),
        pytest.param("test_skip_inline", {"skipped": 1}, 0, id="skip-inline"),
        pytest.param("test_xfail_expected", {"xfailed": 1}, 0, id="xfail"),
        pytest.param("test_xpass_unexpected", {"xpassed": 1}, 0, id="xpass"),
        pytest.param("test_xpass_strict", {"failed": 1}, 1, id="xpass-strict"),
    ],
)
def test_skip_xfail_do_not_crash(
    rich_pytester, assert_rich_outcomes, k_expr, expected_outcomes, expected_ret
):
    rich_pytester.copy_example("test_skip_xfail.py")
    result = rich_pytester.runpytest("-k", k_expr)
    assert result.ret == expected_ret
    assert_rich_outcomes(result, **expected_outcomes)
    result.stdout.fnmatch_lines(["*Summary*"])
