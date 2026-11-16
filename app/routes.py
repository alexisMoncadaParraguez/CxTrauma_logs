"""Endpoints HTTP."""

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import requiere_token
from app.datamanager import DataManagerError
from app.service import Servicio

router = APIRouter()
protegido = APIRouter(dependencies=[Depends(requiere_token)])


def servicio(request: Request) -> Servicio:
    return request.app.state.servicio


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@protegido.get("/reporte")
def reporte(fecha: date | None = None, srv: Servicio = Depends(servicio)) -> dict:
    return srv.reporte(fecha or srv.ayer())


@protegido.get("/fuentes")
def listar_fuentes(srv: Servicio = Depends(servicio)) -> dict:
    catalogo = srv.catalogo or srv.cargar()
    return {
        "bots": sorted({b.bot for b in catalogo.bots}),
        "fuentes": [asdict(e) for e in catalogo.estado],
    }


@protegido.post("/fuentes/actualizar")
def actualizar_fuentes(srv: Servicio = Depends(servicio)) -> dict:
    catalogo = srv.cargar(refrescar=True)
    return {"fuentes": [asdict(e) for e in catalogo.estado]}


@protegido.post("/enviar")
def enviar(
    fecha: date | None = None,
    validate_only: bool | None = None,
    force: bool = False,
    srv: Servicio = Depends(servicio),
) -> dict:
    try:
        return srv.enviar(fecha or srv.ayer(), validate_only=validate_only, force=force)
    except DataManagerError as e:
        raise HTTPException(502, str(e)) from e
