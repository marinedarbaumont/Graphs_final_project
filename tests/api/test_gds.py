import os
import time
import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost")

def get_with_retry(path, tries=12, sleep=2, timeout=60):
    last = None
    for _ in range(tries):
        try:
            r = requests.get(f"{API_URL}{path}", timeout=timeout)
            if r.status_code == 200:
                return r
            last = (r.status_code, r.text[:300])
        except Exception as e:
            last = str(e)
        time.sleep(sleep)
    raise AssertionError(f"Failed after retries: {path} last={last}")

@pytest.mark.integration
def test_gds_pagerank():
    r = get_with_retry("/gds/pagerank?limit=5", tries=15, sleep=2, timeout=60)
    data = r.json()
    assert "results" in data
    assert len(data["results"]) <= 5

@pytest.mark.integration
def test_gds_louvain():
    r = get_with_retry("/gds/louvain?limit=5", tries=15, sleep=2, timeout=60)
    data = r.json()
    assert "results" in data
    assert len(data["results"]) <= 5
