import json
import os
import re
import time
from typing import Any, Dict

import requests

# ----------------------------
# Groq config (interpretation only)
# ----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ----------------------------
# Cypher templates (safe, deterministic)
# ----------------------------

# 1-hop: products directly co-purchased with product_id
CYPHER_COPURCHASE = """
MATCH (p1:Product {product_id: $product_id})-[r:CO_PURCHASED_WITH]-(p2:Product)
RETURN p2.product_id AS product_id, p2.name AS name, r.weight AS weight
ORDER BY weight DESC
LIMIT $limit
""".strip()

# 2-hop recommendations: "people who bought X also bought Y" via shared neighbor
CYPHER_RECOMMEND_2HOP = """
MATCH (p:Product {product_id: $product_id})-[r1:CO_PURCHASED_WITH]-(mid:Product)-[r2:CO_PURCHASED_WITH]-(rec:Product)
WHERE rec.product_id <> $product_id
WITH rec, SUM(r1.weight + r2.weight) AS score
RETURN rec.product_id AS product_id, rec.name AS name, score AS score
ORDER BY score DESC
LIMIT $limit
""".strip()

# shortest path between two products (cap hops to keep it cheap)
CYPHER_CONNECTION = """
MATCH (a:Product {product_id: $from_id}),
      (b:Product {product_id: $to_id})
MATCH p = shortestPath((a)-[:CO_PURCHASED_WITH*..4]-(b))
RETURN [n IN nodes(p) | {product_id: n.product_id, name: n.name}] AS path,
       length(p) AS length
LIMIT 1
""".strip()


# ----------------------------
# Intent parsing (NO LLM for Cypher)
# ----------------------------

# product_id patterns: "product_id 365", "product id=365", "product-id: 365"
RE_PRODUCT_ID = re.compile(r"product[_\s-]?id\s*(?:=|:)?\s*(\d+)", re.IGNORECASE)
RE_LIMIT = re.compile(r"\b(top|first|recommend)\s+(\d+)\b", re.IGNORECASE)

RE_COPURCHASE = re.compile(r"(co[-\s]?purchas|copurchas|bought together|also bought)", re.IGNORECASE)
RE_RECOMMEND = re.compile(r"(recommend|similar)", re.IGNORECASE)
RE_CONNECTION = re.compile(r"(connection|path|linked|related)", re.IGNORECASE)


def _cap_limit(n: int, default_: int = 10, max_: int = 50) -> int:
    if not n:
        return default_
    return max(1, min(int(n), max_))


def parse_intent(question: str) -> Dict[str, Any]:
    q = question.strip()

    # Extract limit if present
    lim_match = RE_LIMIT.search(q)
    limit = _cap_limit(int(lim_match.group(2)) if lim_match else 10)

    # CONNECTION: needs TWO ids (we accept "product_id X and product_id Y")
    if RE_CONNECTION.search(q) and len(RE_PRODUCT_ID.findall(q)) >= 2:
        ids = [int(x) for x in RE_PRODUCT_ID.findall(q)]
        return {"type": "connection", "from_id": ids[0], "to_id": ids[1], "limit": 1}

    # CO-PURCHASE
    if RE_COPURCHASE.search(q):
        pid_match = RE_PRODUCT_ID.search(q)
        if pid_match:
            return {"type": "copurchase", "product_id": int(pid_match.group(1)), "limit": limit}

    # RECOMMENDATIONS (2-hop)
    if RE_RECOMMEND.search(q):
        pid_match = RE_PRODUCT_ID.search(q)
        if pid_match:
            return {"type": "recommend", "product_id": int(pid_match.group(1)), "limit": limit}

    return {"type": "unknown"}


# ----------------------------
# Groq interpretation (LLM used ONLY here)
# ----------------------------

INTERPRET_SYSTEM = """You are a helpful supply-chain/operations analyst.
You receive:
- the user question
- the query intent
- a small JSON result set from Neo4j (co-purchases, recommendations, or a shortest-path connection)

Your job:
1) Summarize what the result shows in plain English.
2) Give 2-4 actionable ops insights (bundling/cross-sell, inventory, substitution risk, demand signals).
Rules:
- Do NOT invent numbers or products that are not in the results.
- If results are empty, explain likely reasons and what to check next.
- Keep it concise (max ~10 lines).
Return ONLY text (no markdown).
"""


def groq_interpret(question: str, intent: Dict[str, Any], data: Any) -> str:
    # If Groq isn't configured, just return a simple fallback interpretation
    if not GROQ_API_KEY:
        return "No LLM interpretation available (GROQ_API_KEY missing)."

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": INTERPRET_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {"question": question, "intent": intent, "data": data},
                    ensure_ascii=False,
                ),
            },
        ],
    }

    r = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    out = r.json()
    return out["choices"][0]["message"]["content"].strip()


# ----------------------------
# Main entry point used by the router
# ----------------------------

def run_llm_query(session, question: str) -> Dict[str, Any]:
    t0 = time.time()
    intent = parse_intent(question)

    if intent["type"] == "unknown":
        return {
            "question": question,
            "intent": intent["type"],
            "cypher": "",
            "params": {},
            "rows": 0,
            "latency_ms": int((time.time() - t0) * 1000),
            "data": [],
            "interpretation": (
                "I can answer: (1) co-purchases for a product_id, (2) 2-hop recommendations for a product_id, "
                "or (3) connection/path between two product_ids. Example: 'Show top 10 co-purchased with product_id 365'."
            ),
        }

    if intent["type"] == "copurchase":
        cypher = CYPHER_COPURCHASE
        params = {"product_id": intent["product_id"], "limit": intent["limit"]}
        records = session.run(cypher, **params).data()

    elif intent["type"] == "recommend":
        cypher = CYPHER_RECOMMEND_2HOP
        params = {"product_id": intent["product_id"], "limit": intent["limit"]}
        records = session.run(cypher, **params).data()

    else:  # connection
        cypher = CYPHER_CONNECTION
        params = {"from_id": intent["from_id"], "to_id": intent["to_id"]}
        one = session.run(cypher, **params).single()
        records = [dict(one)] if one else []

    interpretation = groq_interpret(question, intent, records)

    return {
        "question": question,
        "intent": intent["type"],
        "cypher": cypher,
        "params": params,
        "rows": len(records),
        "latency_ms": int((time.time() - t0) * 1000),
        "data": records,
        "interpretation": interpretation,
    }
