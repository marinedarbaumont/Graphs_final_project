import os
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests (need docker services up)")

@pytest.fixture(scope="session")
def api_url():
    return os.getenv("API_URL", "http://localhost")
