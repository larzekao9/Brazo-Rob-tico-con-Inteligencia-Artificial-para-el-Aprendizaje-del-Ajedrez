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


class CandidataDetallada(BaseModel):
    """Detalle completo de una de las top-N candidatas reales que evaluó la red neuronal.

    A diferencia de `CandidataModelo` (solo jugada + probabilidad), esta incluye el
    resultado de los 3 chequeos tácticos autónomos que aplica `predecir_jugada_maestra`
    (ver `explicar_top_candidatas`) y la evaluación de Stockfish de ESA jugada puntual
    (oráculo de comparación, regla 1 del PAPs — nunca decide, solo mide).

    `evaluacion_stockfish_cp` queda en `None` cuando Stockfish reporta mate forzado en
    esa línea en vez de un puntaje en centipeones (ver `motor_ajedrez.analizar_posicion`)
    — forzarlo a 0 sería engañoso, un mate no es una posición equilibrada.
    """

    jugada: str
    probabilidad: float = Field(ge=0.0, le=1.0)
    da_jaque_mate: bool
    rival_tiene_mate_en_1: bool
    pieza_colgada: bool
    elegida: bool
    evaluacion_stockfish_cp: int | None = None
    diferencia_cp: int = 0


class InferenciaModeloRequest(BaseModel):
    """Cuerpo de entrada para /inferencia."""

    fen: str


class InferenciaModeloResponse(BaseModel):
    """Cuerpo de salida para /inferencia."""

    jugada_elegida: str
    candidatas: list[CandidataModelo]
    candidatas_detalladas: list[CandidataDetallada] = Field(default_factory=list)
    latencia_ms: float
    comparacion_stockfish: ComparacionStockfish
    saliencia: list[float] = Field(min_length=64, max_length=64)
    atencion_por_bloque: list[float] = Field(default_factory=list)


class EstadoModeloResponse(BaseModel):
    """Cuerpo de salida para /estado-modelo."""

    version: int
    fecha_entrenamiento: str
    num_clases: int
    dispositivo: str
    disponible: bool