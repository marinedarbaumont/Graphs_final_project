from fastapi.testclient import TestClient

from app import main


def test_root_route():
    client = TestClient(main.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Supply Chain API is running"


def test_ping_route():
    client = TestClient(main.app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_route(monkeypatch, mock_driver_factory):
    driver = mock_driver_factory(single_row={"ok": 1})
    monkeypatch.setattr(main, "get_driver", lambda: driver)

    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "neo4j": 1}
