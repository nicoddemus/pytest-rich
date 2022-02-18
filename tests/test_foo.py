import time

import pytest

# time.sleep(1)
def check(i):
    if i % 2 != 0:
        raise ValueError("number is odd")


@pytest.mark.parametrize("i", range(8))
def test_foo(i):
    # check(i)
    time.sleep(0.025)
