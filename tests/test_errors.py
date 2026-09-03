from __future__ import annotations


def test_collect_error(rich_pytester):
    rich_pytester.makepyfile("""
    raise Exception("collect error")
    """)
    result = rich_pytester.runpytest()
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*ERROR collecting*"])


def test_collect_error_shown_with_no_summary(rich_pytester):
    """Collection errors must be visible even when --no-summary is used."""
    rich_pytester.makepyfile("""
    raise Exception("collect error")
    """)
    result = rich_pytester.runpytest("--no-summary")
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*ERROR collecting*"])


def test_captured_output_shown_on_failure(rich_pytester):
    """Captured stdout/stderr must be shown for failed tests, like stock pytest (#77)."""
    rich_pytester.makepyfile("""
        import sys

        def test_fail_with_output():
            print("hello from stdout")
            print("hello from stderr", file=sys.stderr)
            assert False
    """)
    result = rich_pytester.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*Captured stdout call*",
        "*hello from stdout*",
        "*Captured stderr call*",
        "*hello from stderr*",
    ])


def test_show_capture_stdout_hides_stderr(rich_pytester):
    """--show-capture=<stream> must show only that stream's sections (#13)."""
    rich_pytester.makepyfile("""
        import sys

        def test_fail_with_output():
            print("hello from stdout")
            print("hello from stderr", file=sys.stderr)
            assert False
    """)
    result = rich_pytester.runpytest("--show-capture=stdout")
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*Captured stdout call*", "*hello from stdout*"])
    result.stdout.no_fnmatch_line("*Captured stderr*")


def test_show_capture_no_hides_captured_output(rich_pytester):
    """--show-capture=no must suppress captured output sections (#13)."""
    rich_pytester.makepyfile("""
        def test_fail_with_output():
            print("hello from stdout")
            assert False
    """)
    result = rich_pytester.runpytest("--show-capture=no")
    assert result.ret == 1
    result.stdout.no_fnmatch_line("*Captured stdout call*")


class TestSetupTeardownErrors:

    def test_setup_error_reported(self, rich_pytester, assert_rich_outcomes):
        rich_pytester.copy_example("test_basic.py")
        result = rich_pytester.runpytest("-k", "test_setup_error")
        assert result.ret != 0
        assert_rich_outcomes(result, errors=1)
        result.stdout.fnmatch_lines(["*ERROR at setup of*test_setup_error*"])

    def test_teardown_error_reported(self, rich_pytester, assert_rich_outcomes):
        rich_pytester.copy_example("test_basic.py")
        result = rich_pytester.runpytest("-k", "test_teardown_error")
        assert result.ret != 0
        assert_rich_outcomes(result, errors=1)
        result.stdout.fnmatch_lines(["*ERROR at teardown of*test_teardown_error*"])

    def test_error_shows_captured_output(self, rich_pytester):
        """Output captured before a fixture blows up must survive (#77)."""
        rich_pytester.makepyfile("""
            import pytest

            @pytest.fixture
            def broken():
                print("diagnostic before the crash")
                raise RuntimeError("boom")

            def test_needs_fixture(broken):
                pass
        """)
        result = rich_pytester.runpytest()
        assert result.ret != 0
        result.stdout.fnmatch_lines([
            "*ERROR at setup of*",
            "*Captured stdout setup*",
            "*diagnostic before the crash*",
        ])


class TestCollectionErrors:

    def test_partial_collection_error_shows_details(self, rich_pytester):
        rich_pytester.makepyfile(
            test_good="def test_pass(): pass",
            test_broken="raise ImportError('boom')",
        )
        result = rich_pytester.runpytest()
        assert result.ret != 0
        result.stdout.fnmatch_lines([
            "*ERROR collecting*test_broken*",
            "*ImportError: boom*",
        ])
