import logging

from fastapi import FastAPI

from app.logging_config import configure_logging
from app.routers.api import router as api_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="InjectGuard Lab",
    description="OpsPilot vulnerable baseline API skeleton",
    version="0.1.0",
)

app.include_router(api_router)
logger.info("InjectGuard Lab API ready")
