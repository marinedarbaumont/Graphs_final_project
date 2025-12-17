from typing import List, Optional
from pydantic import BaseModel

class TrainMLRequest(BaseModel):
    n_pos: int = 5000
    n_neg: int = 5000
    test_size: float = 0.2
    random_state: int = 42

class TrainMLResponse(BaseModel):
    n_pos: int
    n_neg: int
    auc: float
    accuracy: float

class RecommendationItem(BaseModel):
    product_id: int
    name: Optional[str] = None
    score: float

class RecommendationResponse(BaseModel):
    product_id: int
    k: int
    recommendations: List[RecommendationItem]
