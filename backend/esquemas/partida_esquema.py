"""Esquemas Pydantic para los endpoints de partidas jugables (/partida)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, NIVEL_MIN


class CrearPartidaRequest(BaseModel):
    """Cuerpo de entrada para POST /partida.

    `tipo_oponente` hoy solo admite `"motor"` (Stockfish) — pedir cualquier
    otro valor devuelve 400 (ver `fabrica_estrategias.TIPOS_SOPORTADOS`);
    `"modelo"` queda disponible en cuanto HU3/HU4 den un modelo entrenado.
    """

    nivel: int = Field(default=NIVEL_MAX, ge=NIVEL_MIN, le=NIVEL_MAX)
    tipo_oponente: str = "motor"


class EstadoPartidaResponse(BaseModel):
    """Estado completo de una partida, incluidas todas sus jugadas hasta ahora."""

    id: str
    tipo: str
    tipo_oponente: str
    nivel: int
    creada_en: str
    fen: str
    terminada: bool
    resultado: str | None = None
    jugadas: list[str] = Field(default_factory=list)


class ResumenPartidaResponse(BaseModel):
    """Una fila del registro de partidas — sin la lista completa de jugadas."""

    id: str
    tipo: str
    tipo_oponente: str
    nivel: int
    creada_en: str
    fen: str
    terminada: bool
    resultado: str | None = None
    cantidad_jugadas: int


class MoverRequest(BaseModel):
    """Cuerpo de entrada para POST /partida/{id}/mover. Jugada en notación UCI (ej. "e2e4")."""

    jugada: str


class ResultadoMovimientoResponse(BaseModel):
    """Cuerpo de salida tras aplicar la jugada humana y la respuesta de Stockfish."""

    fen: str
    jugada_motor: str | None
    terminada: bool
    resultado: str | None
    jugadas: list[str] = Field(default_factory=list)
