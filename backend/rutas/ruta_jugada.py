"""Endpoints HTTP del motor de ajedrez: calcular jugada y analizar posición."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.esquemas.jugada_esquema import AnalisisResponse, JugadaRequest, JugadaResponse
from backend.servicios.motor.motor_ajedrez import analizar_posicion, calcular_jugada

router = APIRouter(tags=["motor"])


@router.post("/jugada", response_model=JugadaResponse)
def jugada(request: JugadaRequest) -> JugadaResponse:
    """Calcula la jugada elegida por Stockfish para la posición dada."""
    try:
        jugada_san = calcular_jugada(request.fen, nivel=request.nivel)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JugadaResponse(jugada=jugada_san)


@router.post("/analisis", response_model=AnalisisResponse)
def analisis(request: JugadaRequest) -> AnalisisResponse:
    """Analiza la posición dada y devuelve la evaluación de Stockfish."""
    try:
        resultado = analizar_posicion(request.fen, nivel=request.nivel)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AnalisisResponse(**resultado)
