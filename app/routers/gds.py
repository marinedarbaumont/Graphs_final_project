from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from pydantic import BaseModel, Field

from app.database import get_driver
from app.services.gds_service import (
    DEFAULT_GRAPH_NAME,
    run_louvain,
    run_pagerank,
)

router = APIRouter(prefix="/gds", tags=["GDS"])


# -------------------------
# Response models (Pydantic)
# -------------------------

class PageRankItem(BaseModel):
    product_id: int
    name: str | None = None
    score: float


class PageRankResponse(BaseModel):
    graph: str
    limit: int
    results: List[PageRankItem]


class LouvainItem(BaseModel):
    product_id: int
    name: str | None = None
    community_id: int = Field(..., description="Louvain community ID")


class LouvainResponse(BaseModel):
    graph: str
    limit: int
    results: List[LouvainItem]


# -------------------------
# Endpoints
# -------------------------

@router.get("/pagerank", response_model=PageRankResponse)
def pagerank(limit: int = Query(10, ge=1, le=200)):
    driver = get_driver()
    return run_pagerank(driver=driver, limit=limit, graph_name=DEFAULT_GRAPH_NAME)


@router.get("/louvain", response_model=LouvainResponse)
def louvain(limit: int = Query(20, ge=1, le=200)):
    driver = get_driver()
    return run_louvain(driver=driver, limit=limit, graph_name=DEFAULT_GRAPH_NAME)
