"""Esquemas Pydantic para los endpoints de aprendizaje neural (/inferencia, /estado-modelo)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CandidataModelo(BaseModel):
    """Una jugada candidata predicha por el modelo propio."""

    jugada: str
    probabilidad: float = Field(ge=0.0, le=1.0)


class ComparacionStockfish(BaseModel):
    """Comparación con la jugada de Stockfish."""

    jugada_motor: str
    evaluacion_cp: int
    diferencia_cp: int


class InferenciaModeloRequest(BaseModel):
    """Cuerpo de entrada para /inferencia."""

    fen: str


class InferenciaModeloResponse(BaseModel):
    """Cuerpo de salida para /inferencia."""

    jugada_elegida: str
    candidatas: list[CandidataModelo]
    latencia_ms: float
    comparacion_stockfish: ComparacionStockfish
    saliencia: list[float] = Field(min_length=64, max_length=64)


class EstadoModeloResponse(BaseModel):
    """Cuerpo de salida para /estado-modelo."""

    version: int
    fecha_entrenamiento: str
    num_clases: int
    dispositivo: str
    disponible: bool