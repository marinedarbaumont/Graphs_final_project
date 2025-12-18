from app.services import gds_service


def test_run_pagerank_success(monkeypatch, mock_driver_factory):
    rows = [{"product_id": 1, "name": "A", "score": 0.5}]
    driver = mock_driver_factory(data_rows=rows)
    monkeypatch.setattr(gds_service, "ensure_product_graph", lambda session, graph_name: graph_name)

    result = gds_service.run_pagerank(driver=driver, limit=1, graph_name="graph-one")

    assert result["graph"] == "graph-one"
    assert result["limit"] == 1
    assert result["results"] == rows


def test_run_pagerank_fallback(monkeypatch, mock_driver_factory):
    class FakeError(Exception):
        pass

    rows = [{"product_id": 2, "name": "B", "score": 3}]
    driver = mock_driver_factory(data_rows=rows)
    monkeypatch.setattr(gds_service, "Neo4jError", FakeError)

    def _raise(*_args, **_kwargs):
        raise FakeError("no gds")

    monkeypatch.setattr(gds_service, "ensure_product_graph", _raise)

    result = gds_service.run_pagerank(driver=driver, limit=2, graph_name="graph-two")

    assert result["graph"] == "graph-two-fallback-degree"
    assert result["results"] == rows


def test_run_louvain_success(monkeypatch, mock_driver_factory):
    rows = [
        {"product_id": 3, "name": "C", "community_id": 10},
        {"product_id": 4, "name": "D", "community_id": 11},
    ]
    driver = mock_driver_factory(data_rows=rows)
    monkeypatch.setattr(gds_service, "ensure_product_graph", lambda session, graph_name: graph_name)

    result = gds_service.run_louvain(driver=driver, limit=2, graph_name="graph-three")

    assert result["graph"] == "graph-three"
    assert result["results"] == rows


def test_run_louvain_fallback(monkeypatch, mock_driver_factory):
    class FakeError(Exception):
        pass

    rows = [
        {"product_id": 5, "name": "E", "community_id": 5},
        {"product_id": 6, "name": "F", "community_id": 6},
    ]
    driver = mock_driver_factory(data_rows=rows)
    monkeypatch.setattr(gds_service, "Neo4jError", FakeError)

    def _raise(*_args, **_kwargs):
        raise FakeError("no gds")

    monkeypatch.setattr(gds_service, "ensure_product_graph", _raise)

    result = gds_service.run_louvain(driver=driver, limit=2, graph_name="graph-four")

    assert result["graph"] == "graph-four-fallback-community"
    assert result["results"] == rows
