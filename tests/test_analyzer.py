from datetime import date

from app.analyzer import analizar_dia
from app.sources import AWS_BOT


def test_reporte_del_dia(settings, matcher):
    r = analizar_dia(date(2026, 10, 29), settings, matcher)
    assert r["total_ingresos"] == 8
    assert r["total_bots"] == 7
    por_bot = {x["bot"]: x["ingresos"] for x in r["por_bot"]}
    assert por_bot == {"Googlebot": 3, "GPTBot": 1, "Amazonbot": 1, AWS_BOT: 1, "ClaudeBot": 1}
    por_empresa = {x["empresa"]: x["ingresos"] for x in r["por_empresa"]}
    assert por_empresa == {"Google": 3, "OpenAI": 1, "Amazon": 2, "Anthropic": 1}
    assert r["lineas_invalidas"] == 1
    assert len(r["archivos_leidos"]) == 2
