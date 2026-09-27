"""Rutas del tutor conversacional "Turing" (Fase 1: tutor de texto, ver el
plan del tutor y `PLAN_IMPLEMENTACION_COMPLETO.md`)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.esquemas.tutor_esquema import (
    TutorHistorialResponse,
    TutorMensajeRequest,
    TutorMensajeResponse,
    TutorTurnoItem,
)
from backend.rutas.ruta_auth import get_current_user, get_db
from backend.servicios.auth import get_user_by_id
from backend.servicios.tutor import (
    TutorNoDisponibleError,
    borrar_historial_tutor,
    obtener_historial_tutor,
    procesar_mensaje,
)

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post(
    "/mensaje",
    response_model=TutorMensajeResponse,
    summary="Enviarle un mensaje a Turing",
)
def enviar_mensaje(
    data: TutorMensajeRequest,
    usuario_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TutorMensajeResponse:
    """Le manda un mensaje al tutor y devuelve su respuesta (loop ReAct completo).

    503 si Turing no pudo responder (falla de red/API con Groq) — el mensaje
    del jugador queda igual persistido en el historial, así no se pierde su
    pregunta aunque la API externa haya fallado.
    """
    usuario = get_user_by_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        respuesta = procesar_mensaje(db, usuario, data.mensaje)
    except TutorNoDisponibleError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return TutorMensajeResponse(
        respuesta=respuesta, creado_en=datetime.now(timezone.utc).isoformat()
    )


@router.get(
    "/historial",
    response_model=TutorHistorialResponse,
    summary="Historial de conversación con Turing",
)
def historial(
    limite: int = Query(default=50, ge=1, le=200),
    usuario_id: int = Depends(get_current_user),
) -> TutorHistorialResponse:
    """Últimos `limite` turnos de la conversación del usuario autenticado con Turing."""
    turnos = obtener_historial_tutor(usuario_id, limite)
    return TutorHistorialResponse(turnos=[TutorTurnoItem(**turno) for turno in turnos])


@router.delete(
    "/historial",
    status_code=204,
    summary="Reiniciar la conversación con Turing",
)
def eliminar_historial(usuario_id: int = Depends(get_current_user)) -> None:
    """Borra el historial de conversación del usuario autenticado — reset de
    charla, útil si una demo se traba a mitad de conversación."""
    borrar_historial_tutor(usuario_id)
