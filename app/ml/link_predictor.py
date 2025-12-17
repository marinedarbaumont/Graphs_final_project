import os
import joblib
import numpy as np
from neo4j.exceptions import Neo4jError
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

MODEL_PATH = os.getenv("ML_MODEL_PATH", "/code/models/link_predictor.joblib")

FEATURE_QUERY = """
UNWIND $pairs AS pair
MATCH (p:Product {product_id: pair.p}), (q:Product {product_id: pair.q})
WITH p, q
// degrees in co-purchase graph
OPTIONAL MATCH (p)-[:CO_PURCHASED_WITH]-(pn:Product)
WITH p, q, count(pn) AS deg_p
OPTIONAL MATCH (q)-[:CO_PURCHASED_WITH]-(qn:Product)
WITH p, q, deg_p, count(qn) AS deg_q
// common neighbors
OPTIONAL MATCH (p)-[:CO_PURCHASED_WITH]-(x:Product)-[:CO_PURCHASED_WITH]-(q)
WITH p, q, deg_p, deg_q, count(DISTINCT x) AS common
WITH
  p.product_id AS p_id,
  q.product_id AS q_id,
  deg_p,
  deg_q,
  common,
  (deg_p * deg_q) AS pref_attach,
  CASE WHEN (deg_p + deg_q - common) = 0 THEN 0.0
       ELSE (1.0 * common) / (deg_p + deg_q - common) END AS jaccard
RETURN p_id, q_id, deg_p, deg_q, common, pref_attach, jaccard
"""

def save_model(model):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)

def sample_positive_pairs(session, n_pos: int):
    rows = session.run(
        """
        MATCH (p:Product)-[:CO_PURCHASED_WITH]-(q:Product)
        WHERE p.product_id < q.product_id
        RETURN p.product_id AS p, q.product_id AS q
        LIMIT $n
        """,
        n=n_pos,
    ).data()
    return [{"p": r["p"], "q": r["q"]} for r in rows]

def sample_negative_pairs(session, n_neg: int):
    # random pairs without an edge; keep it limited to avoid huge cartesian work
    rows = session.run(
        """
        MATCH (p:Product)
        WITH p ORDER BY rand() LIMIT $n
        MATCH (q:Product)
        WITH p, q ORDER BY rand() LIMIT $n
        WHERE p.product_id <> q.product_id AND p.product_id < q.product_id
        AND NOT (p)-[:CO_PURCHASED_WITH]-(q)
        RETURN p.product_id AS p, q.product_id AS q
        LIMIT $n
        """,
        n=n_neg,
    ).data()
    return [{"p": r["p"], "q": r["q"]} for r in rows]

def fetch_features(session, pairs):
    rows = session.run(FEATURE_QUERY, pairs=pairs).data()
    # X: deg_p, deg_q, common, pref_attach, jaccard
    X = np.array([[r["deg_p"], r["deg_q"], r["common"], r["pref_attach"], r["jaccard"]] for r in rows], dtype=float)
    ids = [(r["p_id"], r["q_id"]) for r in rows]
    return X, ids

def train_and_evaluate(driver, n_pos=5000, n_neg=5000, test_size=0.2, random_state=42):
    try:
        with driver.session() as session:
            pos = sample_positive_pairs(session, n_pos)
            neg = sample_negative_pairs(session, n_neg)

            X_pos, _ = fetch_features(session, pos)
            X_neg, _ = fetch_features(session, neg)

        y_pos = np.ones(len(X_pos))
        y_neg = np.zeros(len(X_neg))

        X = np.vstack([X_pos, X_neg])
        y = np.concatenate([y_pos, y_neg])

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        model = LogisticRegression(max_iter=200, n_jobs=None)
        model.fit(X_train, y_train)

        proba = model.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)

        auc = float(roc_auc_score(y_test, proba))
        acc = float(accuracy_score(y_test, preds))

        save_model(model)
        return auc, acc

    except Neo4jError as e:
        raise RuntimeError(f"Neo4j error: {e.message}") from e
