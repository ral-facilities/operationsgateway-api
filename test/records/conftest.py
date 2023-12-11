import pytest_asyncio
import pytest

import os


@pytest.fixture(scope="function")
def remove_HDF_file():
    yield
    if os.path.exists("test.h5"):
        os.remove("test.h5")
