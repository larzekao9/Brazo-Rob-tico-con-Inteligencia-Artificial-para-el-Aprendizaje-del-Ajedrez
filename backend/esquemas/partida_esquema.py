"""Esquemas Pydantic para los endpoints de partidas jugables (/partida)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, NIVEL_MIN


class CrearPartidaRequest(BaseModel):
    """Cuerpo de entrada para POST /partida."""

    nivel: int = Field(default=NIVEL_MAX, ge=NIVEL_MIN, le=NIVEL_MAX)


class EstadoPartidaResponse(BaseModel):
    """Estado actual de una partida."""

    id: str
    fen: str
    terminada: bool
    resultado: str | None = None


class MoverRequest(BaseModel):
    """Cuerpo de entrada para POST /partida/{id}/mover. Jugada en notación UCI (ej. "e2e4")."""

    jugada: str


class ResultadoMovimientoResponse(BaseModel):
    """Cuerpo de salida tras aplicar la jugada humana y la respuesta de Stockfish."""

    fen: str
    jugada_motor: str | None
    terminada: bool
    resultado: str | None
