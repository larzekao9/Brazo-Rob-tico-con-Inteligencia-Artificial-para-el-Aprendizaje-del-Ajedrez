"""Endpoints HTTP de estadísticas del jugador (HU14)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.esquemas.usuario_esquema import EstadisticasUsuarioResponse, HistorialPartidasResponse
from backend.rutas.ruta_auth import get_current_user, get_db
from backend.servicios.usuario.servicio_estadisticas import (
    calcular_estadisticas,
    obtener_historial_partidas,
)

router = APIRouter(prefix="/usuario", tags=["usuario"])


@router.get("/estadisticas", response_model=EstadisticasUsuarioResponse)
def estadisticas(
    usuario_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EstadisticasUsuarioResponse:
    """Estadísticas agregadas del usuario autenticado (requiere `Authorization: Bearer <token>`)."""
    return EstadisticasUsuarioResponse(**calcular_estadisticas(db, usuario_id))


@router.get("/historial-partidas", response_model=HistorialPartidasResponse)
def historial_partidas(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    usuario_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistorialPartidasResponse:
    """Historial paginado de partidas del usuario autenticado, más reciente primero."""
    return HistorialPartidasResponse(**obtener_historial_partidas(db, usuario_id, limit, offset))
