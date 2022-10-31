import pytest


def test_pass():
    assert True


def test_fail():
    assert False


def test_error():
    raise Exception("error")


@pytest.mark.skip(reason="skipped")
def test_skip():
    ...


@pytest.mark.xfail(reason="xfail")
def test_xfail():
    assert False


@pytest.mark.xfail(reason="xpass")
def test_xpass():
    assert True
