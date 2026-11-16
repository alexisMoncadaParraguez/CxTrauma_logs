"""Autenticación simple por header `X-API-Token`."""

import secrets

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def requiere_token(
    x_api_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API_TOKEN no configurado")
    if not x_api_token or not secrets.compare_digest(x_api_token, settings.api_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
