"""Esquemas Pydantic para los endpoints de visión (/vision).

POST /vision/reconocer recibe `turno` y (opcionalmente) `foto_subida` como
multipart/form-data, no JSON — para poder mandar una imagen no hay un
esquema Pydantic de entrada, los parámetros se declaran directo en
`ruta_vision.py` con `Form`/`File`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReconocerTableroResponse(BaseModel):
    """Cuerpo de salida para POST /vision/reconocer."""

    fen: str


class EstadoCamaraResponse(BaseModel):
    """Cuerpo de salida para GET /vision/estado."""

    fuente: str
    disponible: bool
    ancho: int | None = None
    alto: int | None = None
    latencia_ms: float | None = None
    error: str | None = None


class CalibracionTableroRequest(BaseModel):
    """Cuerpo de entrada para PUT /vision/calibracion: esquinas en píxeles de la foto de /vision/foto."""

    esquinas: dict[str, list[float]]


class CalibracionTableroResponse(BaseModel):
    """Cuerpo de salida de GET/PUT/DELETE /vision/calibracion."""

    calibrada: bool
    esquinas: dict[str, list[float]] | None = None


class CapturaDatasetRequest(BaseModel):
    """Cuerpo de entrada para POST /vision/dataset/foto: solo el campo de piezas del FEN."""

    fen_piezas: str


class CapturaDatasetResponse(BaseModel):
    """Cuerpo de salida para POST /vision/dataset/foto."""

    captura_id: str
    guardadas: int
    total: int


class ResumenDatasetResponse(BaseModel):
    """Cuerpo de salida para GET /vision/dataset/resumen."""

    por_clase: dict[str, int]
    total: int
    capturas: int
    minimo_recomendado: int


class BorrarCapturaResponse(BaseModel):
    """Cuerpo de salida para DELETE /vision/dataset/captura/{captura_id}."""

    borradas: int


class ReentrenarResponse(BaseModel):
    """Cuerpo de salida para POST /vision/dataset/reentrenar."""

    estado: Literal["en_curso"]


class EstadoReentrenamientoResponse(BaseModel):
    """Cuerpo de salida para GET /vision/dataset/reentrenar/estado."""

    estado: Literal["inactivo", "en_curso", "terminado", "error"]
    log: str
