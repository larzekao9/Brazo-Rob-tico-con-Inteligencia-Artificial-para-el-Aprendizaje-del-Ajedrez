"""Endpoints HTTP de visión: capturar una foto de la cámara fija y reconocer
el tablero (HU1, RF06/RF10)."""
from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from backend.esquemas.vision_esquema import ReconocerTableroResponse
from backend.rutas.ruta_auth import get_current_user
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.reconocimiento import generar_imagen_grilla_debug, reconocer_tablero

# Todas las rutas exigen token: capturan la cámara fija y devuelven su imagen,
# así que no pueden quedar abiertas a quien llegue al backend.
router = APIRouter(prefix="/vision", tags=["vision"])

# Tope de una foto subida a mano. Una foto de celular ronda los pocos MB; sin
# tope, una subida enorme se carga entera en memoria y puede tumbar el backend.
TAMANO_MAXIMO_FOTO_BYTES = 10 * 1024 * 1024


async def _leer_foto_subida(foto_subida: UploadFile) -> np.ndarray:
    """Lee una foto subida a mano, con tope de tamaño, y la decodifica a BGR.

    Lee como máximo un byte de más que el tope: alcanza para detectar que se
    pasó sin cargar un archivo enorme completo en memoria.
    """
    datos = await foto_subida.read(TAMANO_MAXIMO_FOTO_BYTES + 1)
    if len(datos) > TAMANO_MAXIMO_FOTO_BYTES:
        raise HTTPException(status_code=413, detail="La foto supera el tamaño máximo de 10 MB")
    imagen = cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise HTTPException(status_code=422, detail="No se pudo leer la imagen subida")
    return imagen


@router.get("/foto")
def foto(_usuario_id: int = Depends(get_current_user)) -> Response:
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
    _usuario_id: int = Depends(get_current_user),
) -> ReconocerTableroResponse:
    """Reconoce el tablero y devuelve su FEN.

    Si se manda `foto_subida` (una imagen ya sacada — ej. de la galería del
    celular, o una que ya se probó y se sabe que reconoce bien), la usa en
    vez de sacar una foto nueva de la cámara fija. Sirve para no depender de
    que la cámara en vivo acierte el encuadre justo en el momento de mostrar
    el sistema — se puede tener una foto ya lista de antemano.
    """
    if foto_subida is not None:
        imagen = await _leer_foto_subida(foto_subida)
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


@router.post("/grilla-debug")
async def grilla_debug(
    foto_subida: UploadFile | None = File(None),
    _usuario_id: int = Depends(get_current_user),
) -> Response:
    """Devuelve la foto enderezada con la grilla 8x8 dibujada encima — prueba
    visual de que la detección geométrica (esquinas, perspectiva, alineación)
    encontró el tablero bien, sin depender de la clasificación de piezas.
    Mismo criterio que `/reconocer`: usa `foto_subida` si llega, si no
    recurre a la cámara fija.
    """
    if foto_subida is not None:
        imagen = await _leer_foto_subida(foto_subida)
    else:
        try:
            imagen = capturar_foto_tablero()
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        debug = generar_imagen_grilla_debug(imagen)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    exito, buffer = cv2.imencode(".jpg", debug)
    if not exito:
        raise HTTPException(status_code=500, detail="No se pudo codificar la imagen de grilla")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")
