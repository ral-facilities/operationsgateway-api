import os

import pytest


@pytest.fixture(scope="function")
def remove_hdf_file():
    yield
    if os.path.exists("test.h5"):
        os.remove("test.h5")
