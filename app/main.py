from fastapi import FastAPI

from app.routers.api import router as api_router

app = FastAPI(
    title="InjectGuard Lab",
    description="OpsPilot vulnerable baseline API skeleton",
    version="0.1.0",
)

app.include_router(api_router)
