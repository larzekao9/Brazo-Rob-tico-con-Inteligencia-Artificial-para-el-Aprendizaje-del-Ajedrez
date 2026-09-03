"""Endpoints HTTP para partidas jugables contra Stockfish."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.game.servicio import crear_partida, mover, obtener_partida
from backend.models.esquemas import (
    CrearPartidaRequest,
    EstadoPartidaResponse,
    MoverRequest,
    ResultadoMovimientoResponse,
)

router = APIRouter(prefix="/partida", tags=["partida"])


@router.post("", response_model=EstadoPartidaResponse)
def crear(request: CrearPartidaRequest) -> EstadoPartidaResponse:
    partida = crear_partida(nivel=request.nivel)
    return EstadoPartidaResponse(id=partida.id, fen=partida.fen, terminada=partida.terminada)


@router.get("/{partida_id}", response_model=EstadoPartidaResponse)
def estado(partida_id: str) -> EstadoPartidaResponse:
    try:
        partida = obtener_partida(partida_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return EstadoPartidaResponse(
        id=partida.id, fen=partida.fen, terminada=partida.terminada, resultado=partida.resultado
    )


@router.post("/{partida_id}/mover", response_model=ResultadoMovimientoResponse)
def mover_partida(partida_id: str, request: MoverRequest) -> ResultadoMovimientoResponse:
    try:
        resultado = mover(partida_id, request.jugada)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ResultadoMovimientoResponse(**resultado)
