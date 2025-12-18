from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ml_recommendations_returns_400_when_model_missing(monkeypatch):
    # Force load_model() to return None
    import app.routers.ml as ml_router
    monkeypatch.setattr(ml_router, "load_model", lambda: None)

    r = client.get("/ml/recommendations/123?k=5")
    assert r.status_code == 400
    assert "Model not trained yet" in r.text
