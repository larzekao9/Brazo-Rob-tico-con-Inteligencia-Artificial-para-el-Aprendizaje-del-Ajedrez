"""Endpoints HTTP de visión: capturar una foto de la cámara fija y reconocer
el tablero (HU1, RF06/RF10)."""
from __future__ import annotations

import cv2
from fastapi import APIRouter, HTTPException, Response

from backend.esquemas.vision_esquema import ReconocerTableroRequest, ReconocerTableroResponse
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.reconocimiento import reconocer_tablero

router = APIRouter(prefix="/vision", tags=["vision"])


@router.get("/foto")
def foto() -> Response:
    """Captura una foto de la cámara fija y la devuelve como JPEG."""
    try:
        imagen = capturar_foto_tablero()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    exito, buffer = cv2.imencode(".jpg", imagen)
    if not exito:
        raise HTTPException(status_code=500, detail="No se pudo codificar la foto capturada")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@router.post("/reconocer", response_model=ReconocerTableroResponse)
def reconocer(request: ReconocerTableroRequest) -> ReconocerTableroResponse:
    """Captura una foto de la cámara fija y reconoce el tablero, devolviendo su FEN."""
    try:
        imagen = capturar_foto_tablero()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    try:
        fen = reconocer_tablero(imagen, turno=request.turno)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return ReconocerTableroResponse(fen=fen)
