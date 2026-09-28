"""Esquemas Pydantic para el panel de entrenamiento del facilitador (HU4, base
del dataset — el reentrenamiento en sí todavía no está construido).
"""
from __future__ import annotations

from pydantic import BaseModel


class DescargarDatasetRequest(BaseModel):
    """Cuerpo de entrada para POST /entrenamiento/dataset.

    `solo_nuevas=true` exporta solo las partidas válidas registradas después
    del corte de la última descarga (ver `servicio_dataset.estado_entrenamiento`,
    campo `partidas_nuevas`); `false` (por defecto) exporta todas las
    partidas válidas históricas."""

    solo_nuevas: bool = False


class UltimaDescargaInfo(BaseModel):
    """Datos de la descarga de dataset más reciente, si hubo alguna."""

    fecha: str
    cantidad_partidas: int
    cantidad_jugadas: int
    facilitador: str | None = None


class EstadoEntrenamientoResponse(BaseModel):
    """Cuerpo de salida para GET /entrenamiento/estado (panel del facilitador).

    `partidas_nuevas`/`jugadas_jugador_nuevas` cuentan las partidas válidas
    registradas después del `corte_en` de la última descarga (o todas las
    válidas, si nunca se descargó nada). `progreso` es
    `min(1, partidas_nuevas / umbral_partidas)`. `modelo_actual` es el
    nombre del archivo del checkpoint que usa Turing por defecto, o `null`
    si no hay ninguno todavía."""

    umbral_partidas: int
    minimo_jugadas_por_partida: int
    partidas_validas_total: int
    partidas_nuevas: int
    jugadas_jugador_nuevas: int
    progreso: float
    listo_para_entrenar: bool
    ultima_descarga: UltimaDescargaInfo | None = None
    modelo_actual: str | None = None
