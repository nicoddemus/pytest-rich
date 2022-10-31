def test_outcomes(pytester):
    pytester.copy_example("test_basic.py")

    outcomes = {
        "passed": 2,
        "skipped": 4,
        "failed": 2,
        "errors": 2,
        "xpassed": 1,
        "xfailed": 3,
    }

    without_rich = pytester.runpytest()
    with_rich = pytester.runpytest("--rich")

    without_rich.assert_outcomes(**outcomes) == with_rich.assert_outcomes(**outcomes)


def test_collect_error(pytester):
    pytester.makepyfile(
        """
    raise Exception("collect error")
    """
    )

    without_rich = pytester.runpytest()
    with_rich = pytester.runpytest("--rich")

    without_rich.assert_outcomes(errors=1) == with_rich.assert_outcomes(errors=1)
