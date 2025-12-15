import os
import math
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from neo4j import GraphDatabase

from app.database import get_driver


# ---------------------------------------------------------------------
# 1) Neo4j connection (uses env vars from .env)
# ---------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# ---------------------------------------------------------------------
# 2) Constraints (run once, safe with IF NOT EXISTS)
# ---------------------------------------------------------------------
def create_constraints() -> None:
    queries = [
        """
        CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
        FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT order_id_unique IF NOT EXISTS
        FOR (o:Order) REQUIRE o.order_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT product_id_unique IF NOT EXISTS
        FOR (p:Product) REQUIRE p.product_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT category_id_unique IF NOT EXISTS
        FOR (cat:Category) REQUIRE cat.category_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT department_id_unique IF NOT EXISTS
        FOR (d:Department) REQUIRE d.department_id IS UNIQUE
        """,
    ]

    with driver.session() as session:
        for q in queries:
            session.run(q)

    print("✅ Constraints created / verified")

# Create Indexes

def create_indexes() -> None:
    queries = [
        # Orders by region
        """
        CREATE INDEX order_region_index IF NOT EXISTS
        FOR (o:Order) ON (o.region)
        """,
        # Orders by region & shipping_mode (composite index)
        """
        CREATE INDEX order_region_shipping_index IF NOT EXISTS
        FOR (o:Order) ON (o.region, o.shipping_mode)
        """,
        # Orders by late_delivery_risk
        """
        CREATE INDEX order_late_risk_index IF NOT EXISTS
        FOR (o:Order) ON (o.late_delivery_risk)
        """,
        # Departments by market
        """
        CREATE INDEX department_market_index IF NOT EXISTS
        FOR (d:Department) ON (d.market)
        """,
    ]

    with driver.session() as session:
        for q in queries:
            session.run(q)

    print("✅ Indexes created / verified")



# ---------------------------------------------------------------------
# 3) Load CSV
# ---------------------------------------------------------------------
def load_csv(path: str) -> pd.DataFrame:
    print(f"📥 Reading CSV: {path}")
    df = pd.read_csv(path, encoding="latin1")

    print(f"   -> {len(df)} rows in original dataset")

    # Optional: during dev, comment in to test on fewer rows
    # df = df.head(5000)

    return df


# ---------------------------------------------------------------------
# 4) Batch helper
# because if we do not use batches seeding the data takes a lot of time
# ---------------------------------------------------------------------
def chunked(iterable, size):
    """Yield successive chunks of given size from a list."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


# ---------------------------------------------------------------------
# 5) Seed graph using UNWIND batches
# ---------------------------------------------------------------------
def seed_graph(df: pd.DataFrame, batch_size: int = 1000) -> None:
    """
    Convert each row to a dict, then send them to Neo4j in batches using UNWIND.
    This is MUCH faster than one query per row.
    """

    # Cypher query that handles a whole batch at once
    cypher = """
    UNWIND $rows AS row

    // Customer
    MERGE (c:Customer {customer_id: row.customer_id})
      ON CREATE SET
        c.first_name = row.first_name,
        c.last_name  = row.last_name,
        c.city       = row.customer_city,
        c.country    = row.customer_country

    // Product
    MERGE (p:Product {product_id: row.product_id})
      ON CREATE SET
        p.name  = row.product_name,
        p.price = row.product_price,
        p.status = row.product_status

    // Category
    MERGE (cat:Category {category_id: row.category_id})
      ON CREATE SET
        cat.name = row.category_name

    MERGE (p)-[:IN_CATEGORY]->(cat)

    // Department
    MERGE (d:Department {department_id: row.department_id})
      ON CREATE SET
        d.name   = row.department_name,
        d.market = row.market

    // Order
    MERGE (o:Order {order_id: row.order_id})
      ON CREATE SET
        o.order_date              = row.order_date,
        o.status                  = row.order_status,
        o.region                  = row.order_region,
        o.delivery_status         = row.delivery_status,
        o.late_delivery_risk      = row.late_risk,
        o.days_shipping_real      = row.days_shipping_real,
        o.days_shipping_scheduled = row.days_shipping_scheduled,
        o.shipping_mode           = row.shipping_mode,
        o.shipping_date           = row.shipping_date

    // Relationships
    MERGE (c)-[:PLACED]->(o)

    MERGE (o)-[r:CONTAINS]->(p)
      ON CREATE SET
        r.order_item_id = row.order_item_id,
        r.quantity      = row.quantity,
        r.unit_price    = row.product_price

    MERGE (o)-[:FROM_DEPARTMENT]->(d)
    """

    # Turn pandas DataFrame into list of dicts once (fast)
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "customer_id": row["Customer Id"],
                "first_name": row.get("Customer Fname"),
                "last_name": row.get("Customer Lname"),
                "customer_city": row.get("Customer City"),
                "customer_country": row.get("Customer Country"),

                "product_id": row["Product Card Id"],
                "product_name": row.get("Product Name"),
                "product_price": float(row.get("Order Item Product Price", 0.0)),
                "product_status": row.get("Product Status"),

                "category_id": row["Category Id"],
                "category_name": row.get("Category Name"),

                "department_id": row["Department Id"],
                "department_name": row.get("Department Name"),
                "market": row.get("Market"),

                "order_id": row["Order Id"],
                "order_date": row.get("order date (DateOrders)"),
                "order_status": row.get("Order Status"),
                "order_region": row.get("Order Region"),
                "delivery_status": row.get("Delivery Status"),
                "late_risk": int(row.get("Late_delivery_risk", 0)),
                "days_shipping_real": float(row.get("Days for shipping (real)", 0.0)),
                "days_shipping_scheduled": float(
                    row.get("Days for shipment (scheduled)", 0.0)
                ),
                "shipping_mode": row.get("Shipping Mode"),
                "shipping_date": row.get("shipping date (DateOrders)"),

                "order_item_id": row["Order Item Id"],
                "quantity": int(row.get("Order Item Quantity", 1)),
            }
        )

    total = len(records)
    num_batches = math.ceil(total / batch_size)
    print(f"🚚 Seeding {total} rows in {num_batches} batches of {batch_size}")

    with driver.session() as session:
        for i, batch in enumerate(chunked(records, batch_size), start=1):
            session.run(cypher, rows=batch)
            print(f"   ✅ Inserted batch {i}/{num_batches} ({len(batch)} rows)")

    print("🎉 All batches inserted!")

# Create co-purchase relationships

def build_copurchase_relationships():
    """
    Build CO_PURCHASED_WITH relationships between products that appear
    in the same order.

    r.weight = number of orders in which the two products co-occur.
    """
    driver = get_driver()

    cypher = """
    MATCH (o:Order)-[:CONTAINS]->(p1:Product),
          (o)-[:CONTAINS]->(p2:Product)
    WHERE id(p1) < id(p2)
    MERGE (p1)-[r:CO_PURCHASED_WITH]-(p2)
    ON CREATE SET r.weight = 1
    ON MATCH  SET r.weight = r.weight + 1
    """

    with driver.session() as session:
        session.run("MATCH ()-[r:CO_PURCHASED_WITH]-() DELETE r")
        session.run(cypher)



# ---------------------------------------------------------------------
# 6) Main entry point
# ---------------------------------------------------------------------
def main():
    csv_path = os.path.join("data", "DataCoSupplyChainDataset.csv")
    df = load_csv(csv_path)

    create_constraints()
    create_indexes()
    seed_graph(df)

    build_copurchase_relationships() 
    print("✅ Built CO_PURCHASED_WITH relationships")


if __name__ == "__main__":
    main()

