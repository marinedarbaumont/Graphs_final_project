from fastapi.testclient import TestClient

from app import main
from app.routers import gds as gds_router
from app.services import gds_service


def test_gds_pagerank_route(monkeypatch, mock_driver_factory):
    rows = [
        {"product_id": 1, "name": "Alpha", "score": 0.9},
        {"product_id": 2, "name": "Beta", "score": 0.8},
    ]
    driver = mock_driver_factory(data_rows=rows)

    monkeypatch.setattr(gds_router, "get_driver", lambda: driver)
    monkeypatch.setattr(gds_service, "ensure_product_graph", lambda session, graph_name: graph_name)

    client = TestClient(main.app)
    resp = client.get("/gds/pagerank?limit=2")

    assert resp.status_code == 200
    data = resp.json()
    assert data["graph"] == gds_service.DEFAULT_GRAPH_NAME
    assert len(data["results"]) == 2


def test_gds_louvain_route(monkeypatch, mock_driver_factory):
    rows = [
        {"product_id": 3, "name": "Gamma", "community_id": 1},
        {"product_id": 4, "name": "Delta", "community_id": 2},
    ]
    driver = mock_driver_factory(data_rows=rows)

    monkeypatch.setattr(gds_router, "get_driver", lambda: driver)
    monkeypatch.setattr(gds_service, "ensure_product_graph", lambda session, graph_name: graph_name)

    client = TestClient(main.app)
    resp = client.get("/gds/louvain?limit=2")

    assert resp.status_code == 200
    data = resp.json()
    assert data["graph"] == gds_service.DEFAULT_GRAPH_NAME
    assert len(data["results"]) == 2
