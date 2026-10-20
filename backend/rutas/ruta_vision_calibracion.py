"""Endpoints de la calibración de la cámara (proceso A del PLAN_CAMARA.md): asistente de calibración con metadata, vigencia y
comprobación de que la cámara no se movió. Conviven con `GET/PUT/DELETE /vision/calibracion` de `ruta_vision.py`, que siguen igual."""
from __future__ import annotations

import json

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from backend.esquemas.vision_esquema import ComprobarCalibracionResponse, EstadoCalibracionResponse
from backend.rutas.ruta_auth import get_current_facilitador
from backend.rutas.ruta_vision import _leer_foto_subida, _validar_esquinas
from backend.servicios.vision import calibracion_camara
from backend.servicios.vision.camara import _fuente_por_defecto, capturar_foto_tablero

router = APIRouter(prefix="/vision/calibracion", tags=["vision-calibracion"])


def _esquinas_de_formulario(texto: str) -> dict[str, tuple[float, float]]:
    """Esquinas enviadas como JSON en un campo de formulario; 422 si no es un objeto `{nombre: [x, y]}` válido."""
    try:
        esquinas = json.loads(texto)
        if not isinstance(esquinas, dict) or not all(isinstance(v, list) for v in esquinas.values()):
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Las esquinas deben ser un JSON {a1, h1, h8, a8} con pares [x, y]") from error
    return _validar_esquinas(esquinas)


def _fuera_de_la_foto(puntos: dict[str, tuple[float, float]], ancho: int, alto: int) -> list[str]:
    return [nombre for nombre, (x, y) in puntos.items() if x > ancho or y > alto]


@router.get("/estado", response_model=EstadoCalibracionResponse)
def estado_calibracion(_facilitador_id: int = Depends(get_current_facilitador)) -> EstadoCalibracionResponse:
    """Si el tablero está calibrado y si la calibración sigue vigente para la cámara actual (resolución y fuente).

    Saca una foto para conocer la resolución; si la cámara no responde, `vigente` queda en `null` con el motivo.
    """
    try:
        alto, ancho = capturar_foto_tablero().shape[:2]
        resolucion: tuple[int, int] | None = (int(ancho), int(alto))
    except Exception:
        resolucion = None
    return EstadoCalibracionResponse(**calibracion_camara.estado(resolucion, str(_fuente_por_defecto())))


@router.post("/previsualizar")
async def previsualizar_calibracion(
    esquinas: str = Form(...),
    foto: UploadFile = File(...),
    _facilitador_id: int = Depends(get_current_facilitador),
) -> Response:
    """Tablero enderezado con la grilla 8x8 para las esquinas dadas sobre la foto dada, sin guardar nada (paso 3 del asistente)."""
    puntos = _esquinas_de_formulario(esquinas)
    imagen = await _leer_foto_subida(foto)
    alto, ancho = imagen.shape[:2]
    if _fuera_de_la_foto(puntos, ancho, alto):
        raise HTTPException(status_code=422, detail="Alguna esquina cae fuera de la foto")
    exito, buffer = cv2.imencode(".jpg", calibracion_camara.previsualizar(imagen, puntos))
    if not exito:
        raise HTTPException(status_code=500, detail="No se pudo codificar la vista previa")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@router.post("/guardar", response_model=EstadoCalibracionResponse)
async def guardar_calibracion(
    esquinas: str = Form(...),
    foto: UploadFile = File(...),
    _facilitador_id: int = Depends(get_current_facilitador),
) -> EstadoCalibracionResponse:
    """Guarda las esquinas con la metadata de la sesión (resolución de la foto, cámara, fecha) y la foto de referencia.

    Los errores graves (esquinas no convexas, fuera de la foto) son 422; lo dudoso (tablero muy chico, muy inclinado, esquina
    pegada al borde) se guarda igual y vuelve en `advertencias`.
    """
    puntos = _esquinas_de_formulario(esquinas)
    imagen = await _leer_foto_subida(foto)
    alto, ancho = imagen.shape[:2]
    fuera = _fuera_de_la_foto(puntos, ancho, alto)
    if fuera:
        raise HTTPException(status_code=422, detail=f"Las esquinas {', '.join(fuera)} caen fuera de la foto ({ancho}×{alto})")
    advertencias = calibracion_camara.evaluar_calidad(puntos, (ancho, alto))
    fuente = str(_fuente_por_defecto())
    calibracion_camara.guardar_calibracion(puntos, imagen, fuente, advertencias)
    return EstadoCalibracionResponse(**calibracion_camara.estado((int(ancho), int(alto)), fuente))


@router.post("/comprobar", response_model=ComprobarCalibracionResponse)
async def comprobar_calibracion(
    foto: UploadFile | None = File(None),
    _facilitador_id: int = Depends(get_current_facilitador),
) -> ComprobarCalibracionResponse:
    """Compara una foto nueva (la subida, o una de la cámara fija) con la de referencia: avisa si la cámara se movió."""
    if foto is not None:
        imagen = await _leer_foto_subida(foto)
    else:
        try:
            imagen = capturar_foto_tablero()
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    return ComprobarCalibracionResponse(**calibracion_camara.comprobar_movimiento(imagen))
