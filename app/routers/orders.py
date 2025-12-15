from typing import List, Optional

from fastapi import APIRouter, HTTPException
from app.database import get_driver
from app.models.order import OrderResponse, OrderCore, CustomerModel, ProductModel

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    driver = get_driver()

    with driver.session() as session:
        record = session.run(
            """
            MATCH (o:Order)
            WHERE toString(o.order_id) = $order_id
            OPTIONAL MATCH (o)<-[:PLACED]-(c:Customer)
            OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
            RETURN properties(o) AS order,
                   properties(c) AS customer,
                   [p IN collect(p) | properties(p)] AS products
            """,
            order_id=order_id,
        ).single()

    if record is None or record["order"] is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order_node = record["order"] or {}
    customer_node = record["customer"]
    products_nodes: List[dict] = record["products"] or []

    # Build Pydantic objects
    order_obj = OrderCore(
        order_id=int(order_node.get("order_id")),
        order_date=order_node.get("order_date"),
        shipping_date=order_node.get("shipping_date"),
        late_delivery_risk=order_node.get("late_delivery_risk"),
        shipping_mode=order_node.get("shipping_mode"),
        days_shipping_scheduled=order_node.get("days_shipping_scheduled"),
        days_shipping_real=order_node.get("days_shipping_real"),
        region=order_node.get("region"),
        delivery_status=order_node.get("delivery_status"),
        status=order_node.get("status"),
    )

    customer_obj: Optional[CustomerModel] = None
    if customer_node is not None:
        customer_obj = CustomerModel(
            customer_id=customer_node.get("customer_id"),
            first_name=customer_node.get("first_name"),
            last_name=customer_node.get("last_name"),
            city=customer_node.get("city"),
            country=customer_node.get("country"),
        )

    products_objs: List[ProductModel] = []
    for p in products_nodes:
        products_objs.append(
            ProductModel(
                product_id=p.get("product_id"),
                name=p.get("name"),
                price=p.get("price"),
            )
        )

    return OrderResponse(
        order=order_obj,
        customer=customer_obj,
        products=products_objs,
    )
