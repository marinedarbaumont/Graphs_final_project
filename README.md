# 📦 Supply Chain Knowledge Graph – Neo4j, FastAPI & Graph Data Science

This project is a **graph-based supply chain analytics platform** built with **Neo4j**, **FastAPI**, **Graph Data Science**, **Machine Learning**, and an **LLM-powered query interface**, fully containerized using **Docker Compose** and automated via a **Makefile**.

The goal is to model a real-world supply chain dataset as a **knowledge graph** and expose advanced analytics, graph algorithms, ML predictions, and natural-language explanations through a clean API.

---

## 📌 Key Features

* Neo4j graph schema with multiple node & relationship types
* Advanced Cypher queries (pathfinding, aggregations, analytics)
* Graph Data Science (PageRank, Louvain)
* Machine Learning link prediction (co-purchase prediction)
* LLM-powered graph querying & interpretation
* Dockerized infrastructure with Nginx reverse proxy
* Automated testing, linting, coverage & Makefile
* Full documentation & reproducibility

---

## 🧱 System Architecture

### Services (Docker Compose)

| Service   | Description                           |
| --------- | ------------------------------------- |
| **neo4j** | Neo4j graph database (Bolt + Browser) |
| **api**   | FastAPI backend (analytics, ML, LLM)  |
| **nginx** | Reverse proxy                         |

### Ports

| Component     | URL                                            |
| ------------- | ---------------------------------------------- |
| API           | [http://localhost](http://localhost)           |
| Swagger       | [http://localhost/docs](http://localhost/docs) |
| Neo4j Browser | [http://localhost:7474](http://localhost:7474) |
| Neo4j Bolt    | bolt://localhost:7687                          |

📐 **System architecture diagram**

<img width="1071" height="622" alt="architecture drawio" src="https://github.com/user-attachments/assets/1e56a820-a391-4bc6-b1b5-e858ea711663" />


---

## 🧠 Neo4j Graph Schema

### Node Labels & Key Properties

| Label        | Properties                                                   |
| ------------ | ------------------------------------------------------------ |
| `Customer`   | `customer_id`, `segment`, `country`                          |
| `Order`      | `order_id`, `order_date`, `delivery_status`, `shipping_days` |
| `Product`    | `product_id`, `name`, `category`, `price`                    |
| `Department` | `department_id`, `name`                                      |
| `Supplier`   | `supplier_id`, `name`, `region`                              |

### Relationship Types (Directed)

* `(Customer)<-[:PLACED_BY]-(Order)`
* `(Order)-[:CONTAINS]->(Product)`
* `(Product)-[:BELONGS_TO]->(Department)`
* `(Product)-[:SUPPLIED_BY]->(Supplier)`
* `(Product)-[:CO_PURCHASED_WITH]-(Product)`

### Constraints & Indexes

* Uniqueness constraints on IDs (`product_id`, `order_id`, etc.)
* Indexes on frequently queried properties (`product_id`, `department_id`)

📊 **Neo4j graph schema diagram**

<img width="1112" height="691" alt="Untitled Diagram drawio" src="https://github.com/user-attachments/assets/6532781e-d02a-4544-bf8f-482a97f50ba0" />


---

## 📥 Dataset & Ingestion

* **Dataset**: DataCo Supply Chain Dataset
* **Format**: CSV
* **Ingestion script**: `scripts/seed_data.py`


### Seeding

* Creates constraints & indexes
* Loads nodes and relationships
* Builds `CO_PURCHASED_WITH` edges
* Idempotent (safe to re-run)

---

## 🚀 Getting Started

### 1️⃣ Environment variables

```bash
cp .env.example .env
```

No secrets are hardcoded.

---

### 2️⃣ Start the full stack

```bash
make docker-run

```

This will:

* Build images
* Start Neo4j, API, Nginx
* Wait for Neo4j readiness
* Automatically seed the database

<img width="451" height="144" alt="Screenshot 2025-12-18 at 23 36 30" src="https://github.com/user-attachments/assets/4f496c9a-83b1-479d-9742-4026d7e5a6ec" />

<img width="369" height="116" alt="Screenshot 2025-12-18 at 23 36 39" src="https://github.com/user-attachments/assets/9946cbb2-f04e-4edc-bf39-4fbfcecbf580" />

<img width="327" height="93" alt="Screenshot 2025-12-18 at 23 36 46" src="https://github.com/user-attachments/assets/21fcaaf0-b054-43fc-b592-53ca6f3f6155" />

To reset everything:

```bash
make docker-down
```

---

## 📡 FastAPI Endpoints

<img width="1470" height="956" alt="Screenshot 2025-12-18 at 23 45 19" src="https://github.com/user-attachments/assets/414627e8-0fb2-4411-b309-200166204da9" />

<img width="1470" height="956" alt="Screenshot 2025-12-18 at 23 45 27" src="https://github.com/user-attachments/assets/e47c912c-1051-4835-8a7f-f9f6dbf387a9" />

### Health

* `GET /health`
  Checks API + Neo4j connectivity.

---

### Core API

* `GET /orders/{order_id}`
* `GET /products/{product_id}`

Uses Neo4j pattern matching and joins.

---

### Advanced Analytics (Cypher)

| Endpoint                                               | Description                     |
| ------------------------------------------------------ | ------------------------------- |
| `/analytics/top-products`                              | Aggregations & ranking          |
| `/analytics/bottlenecks/late-deliveries-by-department` | Operational bottleneck analysis |
| `/analytics/paths/products/shortest`                   | `shortestPath()`                |
| `/analytics/paths/products/all-shortest`               | `allShortestPaths()`            |

✔ Uses OPTIONAL MATCH
✔ Uses aggregations (`WITH`, `COUNT`, `AVG`)
✔ Depth ≥ 3 patterns

**GET /analytics/paths/products/shortest**

Question it answers:
“What is one shortest co-purchase chain connecting product A to product B?”
Example:
* From product “Smart watch” (ID 1360)
* To product “Gaming Laptop” (ID 987)
The shortest path might look like:
Smart watch → Wireless headphones → Gaming Laptop
Interpretation in business terms:
* Even if customers rarely buy smartwatch and gaming laptop together directly,
* They often buy smartwatch + headphones, and also headphones + laptop.
* So there is a 2-step relationship between the two items in the co-purchase network.

**GET /analytics/paths/products/all-shortest**

Question it answers:
“What are all shortest co-purchase chains between product A and product B?”
Sometimes there are multiple equally short paths, e.g.:
1. Smart watch → Wireless headphones → Gaming Laptop
2. Smart watch → Phone case → Gaming Laptop
Both paths have length 2, so they are all shortest paths, and both are interesting:
* They show different ways customers “bridge” products through their purchases.
* They can reveal alternative bundles or different customer journeys.

---

## 📊 Graph Data Science (GDS)

### In-memory projection

Graph is projected using Neo4j GDS for analytics.

### Algorithms

* `GET /gds/pagerank`
* `GET /gds/louvain`

✔ Centrality
✔ Community detection
✔ API integration

---

## 🤖 Machine Learning (Link Prediction)

### Training

* `POST /ml/train-link-predictor`

Features:

* Node degrees
* Common neighbors
* Jaccard similarity
* Preferential attachment

Model:

* Logistic Regression
* Train/test split
* AUC & accuracy returned

### Prediction

* `GET /ml/recommendations/{product_id}?k=10`

Predicts **new co-purchase links** that do not yet exist in the graph.

✔ End-to-end ML workflow
✔ Feature engineering from graph structure
✔ Evaluation metrics

---

## 🧠 LLM-Powered Graph Querying

### Endpoint

* `POST /llm/query`

Allows natural language queries such as:

* “Show me the top 10 products co-purchased with product_id 365”
* “Recommend 10 products similar to product_id 365.”
* "Is there a connection between product_id 365 and product_id 1059?"

The LLM:

* Chooses relevant graph queries
* Executes them safely
* Interprets results in business terms

The LLM is not responsible for database querying, but instead acts as an interpretation and decision-support layer.

✔ Prompt design
✔ Result interpretation
✔ Human-readable explanations

---

## 🧪 Tests & Quality

### Tests

```bash
make test
```

Includes:

* Unit tests
* API integration tests
* Neo4j connection tests
* Cypher query tests

<img width="341" height="58" alt="Screenshot 2025-12-18 at 23 52 04" src="https://github.com/user-attachments/assets/c7ee0271-bb64-4792-bcb9-95bb9a6b996a" />


---

### Coverage

```bash
make coverage
```

✔ Coverage ≥ **60%**
✔ HTML report generated in `htmlcov/index.html`

<img width="681" height="338" alt="Screenshot 2025-12-18 at 23 52 14" src="https://github.com/user-attachments/assets/7f18a4da-40af-480e-8588-f0b331ecf826" />


---

## 🧹 Linting & Formatting

```bash
make lint
```

* `.pylintrc` included
* pylint score ≥ **9.5 / 10**
* PEP 8 compliant
* Docstrings in all modules

<img width="497" height="46" alt="Screenshot 2025-12-18 at 23 45 07" src="https://github.com/user-attachments/assets/a2282752-f28d-4ed4-8d80-9b6e9ac0cae0" />


---

## ⚙️ Makefile Automation

```bash
make help
```

Key commands:

* `make install`
* `make run`
* `make docker-run`
* `make test`
* `make coverage`
* `make lint`
* `make clean`

✔ All commands functional
✔ Documented in README

---

## 🌐 Reverse Proxy

Nginx is used as a **reverse proxy** in front of the API:

* Single entry point
* Production-ready architecture

---

## 📓 Demo Notebook

📁 `demo.ipynb`

Includes:

* Graph exploration
* Cypher queries
* Visual inspection of relationships
* GDS algorithm examples



---

## 🔁 Git Practices



---

## 👤 Author

**Marine d’Arbaumont**

**Ghali Bennis**
ESSEC – CentraleSupélec
Bachelor in AI, Data & Management Science
