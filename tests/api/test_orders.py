import os
import pytest
import requests
from neo4j import GraphDatabase

API_URL = os.getenv("API_URL", "http://localhost")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def get_any_order_id():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            rec = session.run(
                "MATCH (o:Order) RETURN o.order_id AS id ORDER BY id DESC LIMIT 1"
            ).single()
            return rec["id"] if rec else None
    finally:
        driver.close()

@pytest.mark.integration
def test_order_endpoint_returns_order():
    oid = get_any_order_id()
    assert oid is not None, "No Order nodes found; seeding might not have run"

    r = requests.get(f"{API_URL}/orders/{oid}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "order" in data
    assert "customer" in data
    assert "products" in data

@pytest.mark.cypher
def test_cypher_has_products():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            rec = session.run("MATCH (p:Product) RETURN count(p) AS n").single()
            assert rec is not None
            assert rec["n"] > 0
    finally:
        driver.close()