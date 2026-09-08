"""Endpoints HTTP para partidas jugables contra la estrategia de jugada activa."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.esquemas.partida_esquema import (
    CrearPartidaRequest,
    EstadoPartidaResponse,
    MoverRequest,
    ResultadoMovimientoResponse,
    ResumenPartidaResponse,
)
from backend.modelos.partida import Partida
from backend.servicios.partida.servicio_partida import (
    crear_partida,
    listar_partidas,
    mover,
    obtener_partida,
)

router = APIRouter(prefix="/partida", tags=["partida"])


def _a_estado(partida: Partida) -> EstadoPartidaResponse:
    return EstadoPartidaResponse(
        id=partida.id,
        tipo=partida.tipo,
        nivel=partida.nivel,
        creada_en=partida.creada_en,
        fen=partida.fen,
        terminada=partida.terminada,
        resultado=partida.resultado,
        jugadas=partida.jugadas_san,
    )


def _a_resumen(partida: Partida) -> ResumenPartidaResponse:
    return ResumenPartidaResponse(
        id=partida.id,
        tipo=partida.tipo,
        nivel=partida.nivel,
        creada_en=partida.creada_en,
        fen=partida.fen,
        terminada=partida.terminada,
        resultado=partida.resultado,
        cantidad_jugadas=len(partida.jugadas_san),
    )


@router.post("", response_model=EstadoPartidaResponse)
def crear(request: CrearPartidaRequest) -> EstadoPartidaResponse:
    partida = crear_partida(nivel=request.nivel)
    return _a_estado(partida)


@router.get("", response_model=list[ResumenPartidaResponse])
def listar() -> list[ResumenPartidaResponse]:
    """Registro de partidas jugadas mientras este proceso sigue corriendo.

    No sobrevive un reinicio del backend (`RepositorioPartidasEnMemoria`, ver
    sección 4.3 y 7 de PLAN_IMPLEMENTACION_COMPLETO.md) — pero es un registro
    real, no datos de ejemplo.
    """
    return [_a_resumen(partida) for partida in listar_partidas()]


@router.get("/{partida_id}", response_model=EstadoPartidaResponse)
def estado(partida_id: str) -> EstadoPartidaResponse:
    try:
        partida = obtener_partida(partida_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _a_estado(partida)


@router.post("/{partida_id}/mover", response_model=ResultadoMovimientoResponse)
def mover_partida(partida_id: str, request: MoverRequest) -> ResultadoMovimientoResponse:
    try:
        resultado = mover(partida_id, request.jugada)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ResultadoMovimientoResponse(**resultado)
