from fastapi import APIRouter, HTTPException, Query
from neo4j.exceptions import Neo4jError

from app.database import get_driver
from app.models.ml import TrainMLRequest, TrainMLResponse, RecommendationResponse
from app.ml.link_predictor import train_and_evaluate, load_model, fetch_features

router = APIRouter(prefix="/ml", tags=["ML"])

@router.post("/train-link-predictor", response_model=TrainMLResponse)
def train_link_predictor(payload: TrainMLRequest):
    driver = get_driver()
    try:
        auc, acc = train_and_evaluate(
            driver,
            n_pos=payload.n_pos,
            n_neg=payload.n_neg,
            test_size=payload.test_size,
            random_state=payload.random_state,
        )
        return {"n_pos": payload.n_pos, "n_neg": payload.n_neg, "auc": auc, "accuracy": acc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/{product_id}", response_model=RecommendationResponse)
def recommend(product_id: int, k: int = Query(10, ge=1, le=50)):
    model = load_model()
    if model is None:
        raise HTTPException(status_code=400, detail="Model not trained yet. Call POST /ml/train-link-predictor first.")

    driver = get_driver()
    try:
        with driver.session() as session:
            # candidate set = neighbors-of-neighbors (fast + relevant)
            candidates = session.run(
                """
                MATCH (p:Product {product_id: $pid})-[:CO_PURCHASED_WITH]-(n:Product)-[:CO_PURCHASED_WITH]-(c:Product)
                WHERE c.product_id <> $pid
                RETURN DISTINCT c.product_id AS cid, c.name AS name
                LIMIT 2000
                """,
                pid=product_id
            ).data()

            if not candidates:
                raise HTTPException(status_code=404, detail="No candidates found for this product.")

            pairs = [{"p": product_id, "q": r["cid"]} for r in candidates]
            X, ids = fetch_features(session, pairs)

        proba = model.predict_proba(X)[:, 1]
        scored = []
        for (p_id, q_id), score in zip(ids, proba):
            # recover name from candidates list
            name = next((c["name"] for c in candidates if c["cid"] == q_id), None)
            scored.append({"product_id": int(q_id), "name": name, "score": float(score)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"product_id": product_id, "k": k, "recommendations": scored[:k]}

    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Neo4j error: {e.message}") from e
