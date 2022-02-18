import time

import pytest

# time.sleep(1)
@pytest.mark.parametrize("i", range(10))
def test_bar(i):
    # if i == 2:
    #    assert 0, "Some failure"
    time.sleep(0.02)
