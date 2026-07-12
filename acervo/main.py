"""FastAPI application factory and entrypoint (ARCH-002, SEC-002)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from acervo import APP_NAME, __version__
from acervo.api.routes import router
from acervo.db.base import init_db

_WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{APP_NAME} — local API",
        version=__version__,
        # OpenAPI docs are disabled by default in production-oriented builds
        # (ARCH-002); enable explicitly for development if needed.
        docs_url=None,
        redoc_url=None,
        lifespan=_lifespan,
    )

    app.include_router(router, prefix="/api")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (_WEB_DIR / "index.html").read_text(encoding="utf-8")

    return app


app = create_app()


def main() -> None:  # pragma: no cover - thin runtime wrapper
    import uvicorn

    from acervo.config import get_settings

    settings = get_settings()
    # Loopback only — never expose to the network without explicit config.
    uvicorn.run("acervo.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
