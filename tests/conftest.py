import os
import sys

import pytest

test_dir = os.path.abspath(os.path.dirname(__file__))
repo = os.path.abspath(os.path.join(test_dir, os.pardir))
sys.path.insert(0, repo)


@pytest.fixture
def here():
    return test_dir
