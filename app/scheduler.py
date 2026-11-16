"""Programa el envío diario (por defecto 11:00, hora de Chile)."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.service import Servicio


def crear_scheduler(servicio: Servicio) -> BackgroundScheduler:
    hora, minuto = (int(x) for x in servicio.settings.hora_envio.split(":"))
    scheduler = BackgroundScheduler(timezone=servicio.settings.zona_horaria)
    scheduler.add_job(
        servicio.job_diario,
        CronTrigger(hour=hora, minute=minuto, timezone=servicio.settings.zona_horaria),
        id="envio_diario_ga4",
        misfire_grace_time=3600,
        coalesce=True,
    )
    return scheduler
