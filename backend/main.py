from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.middleware import CorrelationIdMiddleware
from backend.routes.portfolio_routes import router as portfolio_router
from backend.routes.stock_routes import router as stock_router
from backend.schemas import HealthResponse
from utils.config import CORS_ORIGINS
from utils.logger import setup_logging
from utils.metrics import metrics

setup_logging()

app = FastAPI(
    title="AI Market Analyst API",
    description=(
        "Multi-agent AI platform for Indian stock analysis "
        "using fundamental, technical, and sentiment analysis."
    ),
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router)
app.include_router(portfolio_router)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    logger.debug("Health check called")
    return HealthResponse()


@app.get("/metrics")
def get_metrics() -> dict:
    logger.debug("Metrics endpoint called")
    return metrics.snapshot()


logger.info("AI Market Analyst API initialised")
