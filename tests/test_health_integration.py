import pytest
import requests

@pytest.mark.integration
def test_health_endpoint_integration(api_url):
    r = requests.get(f"{api_url}/health", timeout=10)
    assert r.status_code == 200
