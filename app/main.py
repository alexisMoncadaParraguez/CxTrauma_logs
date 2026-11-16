"""Punto de entrada FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routes import protegido, router
from app.scheduler import crear_scheduler
from app.service import Servicio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.servicio = Servicio(settings)
    scheduler = None
    if settings.scheduler_activo:
        scheduler = crear_scheduler(app.state.servicio)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="CxTrauma Logs — detector de bots", lifespan=lifespan)
app.include_router(router)
app.include_router(protegido)
