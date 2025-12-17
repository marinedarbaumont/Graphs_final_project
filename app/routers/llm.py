from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import get_driver
from app.services.llm_service import run_llm_query

router = APIRouter(prefix="/llm", tags=["LLM"])


class LLMQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class LLMQueryResponse(BaseModel):
    question: str
    intent: str
    cypher: str
    params: dict
    rows: int
    latency_ms: int
    data: list
    interpretation: str


@router.post("/query", response_model=LLMQueryResponse)
def llm_query(payload: LLMQueryRequest):
    try:
        driver = get_driver()
        with driver.session() as session:
            return run_llm_query(session, payload.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
