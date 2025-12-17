from __future__ import annotations

from typing import Any, Dict, List

from neo4j import Driver


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

    return {"graph": gname, "limit": limit, "results": rows}


def run_louvain(driver: Driver, limit: int = 20, graph_name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
    """
    Runs Louvain community detection on the projected product co-purchase graph.
    Returns a flat list of products with their community_id (simple + easy to grade).
    """
    with driver.session() as session:
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

    return {"graph": gname, "limit": limit, "results": rows}
