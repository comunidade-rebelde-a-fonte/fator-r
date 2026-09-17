import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fator_r.api import (
    agents,
    auth,
    companies,
    fator_r,
    health,
    inbox,
    movements,
    observability,
    portfolio,
    simulations,
)
from fator_r.api.deps import require_user
from fator_r.core.db import get_sessionmaker
from fator_r.core.limites import LimiteCorpoMiddleware
from fator_r.core.seguranca_http import SegurancaHttpMiddleware
from fator_r.core.settings import get_settings
from fator_r.tracing.client import get_langfuse, instrumentar_anthropic
from fator_r.tracing.sync import aplicar_status, reenviar_falhas

logger = logging.getLogger(__name__)

# Rotas públicas: só estas. Qualquer outra entra em `protected` (CLAUDE.md §5.3).
PUBLIC_PATHS = frozenset({"/health", "/auth/login"})


async def _job_sync_langfuse() -> None:
    async with get_sessionmaker()() as session:
        await aplicar_status(session)


async def _job_rotina_priorizador() -> None:
    from fator_r.agents.priorizador import rotina_semanal

    await rotina_semanal()


async def _job_reenvio_langfuse() -> None:
    async with get_sessionmaker()() as session:
        await reenviar_falhas(session)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    if settings.langfuse_tracing_enabled:
        instrumentar_anthropic()
        get_langfuse()
    if settings.env != "test":
        scheduler.add_job(_job_sync_langfuse, "interval", seconds=settings.langfuse_sync_interval_s)
        scheduler.add_job(_job_reenvio_langfuse, "interval", minutes=5)
        scheduler.add_job(
            _job_rotina_priorizador,
            "cron",
            day_of_week="sun",
            hour=settings.rotina_priorizador_hora,
            minute=0,
        )
        scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        get_langfuse().flush()


def create_app() -> FastAPI:
    settings = get_settings()
    # Sem /docs, /redoc e /openapi.json públicos; o schema sai de app.openapi() (script).
    app = FastAPI(
        title="Fator R API",
        version="0.1.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    # Multipart do maior upload permitido + margem; vale antes da autenticação (revisão A1).
    app.add_middleware(
        LimiteCorpoMiddleware, max_bytes=settings.upload_max_mb * 1024 * 1024 + 256 * 1024
    )
    app.add_middleware(
        SegurancaHttpMiddleware,
        origens_permitidas=settings.cors_origins,
        hsts=settings.env == "prod",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health.router)
    app.include_router(auth.public_router)

    protected = APIRouter(dependencies=[Depends(require_user)])
    protected.include_router(auth.router)
    protected.include_router(companies.router)
    protected.include_router(movements.router)
    protected.include_router(fator_r.router)
    protected.include_router(portfolio.router)
    protected.include_router(observability.router)
    protected.include_router(inbox.router)
    protected.include_router(simulations.router)
    protected.include_router(agents.router)
    if settings.env in ("dev", "test"):
        from fator_r.api import agents_dev

        protected.include_router(agents_dev.router)
    app.include_router(protected)
    return app


app = create_app()
