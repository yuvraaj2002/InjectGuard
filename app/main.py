import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.container import AppContainer
from app.logging_config import configure_logging
from app.routers.api import router as api_router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Composition root: build shared services once, tear them down on shutdown."""
    container = AppContainer.build()
    app.state.container = container
    logger.info("InjectGuard Lab API ready")
    try:
        yield
    finally:
        container.close()
        app.state.container = None


app = FastAPI(
    title="InjectGuard Lab",
    description="BankOps agent lab with prompt-injection defenses",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
