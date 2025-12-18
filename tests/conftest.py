import os
from typing import Any, Callable, List, Optional

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests (need docker services up)")


@pytest.fixture(scope="session")
def api_url():
    return os.getenv("API_URL", "http://localhost")


class MockRunResult:
    """
    Minimal neo4j result stub supporting .data() and .single().
    """

    def __init__(self, data_rows: Optional[List[dict]] = None, single_row: Optional[dict] = None):
        self._data_rows = data_rows or []
        self._single_row = single_row

    def data(self) -> List[dict]:
        return self._data_rows

    def single(self) -> Optional[dict]:
        return self._single_row


class MockSession:
    def __init__(
        self,
        data_rows: Optional[List[dict]] = None,
        single_row: Optional[dict] = None,
        side_effect: Optional[Callable[..., Any]] = None,
    ):
        self._data_rows = data_rows or []
        self._single_row = single_row
        self._side_effect = side_effect

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, *args, **kwargs):
        if self._side_effect:
            result = self._side_effect(*args, **kwargs)
            if isinstance(result, Exception):
                raise result
            return result
        return MockRunResult(self._data_rows, self._single_row)


class MockDriver:
    def __init__(self, session: MockSession):
        self._session = session

    def session(self):
        return self._session

    def close(self):
        return None


@pytest.fixture
def mock_driver_factory():
    def _factory(data_rows=None, single_row=None, side_effect=None):
        session = MockSession(data_rows=data_rows, single_row=single_row, side_effect=side_effect)
        return MockDriver(session)

    return _factory
