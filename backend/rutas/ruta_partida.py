"""Endpoints HTTP para partidas jugables contra la estrategia de jugada activa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.esquemas.partida_esquema import (
    AnalisisCompletoResponse,
    CrearPartidaRequest,
    EstadoPartidaResponse,
    JugadasLegalesResponse,
    MoverRequest,
    ResultadoMovimientoResponse,
    ResumenPartidaResponse,
)
from backend.modelos.partida import Partida
from backend.rutas.ruta_auth import get_current_user
from backend.servicios.partida.servicio_partida import (
    analisis_completo,
    crear_partida,
    jugadas_legales_desde,
    listar_partidas,
    mover,
    mover_desde_foto,
    obtener_partida,
)

router = APIRouter(prefix="/partida", tags=["partida"])


def _a_estado(partida: Partida) -> EstadoPartidaResponse:
    return EstadoPartidaResponse(
        id=partida.id,
        tipo=partida.tipo,
        tipo_oponente=partida.tipo_oponente,
        nivel=partida.nivel,
        creada_en=partida.creada_en,
        fen=partida.fen,
        fen_inicial=partida.fen_inicial,
        terminada=partida.terminada,
        resultado=partida.resultado,
        jugadas=partida.jugadas_san,
    )


def _a_resumen(partida: Partida) -> ResumenPartidaResponse:
    return ResumenPartidaResponse(
        id=partida.id,
        tipo=partida.tipo,
        tipo_oponente=partida.tipo_oponente,
        nivel=partida.nivel,
        creada_en=partida.creada_en,
        fen=partida.fen,
        terminada=partida.terminada,
        resultado=partida.resultado,
        cantidad_jugadas=len(partida.jugadas_san),
    )


@router.post("", response_model=EstadoPartidaResponse)
def crear(
    request: CrearPartidaRequest,
    usuario_id: int = Depends(get_current_user),
) -> EstadoPartidaResponse:
    """Requiere `Authorization: Bearer <token>` (HU10) — la partida queda asociada
    al usuario del token, para poder filtrarla después en `/usuario/estadisticas`
    y `/usuario/historial-partidas`."""
    try:
        partida = crear_partida(
            nivel=request.nivel,
            tipo_oponente=request.tipo_oponente,
            fen_inicial=request.fen_inicial,
            usuario_id=usuario_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _a_estado(partida)


@router.get("", response_model=list[ResumenPartidaResponse])
def listar() -> list[ResumenPartidaResponse]:
    """Registro de partidas jugadas mientras este proceso sigue corriendo.

    No sobrevive un reinicio del backend (`RepositorioPartidasEnMemoria`, ver
    sección 4.3 y 7 de PLAN_IMPLEMENTACION_COMPLETO.md) — pero es un registro
    real, no datos de ejemplo.
    """
    return [_a_resumen(partida) for partida in listar_partidas()]


@router.get("/{partida_id}", response_model=EstadoPartidaResponse)
def estado(partida_id: str, usuario_id: int = Depends(get_current_user)) -> EstadoPartidaResponse:
    """Requiere `Authorization: Bearer <token>` (HU10) — 403 si la partida es de otro usuario."""
    try:
        partida = obtener_partida(partida_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if partida.usuario_id is not None and partida.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="La partida pertenece a otro usuario")
    return _a_estado(partida)


@router.get("/{partida_id}/jugadas-legales", response_model=JugadasLegalesResponse)
def jugadas_legales(partida_id: str, casilla: str) -> JugadasLegalesResponse:
    try:
        casillas = jugadas_legales_desde(partida_id, casilla)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JugadasLegalesResponse(casillas=casillas)


@router.post("/{partida_id}/mover", response_model=ResultadoMovimientoResponse)
def mover_partida(partida_id: str, request: MoverRequest) -> ResultadoMovimientoResponse:
    try:
        resultado = mover(partida_id, request.jugada)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ResultadoMovimientoResponse(**resultado)


@router.post("/{partida_id}/mover-desde-foto", response_model=ResultadoMovimientoResponse)
def mover_partida_desde_foto(partida_id: str) -> ResultadoMovimientoResponse:
    """Detecta la jugada hecha en el tablero físico (cámara fija) y la aplica (RF11)."""
    try:
        resultado = mover_desde_foto(partida_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (RuntimeError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ResultadoMovimientoResponse(**resultado)


@router.get("/{partida_id}/analisis-completo", response_model=AnalisisCompletoResponse)
def analisis_completo_partida(partida_id: str) -> AnalisisCompletoResponse:
    """Analiza con Stockfish cada jugada de la partida, para la vista de aprendizaje (HU5/HU6)."""
    try:
        return AnalisisCompletoResponse(**analisis_completo(partida_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
