"""Endpoints HTTP de visión: capturar una foto de la cámara fija y reconocer
el tablero (HU1, RF06/RF10)."""
from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from backend.esquemas.vision_esquema import ReconocerTableroResponse
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
async def reconocer(
    turno: str = Form("w"),
    foto_subida: UploadFile | None = File(None),
) -> ReconocerTableroResponse:
    """Reconoce el tablero y devuelve su FEN.

    Si se manda `foto_subida` (una imagen ya sacada — ej. de la galería del
    celular, o una que ya se probó y se sabe que reconoce bien), la usa en
    vez de sacar una foto nueva de la cámara fija. Sirve para no depender de
    que la cámara en vivo acierte el encuadre justo en el momento de mostrar
    el sistema — se puede tener una foto ya lista de antemano.
    """
    if foto_subida is not None:
        datos = await foto_subida.read()
        imagen = cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)
        if imagen is None:
            raise HTTPException(status_code=422, detail="No se pudo leer la imagen subida")
    else:
        try:
            imagen = capturar_foto_tablero()
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        fen = reconocer_tablero(imagen, turno=turno)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return ReconocerTableroResponse(fen=fen)
