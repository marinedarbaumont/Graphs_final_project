from fastapi.testclient import TestClient
from app.main import app

def test_ping_unit():
    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
