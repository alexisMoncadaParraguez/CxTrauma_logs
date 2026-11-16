"""Envío de los conteos diarios a Google Analytics 4 vía Google Data Manager API (events:ingest).

Se envía un evento por bot y día. No viajan IPs ni datos de visitantes, solo conteos agregados.
"""

import hashlib
import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings

log = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/datamanager"
MAX_EVENTOS = 2000


class DataManagerError(RuntimeError):
    pass


def _client_id(bot: str) -> str:
    """clientId sintético y estable por bot (formato tipo GA: número.número)."""
    h = int(hashlib.sha256(bot.encode()).hexdigest(), 16)
    return f"{h % 10**10}.{(h // 10**10) % 10**10}"


def construir_payload(reporte: dict, settings: Settings, validate_only: bool) -> dict:
    dia = date.fromisoformat(reporte["fecha"])
    # Mediodía local del día analizado (GA4 acepta eventos de hasta 72 h atrás)
    momento = datetime.combine(dia, time(12, 0), ZoneInfo(settings.zona_horaria))
    timestamp = momento.isoformat()

    eventos = [
        {
            "eventName": settings.dm_event_name,
            "eventTimestamp": timestamp,
            "transactionId": f"{reporte['fecha']}-{item['bot']}",
            "clientId": _client_id(item["bot"]),
            "additionalEventParameters": [
                {"parameterName": "bot_name", "value": item["bot"]},
                {"parameterName": "bot_company", "value": item["empresa"]},
                {"parameterName": "bot_hits", "value": str(item["ingresos"])},
                {"parameterName": "fecha_log", "value": reporte["fecha"]},
            ],
        }
        for item in reporte["por_bot"]
    ][:MAX_EVENTOS]

    return {
        "destinations": [
            {
                "operatingAccount": {
                    "accountType": "GOOGLE_ANALYTICS_PROPERTY",
                    "accountId": settings.ga4_property_id,
                },
                "productDestinationId": settings.ga4_measurement_id,
            }
        ],
        "events": eventos,
        "validateOnly": validate_only,
    }


def _token(settings: Settings) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    credenciales = service_account.Credentials.from_service_account_file(
        settings.google_application_credentials, scopes=[SCOPE]
    )
    credenciales.refresh(Request())
    return credenciales.token


def enviar(payload: dict, settings: Settings, client: httpx.Client | None = None) -> dict:
    if not settings.ga4_property_id or not settings.ga4_measurement_id:
        raise DataManagerError("Faltan GA4_PROPERTY_ID / GA4_MEASUREMENT_ID")
    if not payload["events"]:
        return {"enviado": False, "motivo": "sin eventos"}

    headers = {"Authorization": f"Bearer {_token(settings)}"}
    propio = client is None
    client = client or httpx.Client(timeout=30)
    try:
        resp = client.post(settings.dm_endpoint, json=payload, headers=headers)
    finally:
        if propio:
            client.close()
    if resp.status_code >= 400:
        log.error("Data Manager respondió %s: %s", resp.status_code, resp.text)
        raise DataManagerError(f"HTTP {resp.status_code}: {resp.text}")
    return {"enviado": True, "eventos": len(payload["events"]), "respuesta": resp.json()}
