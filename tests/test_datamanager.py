import httpx
import pytest

from app import datamanager


def reporte():
    return {
        "fecha": "2026-10-29",
        "por_bot": [
            {"bot": "Googlebot", "empresa": "Google", "ingresos": 3},
            {"bot": "ClaudeBot", "empresa": "Anthropic", "ingresos": 1},
        ],
    }


def test_payload(settings):
    p = datamanager.construir_payload(reporte(), settings, validate_only=True)
    dest = p["destinations"][0]
    assert dest["operatingAccount"] == {"accountType": "GOOGLE_ANALYTICS_PROPERTY", "accountId": "123"}
    assert dest["productDestinationId"] == "G-TEST"
    assert p["validateOnly"] is True
    ev = p["events"][0]
    assert ev["eventName"] == "bot_traffic_daily"
    assert ev["transactionId"] == "2026-10-29-Googlebot"
    assert ev["eventTimestamp"] == "2026-10-29T12:00:00-03:00"
    params = {x["parameterName"]: x["value"] for x in ev["additionalEventParameters"]}
    assert params == {"bot_name": "Googlebot", "bot_company": "Google", "bot_hits": "3", "fecha_log": "2026-10-29"}
    # clientId estable y distinto por bot
    assert ev["clientId"] == datamanager._client_id("Googlebot") != p["events"][1]["clientId"]


def test_enviar(settings, monkeypatch):
    monkeypatch.setattr(datamanager, "_token", lambda s: "tok")
    vistos = {}

    def handler(request):
        vistos["auth"] = request.headers["Authorization"]
        return httpx.Response(200, json={"requestId": "abc"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    payload = datamanager.construir_payload(reporte(), settings, validate_only=True)
    r = datamanager.enviar(payload, settings, client)
    assert r == {"enviado": True, "eventos": 2, "respuesta": {"requestId": "abc"}}
    assert vistos["auth"] == "Bearer tok"


def test_enviar_error(settings, monkeypatch):
    monkeypatch.setattr(datamanager, "_token", lambda s: "tok")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(400, text="mal")))
    payload = datamanager.construir_payload(reporte(), settings, validate_only=True)
    with pytest.raises(datamanager.DataManagerError):
        datamanager.enviar(payload, settings, client)
