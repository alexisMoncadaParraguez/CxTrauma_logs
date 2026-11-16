"""Estado compartido (catálogo de IPs + matcher) y operaciones de alto nivel."""

import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import datamanager
from app.analyzer import analizar_dia
from app.config import Settings
from app.matcher import Matcher
from app.sources import Catalogo, cargar_catalogo

log = logging.getLogger(__name__)


class Servicio:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self.catalogo: Catalogo | None = None
        self.matcher: Matcher | None = None

    def cargar(self, refrescar: bool = False) -> Catalogo:
        catalogo = cargar_catalogo(self.settings, refrescar=refrescar)
        matcher = Matcher(catalogo.bots)
        with self._lock:
            self.catalogo, self.matcher = catalogo, matcher
        return catalogo

    def _matcher(self) -> Matcher:
        if self.matcher is None:
            self.cargar()
        return self.matcher

    def ayer(self) -> date:
        return datetime.now(ZoneInfo(self.settings.zona_horaria)).date() - timedelta(days=1)

    def reporte(self, dia: date) -> dict:
        return analizar_dia(dia, self.settings, self._matcher())

    # --- Registro de envíos (idempotencia) ---

    def _envios(self) -> dict:
        ruta = self.settings.envios_path
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}

    def _registrar_envio(self, dia: date, resultado: dict) -> None:
        envios = self._envios()
        envios[dia.isoformat()] = {
            "enviado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "eventos": resultado.get("eventos", 0),
        }
        ruta = self.settings.envios_path
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(envios, indent=2), encoding="utf-8")

    def enviar(self, dia: date, validate_only: bool | None = None, force: bool = False) -> dict:
        if validate_only is None:
            validate_only = self.settings.dm_validate_only
        if not validate_only and not force and dia.isoformat() in self._envios():
            return {"enviado": False, "motivo": f"{dia} ya fue enviado (usar force)"}

        reporte = self.reporte(dia)
        payload = datamanager.construir_payload(reporte, self.settings, validate_only)
        resultado = datamanager.enviar(payload, self.settings)
        resultado["validate_only"] = validate_only
        resultado["fecha"] = dia.isoformat()
        if resultado.get("enviado") and not validate_only:
            self._registrar_envio(dia, resultado)
        return resultado

    def job_diario(self) -> None:
        """Refresca las listas y envía el día anterior a GA4."""
        dia = self.ayer()
        try:
            self.cargar(refrescar=True)
            resultado = self.enviar(dia)
            log.info("Job diario %s: %s", dia, resultado)
        except Exception:
            log.exception("Falló el job diario para %s", dia)
