import json

import pytest
from fastapi.testclient import TestClient

from app import datamanager
from app.config import get_settings
from app.main import app
from app.service import Servicio


@pytest.fixture
def client(settings, matcher, monkeypatch):
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as c:
        srv: Servicio = app.state.servicio
        srv.matcher = matcher
        yield c
    app.dependency_overrides.clear()


H = {"X-API-Token": "secreto"}


def test_health_sin_token(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_token_requerido(client):
    assert client.get("/reporte").status_code == 401
    assert client.get("/reporte", headers={"X-API-Token": "otro"}).status_code == 401


def test_reporte(client):
    r = client.get("/reporte?fecha=2026-10-29", headers=H).json()
    assert r["total_bots"] == 7


def test_enviar_idempotente(client, settings, monkeypatch):
    llamadas = []

    def falso(payload, s):
        llamadas.append(payload)
        return {"enviado": True, "eventos": len(payload["events"])}

    monkeypatch.setattr(datamanager, "enviar", falso)
    url = "/enviar?fecha=2026-10-29&validate_only=false"
    assert client.post(url, headers=H).json()["enviado"] is True
    assert client.post(url, headers=H).json()["enviado"] is False  # ya enviado
    assert client.post(url + "&force=true", headers=H).json()["enviado"] is True
    assert len(llamadas) == 2
    assert "2026-10-29" in json.loads(settings.envios_path.read_text())
    # validate_only no registra
    client.post("/enviar?fecha=2026-10-28&validate_only=true", headers=H)
    assert "2026-10-28" not in json.loads(settings.envios_path.read_text())
