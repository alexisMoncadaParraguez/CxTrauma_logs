"""Lectura en streaming de los access logs de Apache (incluye rotados y .gz)."""

import glob
import gzip
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FORMATO_FECHA = "%d/%b/%Y:%H:%M:%S %z"


@dataclass
class Linea:
    ip: str
    momento: datetime
    metodo: str
    ruta: str
    estado: int
    user_agent: str


@dataclass
class ResultadoLectura:
    archivos: list[str]
    lineas_invalidas: int = 0


def archivos_log(patron: str) -> list[str]:
    return sorted(glob.glob(patron))


def _abrir(ruta: str):
    if ruta.endswith(".gz"):
        return gzip.open(ruta, "rt", encoding="utf-8", errors="replace")
    return open(ruta, encoding="utf-8", errors="replace")


def parsear_linea(texto: str, regex: re.Pattern) -> Linea | None:
    m = regex.match(texto)
    if not m:
        return None
    try:
        momento = datetime.strptime(m["time"], FORMATO_FECHA)
    except ValueError:
        return None
    return Linea(
        ip=m["ip"],
        momento=momento,
        metodo=m["method"] or "-",
        ruta=m["path"] or "-",
        estado=int(m["status"]),
        user_agent=m.groupdict().get("ua") or "",
    )


def leer_dia(
    patron: str, regex_texto: str, dia: date, zona: str, resultado: ResultadoLectura
) -> Iterator[Linea]:
    """Entrega las líneas cuyo instante cae en `dia` según la zona horaria local."""
    regex = re.compile(regex_texto)
    tz = ZoneInfo(zona)
    for ruta in archivos_log(patron):
        # Saltar archivos que no se tocaron desde antes del día buscado
        if datetime.fromtimestamp(Path(ruta).stat().st_mtime, tz).date() < dia:
            continue
        resultado.archivos.append(ruta)
        with _abrir(ruta) as f:
            for texto in f:
                linea = parsear_linea(texto, regex)
                if linea is None:
                    if texto.strip():
                        resultado.lineas_invalidas += 1
                    continue
                if linea.momento.astimezone(tz).date() == dia:
                    yield linea
