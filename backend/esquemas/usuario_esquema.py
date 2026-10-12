"""Esquemas Pydantic para los endpoints de estadísticas del jugador (/usuario, HU14)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TopErrorItem(BaseModel):
    """Cuenta de jugadas de una categoría de error (blunder/error/inexactitud)."""

    tipo: str
    cantidad: int


class SemanaProgresoItem(BaseModel):
    """Una semana (lunes a domingo) del gráfico de progreso. `precision` es `None` sin jugadas analizadas."""

    semana_inicio: str
    partidas: int
    victorias: int
    precision: float | None = None


class ResultadosRivalItem(BaseModel):
    """Resultados del jugador contra un rival (partidas terminadas y jugadas)."""

    ganadas: int = 0
    perdidas: int = 0
    tablas: int = 0


class FasePrecisionItem(BaseModel):
    """Precisión en una fase de la partida (`apertura`, `medio` o `final`); `None` sin jugadas analizadas."""

    fase: str
    jugadas: int
    precision: float | None = None


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
    # Partidas por rival entre las realmente jugadas (`total_partidas` incluye las que nadie jugó).
    partidas_por_oponente: dict[str, int] = Field(default_factory=dict)
    progreso_semanal: list[SemanaProgresoItem] = Field(default_factory=list)
    resultados_por_oponente: dict[str, ResultadosRivalItem] = Field(default_factory=dict)
    precision_por_fase: list[FasePrecisionItem] = Field(default_factory=list)


class PartidaHistorialItem(BaseModel):
    """Una fila de GET /usuario/historial-partidas.

    Solo incluye partidas con al menos una jugada del jugador (ver
    `servicio_estadisticas.obtener_historial_partidas`) — las que la Sala de
    Control crea sola y nadie llega a jugar no aparecen acá.

    Para partidas `humano` (salas): incluye `rival_nombre`, `codigo_sala`,
    `color` ("blancas"|"negras") y el resultado desde la perspectiva del
    jugador (`1-0`/`0-1`/`1/2-1/2`).
    """

    id: str
    fecha: str
    resultado: str | None
    tipo_oponente: str
    nivel: int
    cantidad_jugadas: int
    estado: str | None = None
    # Campos para partidas humano vs humano
    rival_nombre: str | None = None
    codigo_sala: str | None = None
    color: str | None = None  # "blancas" | "negras"


class HistorialPartidasResponse(BaseModel):
    """Cuerpo de salida para GET /usuario/historial-partidas."""

    total: int
    partidas: list[PartidaHistorialItem] = Field(default_factory=list)
