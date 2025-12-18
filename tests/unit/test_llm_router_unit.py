from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_llm_valueerror_becomes_400(monkeypatch):
    import app.routers.llm as llm_router

    def boom(*args, **kwargs):
        raise ValueError("unsafe cypher")

    monkeypatch.setattr(llm_router, "run_llm_query", boom)

    r = client.post("/llm/query", json={"question": "show me something"})
    assert r.status_code == 400
    assert "unsafe cypher" in r.text
