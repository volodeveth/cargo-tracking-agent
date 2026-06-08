from __future__ import annotations
from fastapi import FastAPI
from .routes import router
from .web import web_router


def create_app() -> FastAPI:
    app = FastAPI(title="Cargo Tracking Agent")
    app.include_router(router)
    app.include_router(web_router)
    return app


app = create_app()
