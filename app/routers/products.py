from typing import List

from fastapi import APIRouter, HTTPException
from app.database import get_driver
from app.models.order import (
    ProductModel,
    OrderCore,
    CustomerModel,
    ProductDetailsResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/{product_id}", response_model=ProductDetailsResponse)
def get_product(product_id: str):
    """
    Get a product with:
      - its basic info
      - the orders that contain it
      - the customers who bought it
    """
    driver = get_driver()

    with driver.session() as session:
        record = session.run(
            """
            MATCH (p:Product)
            WHERE toString(p.product_id) = $product_id

            OPTIONAL MATCH (p)<-[:CONTAINS]-(o:Order)
            OPTIONAL MATCH (o)<-[:PLACED]-(c:Customer)

            RETURN
              properties(p) AS product,
              collect(DISTINCT properties(o)) AS orders,
              collect(DISTINCT properties(c)) AS customers
            """,
            product_id=product_id,
        ).single()

    if record is None or record["product"] is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_node = record["product"] or {}
    orders_nodes: List[dict] = record["orders"] or []
    customers_nodes: List[dict] = record["customers"] or []

    # Pydantic ProductModel
    product = ProductModel(
        product_id=product_node.get("product_id"),
        name=product_node.get("name"),
        price=product_node.get("price"),
    )

    # Pydantic OrderCore list
    orders: List[OrderCore] = []
    for o in orders_nodes:
        # some orders might be missing if there are no orders, so we guard
        if o is None:
            continue
        orders.append(
            OrderCore(
                order_id=int(o.get("order_id")),
                order_date=o.get("order_date"),
                shipping_date=o.get("shipping_date"),
                late_delivery_risk=o.get("late_delivery_risk"),
                shipping_mode=o.get("shipping_mode"),
                days_shipping_scheduled=o.get("days_shipping_scheduled"),
                days_shipping_real=o.get("days_shipping_real"),
                region=o.get("region"),
                delivery_status=o.get("delivery_status"),
                status=o.get("status"),
            )
        )

    # Pydantic CustomerModel list
    customers: List[CustomerModel] = []
    for c in customers_nodes:
        if c is None:
            continue
        customers.append(
            CustomerModel(
                customer_id=c.get("customer_id"),
                first_name=c.get("first_name"),
                last_name=c.get("last_name"),
                city=c.get("city"),
                country=c.get("country"),
            )
        )

    return ProductDetailsResponse(
        product=product,
        orders=orders,
        customers=customers,
    )
