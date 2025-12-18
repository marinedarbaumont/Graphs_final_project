from fastapi.testclient import TestClient
from app import database as database_module
from app.main import app

client = TestClient(app)

class FakeResult:
    def __init__(self, record=None, records=None):
        self._record = record
        self._records = records or []

    def single(self):
        return self._record

    def data(self):
        return self._records

class FakeSession:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

    def run(self, query, **params):
        # Adjust the "if" checks to match the queries in app/routers/orders.py
        if "MATCH (o:Order" in query and "RETURN properties(o) AS order" in query:
            return FakeResult(record={
                "order": {"order_id": params.get("order_id", 1)},
                "customer": {"customer_id": 10},
                "products": [{"product_id": 100, "name": "Widget"}],
            })
        return FakeResult(record=None, records=[])

class FakeDriver:
    def session(self):
        return FakeSession()

def test_orders_endpoint_unit(monkeypatch):
    # override the global driver used by get_driver()
    monkeypatch.setattr(database_module, "_driver", FakeDriver())

    r = client.get("/orders/1")
    assert r.status_code == 200
    body = r.json()
    assert "order" in body
    assert "customer" in body
    assert "products" in body
