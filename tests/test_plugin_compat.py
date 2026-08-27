from __future__ import annotations


def test_survives_makereport_hookwrapper_mutating_nodeid(rich_pytester):
    """A plugin's makereport hookwrapper rewriting report.nodeid must not crash rich.

    Regression test for #74: a hookwrapper that swaps ``report.nodeid`` for a
    display-only string (e.g. to prepend a docstring) made ``_update_task``
    derive a bogus file path and KeyError on ``runtest_tasks_per_file``,
    aborting the whole run with an INTERNALERROR. The progress row must also
    still advance — surviving the mutation by silently dropping updates is not
    enough.
    """
    rich_pytester.makepyfile(nodeid_mutator="""
        import pytest

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(item, call):
            outcome = yield
            report = outcome.get_result()
            report.nodeid = f"custom docstring <- {report.nodeid.split('::')[0]}"
    """)
    rich_pytester.makepyfile("""
        def test_one_plus_one_equals_2():
            assert 1 == 1
    """)
    rich_pytester.syspathinsert()
    result = rich_pytester.runpytest("-p", "nodeid_mutator")
    result.stdout.no_fnmatch_line("*INTERNALERROR*")
    result.stdout.fnmatch_lines(
        ["*100%*test_survives_makereport_hookwrapper_mutating_nodeid.py*"]
    )
    assert result.ret == 0


def test_progress_completes_with_deselected_tests(rich_pytester):
    """Deselected tests must not keep the per-file progress below 100%."""
    rich_pytester.makepyfile("""
        def test_selected():
            pass

        def test_deselected():
            pass
    """)
    result = rich_pytester.runpytest("-k", "test_selected")
    assert result.ret == 0
    result.stdout.fnmatch_lines(
        ["*100%*test_progress_completes_with_deselected_tests.py*"]
    )
