"""FastAPI dependencies — pull shared services off the app-scoped container."""

from __future__ import annotations

from fastapi import Request

from app.container import AppContainer


def get_container(request: Request) -> AppContainer:
    """Return the ``AppContainer`` created during FastAPI lifespan startup."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("AppContainer is not initialized; check FastAPI lifespan wiring")
    return container
