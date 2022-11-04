import warnings

import pytest


def test_pass():
    assert True


def test_fail():
    assert False


def test_setup_error(nonexistent_fixture):
    pass


@pytest.fixture
def teardown_error_fixture():
    yield
    raise Exception("error")


def test_teardown_error(teardown_error_fixture):
    pass


@pytest.mark.skip
def test_skip_no_reason():
    ...


@pytest.mark.skip(reason="skipped")
def test_skip():
    ...


@pytest.mark.skip("skipped")
def test_skip_no_keyword():
    ...


def test_inline_skip():
    pytest.skip("skipped")


@pytest.mark.xfail
def test_xfail_no_reason():
    assert False


@pytest.mark.xfail(reason="xfail")
def test_xfail():
    assert False


def test_inline_xfail():
    pytest.xfail("xfail")


@pytest.mark.xfail(reason="xpass")
def test_xpass():
    assert True


def test_nested_failure():
    def inner():
        assert False

    inner()


# These two tests raise an `AssertionError`, so they are commented out
# for now. They will be uncommented once the `AssertionError` is
# handled.
# Related issue: https://github.com/nicoddemus/pytest-rich/issues/44

# def test_doubly_nested_failures():
#     def inner():
#         def inner_inner():
#             assert False
#         inner_inner()
#     inner()


# def test_triply_nested_failures():
#     def inner():
#         def inner_inner():
#             def inner_inner_inner():
#                 assert False
#             inner_inner_inner()
#         inner_inner()
#     inner()


def test_warning():
    warnings.warn("warning")
