"""Esquemas Pydantic para el endpoint de simulación 3D en vivo (/simulacion)."""
from __future__ import annotations

from pydantic import BaseModel


class AbrirVentana3DRequest(BaseModel):
    """Cuerpo de entrada para POST /simulacion/abrir-ventana-3d.

    `partida_id` es la partida activa que se está jugando en la Sala de
    Control ahora mismo — el frontend ya la tiene disponible al momento de
    apretar el botón.
    """

    partida_id: str


class AbrirVentana3DResponse(BaseModel):
    """Confirma que el proceso de la ventana 3D se lanzó — no que ya está visible."""

    lanzado: bool
