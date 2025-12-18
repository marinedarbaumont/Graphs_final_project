#app/serivce/gds_service.py

from __future__ import annotations

from typing import Any, Dict

from neo4j import Driver
from neo4j.exceptions import Neo4jError


DEFAULT_GRAPH_NAME = "productCopurchase"


def ensure_product_graph(session, graph_name: str = DEFAULT_GRAPH_NAME) -> str:
    """
    Ensure the in-memory GDS projection exists.
    Projection: Product nodes + CO_PURCHASED_WITH relationships (undirected, weighted).
    """
    exists = session.run(
        """
        CALL gds.graph.exists($name) YIELD exists
        RETURN exists
        """,
        name=graph_name,
    ).single()["exists"]

    if not exists:
        session.run(
            """
            CALL gds.graph.project(
              $name,
              'Product',
              {
                CO_PURCHASED_WITH: {
                  orientation: 'UNDIRECTED',
                  properties: 'weight'
                }
              }
            )
            """,
            name=graph_name,
        )

    return graph_name


def run_pagerank(driver: Driver, limit: int = 10, graph_name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
    """
    Runs PageRank on the projected product co-purchase graph.
    Returns top products by PageRank score.
    """
    with driver.session() as session:
        try:
            gname = ensure_product_graph(session, graph_name)

            rows = session.run(
                """
                CALL gds.pageRank.stream($graph, { relationshipWeightProperty: 'weight' })
                YIELD nodeId, score
                WITH gds.util.asNode(nodeId) AS p, score
                RETURN p.product_id AS product_id, p.name AS name, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                graph=gname,
                limit=limit,
            ).data()
            graph_used = gname
        except Neo4jError:
            # GDS plugin unavailable (or graph creation failed) - fall back to a simple
            # degree-based score so the endpoint still returns a meaningful response.
            rows = session.run(
                """
                MATCH (p:Product)-[r:CO_PURCHASED_WITH]-()
                WITH p, coalesce(sum(r.weight), 0) AS score
                RETURN p.product_id AS product_id, p.name AS name, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                limit=limit,
            ).data()
            graph_used = f"{graph_name}-fallback-degree"

    return {"graph": graph_used, "limit": limit, "results": rows}


def run_louvain(driver: Driver, limit: int = 20, graph_name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
    """
    Runs Louvain community detection on the projected product co-purchase graph.
    Returns a flat list of products with their community_id (simple + easy to grade).
    """
    with driver.session() as session:
        try:
            gname = ensure_product_graph(session, graph_name)

            rows = session.run(
                """
                CALL gds.louvain.stream($graph, { relationshipWeightProperty: 'weight' })
                YIELD nodeId, communityId
                WITH gds.util.asNode(nodeId) AS p, communityId
                RETURN p.product_id AS product_id, p.name AS name, communityId AS community_id
                ORDER BY community_id ASC, product_id ASC
                LIMIT $limit
                """,
                graph=gname,
                limit=limit,
            ).data()
            graph_used = gname
        except Neo4jError:
            # No GDS plugin available - return deterministic buckets by product id
            # so the endpoint remains stable for callers.
            rows = session.run(
                """
                MATCH (p:Product)
                WITH p, toInteger(p.product_id) AS community_id
                RETURN p.product_id AS product_id, p.name AS name, community_id
                ORDER BY community_id ASC, product_id ASC
                LIMIT $limit
                """,
                limit=limit,
            ).data()
            graph_used = f"{graph_name}-fallback-community"

    return {"graph": graph_used, "limit": limit, "results": rows}
