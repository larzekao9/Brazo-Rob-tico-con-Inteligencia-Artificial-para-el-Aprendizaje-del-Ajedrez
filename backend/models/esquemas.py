"""Esquemas Pydantic para la API del backend."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.engine.stockfish_wrapper import NIVEL_MAX, NIVEL_MIN


class JugadaRequest(BaseModel):
    """Cuerpo de entrada para /jugada y /analisis."""

    fen: str
    nivel: int = Field(default=NIVEL_MAX, ge=NIVEL_MIN, le=NIVEL_MAX)


class JugadaResponse(BaseModel):
    """Cuerpo de salida para /jugada."""

    jugada: str


class AnalisisResponse(BaseModel):
    """Cuerpo de salida para /analisis."""

    jugada: str | None
    evaluacion_cp: int | None
    mate_en: int | None


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
