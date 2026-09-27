"""Esquemas Pydantic para el tutor conversacional "Turing" (/tutor)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TutorMensajeRequest(BaseModel):
    """Cuerpo para POST /tutor/mensaje."""

    mensaje: str = Field(min_length=1, max_length=2000)


class TutorMensajeResponse(BaseModel):
    """Cuerpo de salida para POST /tutor/mensaje."""

    respuesta: str
    creado_en: str


class TutorTurnoItem(BaseModel):
    """Un turno del historial de conversación con Turing."""

    rol: str
    contenido: str
    creado_en: str


class TutorHistorialResponse(BaseModel):
    """Cuerpo de salida para GET /tutor/historial."""

    turnos: list[TutorTurnoItem] = Field(default_factory=list)
