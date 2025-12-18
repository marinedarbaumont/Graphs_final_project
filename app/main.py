from fastapi import FastAPI

from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.analytics import router as analytics_router
from app.routers import gds
from app.routers.ml import router as ml_router
from app.routers import llm

from .database import get_driver

app = FastAPI(title="Supply Chain Graph API")

@app.get("/health")
def health_check():
    driver = get_driver()
    with driver.session() as session:
        result = session.run("RETURN 1 AS ok").single()
    return {"status": "ok", "neo4j": result["ok"]}

@app.get("/")
def root():
    return {"message": "Supply Chain API is running"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

app.include_router(orders_router)
app.include_router(products_router)
app.include_router(analytics_router)
app.include_router(gds.router)
app.include_router(ml_router)
app.include_router(llm.router)
