from typing import List

from fastapi import APIRouter, Query, HTTPException
from app.database import get_driver
from app.models.analytics import (
    TopProduct,
    TopProductsResponse,
    DepartmentBottleneck,
    DepartmentBottlenecksResponse,
    ProductPathResponse,
    AllProductPathsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/top-products", response_model=TopProductsResponse)
def get_top_products(limit: int = Query(10, ge=1, le=100)):
    """
    Return the top N products, ordered by how many times they appear in orders.
    """
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (:Order)-[r:CONTAINS]->(p:Product)
            RETURN
              p.product_id AS product_id,
              p.name AS name,
              count(*) AS times_ordered,
              coalesce(sum(r.quantity), 0) AS total_quantity
            ORDER BY times_ordered DESC
            LIMIT $limit
            """,
            limit=limit,
        )

        items: List[TopProduct] = []
        for record in result:
            items.append(
                TopProduct(
                    product_id=record["product_id"],
                    name=record["name"],
                    times_ordered=record["times_ordered"],
                    total_quantity=record["total_quantity"],
                )
            )

    return TopProductsResponse(items=items)


@router.get(
    "/bottlenecks/late-deliveries-by-department",
    response_model=DepartmentBottlenecksResponse,
)
def get_late_deliveries_by_department(
    limit: int = Query(10, ge=1, le=100),
):
    """
    Find departments that are bottlenecks based on late deliveries.

    For each department:
    - total_orders: how many orders went through this department
    - late_orders: how many of those had late_delivery_risk = 1
    - late_ratio: percentage of late orders (0–100)
    """
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            // Get all orders per department
            MATCH (d:Department)<-[:FROM_DEPARTMENT]-(o:Order)
            WITH d, collect(o) AS orders

            // Compute late vs total
            WITH
              d,
              orders,
              [o IN orders WHERE o.late_delivery_risk = 1] AS late_orders_list,
              size(orders) AS total_orders
            WITH
              d,
              size(late_orders_list) AS late_orders,
              total_orders,
              CASE
                WHEN total_orders = 0 THEN 0.0
                ELSE 100.0 * size(late_orders_list) / total_orders
              END AS late_ratio

            RETURN
              d.department_id AS department_id,
              d.name AS department_name,
              d.market AS market,
              late_orders,
              total_orders,
              late_ratio
            ORDER BY late_ratio DESC, late_orders DESC
            LIMIT $limit
            """,
            limit=limit,
        )

        items: List[DepartmentBottleneck] = []
        for record in result:
            items.append(
                DepartmentBottleneck(
                    department_id=record["department_id"],
                    department_name=record["department_name"],
                    market=record["market"],
                    late_orders=record["late_orders"],
                    total_orders=record["total_orders"],
                    late_ratio=record["late_ratio"],
                )
            )

    return DepartmentBottlenecksResponse(items=items)



@router.get(
    "/bottlenecks/late-deliveries-by-department",
    response_model=DepartmentBottlenecksResponse,
)
def get_late_deliveries_by_department(
    limit: int = Query(10, ge=1, le=100),
):
    """
    Find departments that are bottlenecks based on late deliveries.
    """
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Department)<-[:FROM_DEPARTMENT]-(o:Order)
            WITH d, collect(o) AS orders
            WITH
              d,
              orders,
              [o IN orders WHERE o.late_delivery_risk = 1] AS late_orders_list,
              size(orders) AS total_orders
            WITH
              d,
              size(late_orders_list) AS late_orders,
              total_orders,
              CASE
                WHEN total_orders = 0 THEN 0.0
                ELSE 100.0 * size(late_orders_list) / total_orders
              END AS late_ratio
            RETURN
              d.department_id AS department_id,
              d.name AS department_name,
              d.market AS market,
              late_orders,
              total_orders,
              late_ratio
            ORDER BY late_ratio DESC, late_orders DESC
            LIMIT $limit
            """,
            limit=limit,
        )

        items: List[DepartmentBottleneck] = []
        for record in result:
            items.append(
                DepartmentBottleneck(
                    department_id=record["department_id"],
                    department_name=record["department_name"],
                    market=record["market"],
                    late_orders=record["late_orders"],
                    total_orders=record["total_orders"],
                    late_ratio=record["late_ratio"],
                )
            )

    return DepartmentBottlenecksResponse(items=items)

# Shortest path endpoints


@router.get(
    "/paths/products/shortest",
    response_model=ProductPathResponse,
)
def shortest_product_path(
    from_id: int = Query(..., description="Source product_id"),
    to_id: int = Query(..., description="Target product_id"),
):
    """
    Find ONE shortest co-purchase path between two products
    using the CO_PURCHASED_WITH relationships.
    """
    driver = get_driver()

    with driver.session() as session:
        record = session.run(
            """
            MATCH (start:Product {product_id: $from_id}),
                  (end:Product   {product_id: $to_id})
            MATCH p = shortestPath(
                (start)-[:CO_PURCHASED_WITH*1..5]-(end)
            )
            RETURN
              [n IN nodes(p) | {product_id: n.product_id, name: n.name}] AS products,
              length(p) AS length
            """,
            from_id=from_id,
            to_id=to_id,
        ).single()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No path found between these products",
        )

    products = record["products"]
    length = record["length"]

    return {
        "path": {
            "products": products,
            "length": length,
        }
    }


@router.get(
    "/paths/products/all-shortest",
    response_model=AllProductPathsResponse,
)
def all_shortest_product_paths(
    from_id: int = Query(..., description="Source product_id"),
    to_id: int = Query(..., description="Target product_id"),
):
    """
    Find ALL shortest co-purchase paths between two products.
    """
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (start:Product {product_id: $from_id}),
                  (end:Product   {product_id: $to_id})
            MATCH p = allShortestPaths(
                (start)-[:CO_PURCHASED_WITH*1..5]-(end)
            )
            RETURN
              [n IN nodes(p) | {product_id: n.product_id, name: n.name}] AS products,
              length(p) AS length
            ORDER BY length ASC
            """,
            from_id=from_id,
            to_id=to_id,
        )

        paths: List[dict] = []
        for record in result:
            paths.append(
                {
                    "products": record["products"],
                    "length": record["length"],
                }
            )

    if not paths:
        raise HTTPException(
            status_code=404,
            detail="No paths found between these products",
        )

    return {"paths": paths}
