"""Agrega los ingresos de bots de un día."""

from collections import Counter
from datetime import date

from app.config import Settings
from app.log_parser import ResultadoLectura, leer_dia
from app.matcher import Matcher

TOP = 20


def analizar_dia(dia: date, settings: Settings, matcher: Matcher) -> dict:
    lectura = ResultadoLectura(archivos=[])
    total = 0
    por_bot: Counter[str] = Counter()
    por_empresa: Counter[str] = Counter()
    empresa_bot: dict[str, str] = {}
    ips: Counter[tuple[str, str]] = Counter()
    rutas: Counter[str] = Counter()

    for linea in leer_dia(
        settings.apache_log_glob, settings.log_format_regex, dia, settings.zona_horaria, lectura
    ):
        total += 1
        c = matcher.buscar(linea.ip)
        if c is None:
            continue
        por_bot[c.bot] += 1
        por_empresa[c.empresa] += 1
        empresa_bot[c.bot] = c.empresa
        ips[(linea.ip, c.bot)] += 1
        rutas[linea.ruta] += 1

    total_bots = sum(por_bot.values())
    return {
        "fecha": dia.isoformat(),
        "total_ingresos": total,
        "total_bots": total_bots,
        "porcentaje_bots": round(100 * total_bots / total, 2) if total else 0.0,
        "por_bot": [
            {"bot": bot, "empresa": empresa_bot[bot], "ingresos": n}
            for bot, n in por_bot.most_common()
        ],
        "por_empresa": [{"empresa": e, "ingresos": n} for e, n in por_empresa.most_common()],
        "top_ips": [
            {"ip": ip, "bot": bot, "ingresos": n} for (ip, bot), n in ips.most_common(TOP)
        ],
        "top_rutas": [{"ruta": r, "ingresos": n} for r, n in rutas.most_common(TOP)],
        "archivos_leidos": lectura.archivos,
        "lineas_invalidas": lectura.lineas_invalidas,
    }
