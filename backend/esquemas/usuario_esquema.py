"""Esquemas Pydantic para los endpoints de estadísticas del jugador (/usuario, HU14)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TopErrorItem(BaseModel):
    """Cuenta de jugadas de una categoría de error (blunder/error/inexactitud)."""

    tipo: str
    cantidad: int


class EstadisticasUsuarioResponse(BaseModel):
    """Cuerpo de salida para GET /usuario/estadisticas."""

    total_partidas: int
    partidas_ganadas: int
    partidas_perdidas: int
    partidas_tablas: int
    win_percent_promedio: float
    racha_victoria_actual: int
    precision_promedio: float
    top_errores: list[TopErrorItem] = Field(default_factory=list)


class PartidaHistorialItem(BaseModel):
    """Una fila de GET /usuario/historial-partidas."""

    id: str
    fecha: str
    resultado: str | None
    tipo_oponente: str
    nivel: int
    cantidad_jugadas: int


class HistorialPartidasResponse(BaseModel):
    """Cuerpo de salida para GET /usuario/historial-partidas."""

    total: int
    partidas: list[PartidaHistorialItem] = Field(default_factory=list)
