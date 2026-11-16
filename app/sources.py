"""Descarga, caché y normalización de las listas de IP publicadas por las empresas."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

from app.config import Settings

log = logging.getLogger(__name__)

IPVERSE_URL = "https://raw.githubusercontent.com/ipverse/bot-ip-blocks/master/crawlers.json"
GOOGLE_BASE = "https://developers.google.com/static/search/apis/ipranges"
AWS_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
AWS_BOT = "Amazon AWS (nube, no verificado)"

# Prioridad: menor número gana cuando una IP calza con varias listas
PRIORIDAD_BOT = 0
PRIORIDAD_NUBE = 10

# Bot → empresa. Lo que no esté aquí usa el nombre del servicio.
EMPRESAS = {
    "Googlebot": "Google",
    "Google (special)": "Google",
    "Google (user-triggered)": "Google",
    "GPTBot": "OpenAI",
    "ChatGPT-User": "OpenAI",
    "OAI-SearchBot": "OpenAI",
    "ClaudeBot": "Anthropic",
    "Amazonbot": "Amazon",
    AWS_BOT: "Amazon",
    "Bingbot": "Microsoft",
    "Applebot": "Apple",
    "Meta-ExternalAgent": "Meta",
    "PerplexityBot": "Perplexity",
    "DuckDuckBot": "DuckDuckGo",
    "Common Crawl": "Common Crawl",
    "Kagibot": "Kagi",
    "Yandex": "Yandex",
    "Ahrefs": "Ahrefs",
    "SE Ranking": "SE Ranking",
    "SERankingBacklinksBot": "SE Ranking",
}


def empresa_de(bot: str) -> str:
    return EMPRESAS.get(bot, bot)


@dataclass
class BotRanges:
    bot: str
    cidrs: list[str]
    prioridad: int = PRIORIDAD_BOT

    @property
    def empresa(self) -> str:
        return empresa_de(self.bot)


@dataclass
class Fuente:
    clave: str
    url: str
    parser: Callable[[dict], list[BotRanges]]


@dataclass
class EstadoFuente:
    clave: str
    url: str
    rangos: int = 0
    actualizado: str | None = None
    error: str | None = None


@dataclass
class Catalogo:
    bots: list[BotRanges] = field(default_factory=list)
    estado: list[EstadoFuente] = field(default_factory=list)


# --- Parsers por formato ---------------------------------------------------


def parse_ipverse(data: dict) -> list[BotRanges]:
    salida = []
    for nombre, info in data.get("services", {}).items():
        cidrs = list(info.get("ipv4", [])) + list(info.get("ipv6", []))
        if cidrs:
            salida.append(BotRanges(nombre, cidrs))
    return salida


def parser_prefixes(bot: str) -> Callable[[dict], list[BotRanges]]:
    """Formato de Google y OpenAI: {"prefixes": [{"ipv4Prefix": ...} | {"ipv6Prefix": ...}]}."""

    def _parse(data: dict) -> list[BotRanges]:
        cidrs = [
            p.get("ipv4Prefix") or p.get("ipv6Prefix")
            for p in data.get("prefixes", [])
            if p.get("ipv4Prefix") or p.get("ipv6Prefix")
        ]
        return [BotRanges(bot, cidrs)] if cidrs else []

    return _parse


def parse_aws(data: dict) -> list[BotRanges]:
    cidrs = {p["ip_prefix"] for p in data.get("prefixes", []) if "ip_prefix" in p}
    cidrs |= {p["ipv6_prefix"] for p in data.get("ipv6_prefixes", []) if "ipv6_prefix" in p}
    return [BotRanges(AWS_BOT, sorted(cidrs), PRIORIDAD_NUBE)] if cidrs else []


def fuentes(settings: Settings) -> list[Fuente]:
    lista = [
        Fuente("ipverse", IPVERSE_URL, parse_ipverse),
        Fuente("google-googlebot", f"{GOOGLE_BASE}/googlebot.json", parser_prefixes("Googlebot")),
        Fuente(
            "google-special",
            f"{GOOGLE_BASE}/special-crawlers.json",
            parser_prefixes("Google (special)"),
        ),
        Fuente(
            "google-user-triggered",
            f"{GOOGLE_BASE}/user-triggered-fetchers.json",
            parser_prefixes("Google (user-triggered)"),
        ),
        Fuente("openai-gptbot", "https://openai.com/gptbot.json", parser_prefixes("GPTBot")),
        Fuente(
            "openai-searchbot", "https://openai.com/searchbot.json", parser_prefixes("OAI-SearchBot")
        ),
        Fuente(
            "openai-chatgpt-user",
            "https://openai.com/chatgpt-user.json",
            parser_prefixes("ChatGPT-User"),
        ),
    ]
    if settings.incluir_aws:
        lista.append(Fuente("aws", AWS_URL, parse_aws))
    return lista


# --- Caché -----------------------------------------------------------------


def _ruta_cache(settings: Settings, clave: str) -> Path:
    return settings.sources_dir / f"{clave}.json"


def _leer_cache(ruta: Path) -> tuple[dict, str] | None:
    if not ruta.exists():
        return None
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return contenido["data"], contenido["actualizado"]


def _guardar_cache(ruta: Path, data: dict) -> str:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ruta.write_text(json.dumps({"actualizado": ahora, "data": data}), encoding="utf-8")
    return ahora


def cargar_catalogo(settings: Settings, refrescar: bool = False) -> Catalogo:
    """Carga todas las fuentes. Con `refrescar` descarga; si falla, usa la última caché."""
    catalogo = Catalogo()
    with httpx.Client(timeout=settings.timeout_descarga, follow_redirects=True) as client:
        for fuente in fuentes(settings):
            estado = EstadoFuente(fuente.clave, fuente.url)
            ruta = _ruta_cache(settings, fuente.clave)
            data = None

            if refrescar or not ruta.exists():
                try:
                    resp = client.get(fuente.url)
                    resp.raise_for_status()
                    data = resp.json()
                    estado.actualizado = _guardar_cache(ruta, data)
                except (httpx.HTTPError, ValueError) as e:
                    estado.error = f"{type(e).__name__}: {e}"
                    log.warning("No se pudo descargar %s: %s", fuente.url, e)

            if data is None:
                cache = _leer_cache(ruta)
                if cache:
                    data, estado.actualizado = cache

            if data is not None:
                bots = fuente.parser(data)
                estado.rangos = sum(len(b.cidrs) for b in bots)
                catalogo.bots.extend(bots)
            catalogo.estado.append(estado)
    return catalogo
