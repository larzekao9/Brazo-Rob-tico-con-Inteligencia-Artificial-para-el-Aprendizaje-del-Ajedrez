"""Endpoints HTTP de visión: capturar una foto de la cámara fija y reconocer
el tablero (HU1, RF06/RF10)."""
from __future__ import annotations

import json
import math
import time

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from backend.esquemas.vision_esquema import (
    BorrarCapturaResponse,
    CapturaDatasetRequest,
    CapturaDatasetResponse,
    EstadoReentrenamientoResponse,
    FotosPiezaResponse,
    ReentrenarResponse,
    ResumenDatasetResponse,
    CalibracionTableroRequest,
    CalibracionTableroResponse,
    EstadoCamaraResponse,
    ReconocerTableroResponse,
)
from backend.rutas.ruta_auth import get_current_facilitador, get_current_user
from backend.servicios.vision.camara import _fuente_por_defecto, capturar_foto_tablero, flujo_de_frames
from backend.servicios.vision import dataset_propio, tablero, verificacion
from backend.servicios.vision.modelo_piezas import CLASES
from backend.servicios.vision.reconocimiento import generar_imagen_grilla_debug, reconocer_tablero

# Todas las rutas exigen token: capturan la cámara fija y devuelven su imagen,
# así que no pueden quedar abiertas a quien llegue al backend.
router = APIRouter(prefix="/vision", tags=["vision"])

# Tope de una foto subida a mano. Una foto de celular ronda los pocos MB; sin
# tope, una subida enorme se carga entera en memoria y puede tumbar el backend.
TAMANO_MAXIMO_FOTO_BYTES = 10 * 1024 * 1024
MAXIMO_FOTOS_PIEZA = 20


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


@router.get("/estado", response_model=EstadoCamaraResponse)
def estado_camara(_facilitador_id: int = Depends(get_current_facilitador)) -> EstadoCamaraResponse:
    """Estado de la cámara fija: captura una foto de prueba y mide la latencia.

    Nunca devuelve 500: si la captura falla, `disponible=false` y el motivo en `error`.
    """
    fuente = str(_fuente_por_defecto())
    inicio = time.perf_counter()
    try:
        imagen = capturar_foto_tablero()
    except Exception as error:
        return EstadoCamaraResponse(fuente=fuente, disponible=False, error=str(error) or type(error).__name__)
    latencia_ms = (time.perf_counter() - inicio) * 1000
    alto, ancho = imagen.shape[:2]
    return EstadoCamaraResponse(
        fuente=fuente, disponible=True, ancho=int(ancho), alto=int(alto), latencia_ms=round(latencia_ms, 1)
    )


@router.get("/foto")
def foto(grilla: bool = False, _usuario_id: int = Depends(get_current_user)) -> Response:
    """Captura una foto de la cámara fija y la devuelve como JPEG.

    Con `grilla=true` devuelve la foto enderezada con la grilla 8x8 dibujada encima.
    """
    try:
        imagen = capturar_foto_tablero()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if grilla:
        try:
            imagen = generar_imagen_grilla_debug(imagen)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
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


AREA_MINIMA_CALIBRACION_PX2 = 1000.0


def _validar_esquinas(esquinas: dict[str, list[float]]) -> dict[str, tuple[float, float]]:
    """Valida las 4 esquinas y devuelve `{nombre: (x, y)}`; lanza 422 en español si algo no cierra."""
    if set(esquinas) != set(tablero.ORDEN_DE_CLICS):
        raise HTTPException(status_code=422, detail="Hacen falta exactamente las esquinas a1, h1, h8 y a8")
    puntos: dict[str, tuple[float, float]] = {}
    for nombre in tablero.ORDEN_DE_CLICS:
        coordenada = esquinas[nombre]
        if len(coordenada) != 2 or not all(math.isfinite(v) and v >= 0 for v in coordenada):
            raise HTTPException(
                status_code=422, detail=f"La esquina {nombre} debe ser [x, y] con números finitos mayores o iguales a 0"
            )
        puntos[nombre] = (float(coordenada[0]), float(coordenada[1]))

    ciclo = [puntos[nombre] for nombre in tablero.ORDEN_DE_CLICS]
    productos = []
    area_doble = 0.0
    for i in range(4):
        (x1, y1), (x2, y2), (x3, y3) = ciclo[i], ciclo[(i + 1) % 4], ciclo[(i + 2) % 4]
        productos.append((x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2))
        area_doble += x1 * y2 - x2 * y1
    convexo = all(p > 0 for p in productos) or all(p < 0 for p in productos)
    if not convexo or abs(area_doble) / 2 <= AREA_MINIMA_CALIBRACION_PX2:
        raise HTTPException(
            status_code=422,
            detail="Las esquinas no forman un cuadrilátero convexo de tamaño razonable: marcalas en orden a1, h1, h8, a8",
        )
    return puntos


def _estado_calibracion() -> CalibracionTableroResponse:
    ruta = tablero.ARCHIVO_ESQUINAS
    if not ruta.exists():
        return CalibracionTableroResponse(calibrada=False, esquinas=None)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        esquinas = {nombre: [float(datos[nombre][0]), float(datos[nombre][1])] for nombre in tablero.ORDEN_DE_CLICS}
    except (ValueError, KeyError, TypeError, IndexError):
        return CalibracionTableroResponse(calibrada=False, esquinas=None)
    return CalibracionTableroResponse(calibrada=True, esquinas=esquinas)


@router.get("/calibracion", response_model=CalibracionTableroResponse)
def obtener_calibracion(_facilitador_id: int = Depends(get_current_facilitador)) -> CalibracionTableroResponse:
    """Esquinas del tablero calibradas a mano (píxeles de la foto), o `calibrada=false` si se usa la detección automática."""
    return _estado_calibracion()


@router.put("/calibracion", response_model=CalibracionTableroResponse)
def guardar_calibracion(
    cuerpo: CalibracionTableroRequest, _facilitador_id: int = Depends(get_current_facilitador)
) -> CalibracionTableroResponse:
    """Guarda las 4 esquinas marcadas por el facilitador."""
    puntos = _validar_esquinas(cuerpo.esquinas)
    tablero.guardar_esquinas_calibradas(puntos)
    return _estado_calibracion()


@router.delete("/calibracion", response_model=CalibracionTableroResponse)
def borrar_calibracion(_facilitador_id: int = Depends(get_current_facilitador)) -> CalibracionTableroResponse:
    """Borra la calibración manual y vuelve a la detección automática."""
    tablero.ARCHIVO_ESQUINAS.unlink(missing_ok=True)
    return _estado_calibracion()


@router.post("/dataset/foto", response_model=CapturaDatasetResponse)
def capturar_foto_dataset(
    cuerpo: CapturaDatasetRequest, _facilitador_id: int = Depends(get_current_facilitador)
) -> CapturaDatasetResponse:
    """Saca una foto de la cámara fija y guarda las 64 casillas etiquetadas con el FEN de piezas dado."""
    try:
        resultado = dataset_propio.capturar_foto_etiquetada(cuerpo.fen_piezas, cuerpo.solo_piezas)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return CapturaDatasetResponse(**resultado)


@router.post("/dataset/pieza", response_model=FotosPiezaResponse)
async def subir_fotos_pieza(
    clase: str = Form(...),
    fotos: list[UploadFile] = File(...),
    _facilitador_id: int = Depends(get_current_facilitador),
) -> FotosPiezaResponse:
    """Sube fotos de una pieza (o casilla vacía) de una clase; se guardan tal cual, sin enderezar ni recortar."""
    if clase not in CLASES:
        raise HTTPException(status_code=422, detail=f"Clase inválida: {clase!r}")
    if not 1 <= len(fotos) <= MAXIMO_FOTOS_PIEZA:
        raise HTTPException(status_code=422, detail=f"Se aceptan de 1 a {MAXIMO_FOTOS_PIEZA} fotos por pedido")
    imagenes = []
    for foto_subida in fotos:
        try:
            imagenes.append(await _leer_foto_subida(foto_subida))
        except HTTPException as error:
            if error.status_code == 422:
                raise HTTPException(
                    status_code=422, detail=f"No se pudo leer la imagen: {foto_subida.filename}"
                ) from error
            raise
    return FotosPiezaResponse(**dataset_propio.guardar_fotos_pieza(clase, imagenes))


@router.post("/dataset/foto-tablero", response_model=CapturaDatasetResponse)
async def subir_foto_tablero_dataset(
    fen_piezas: str = Form(...),
    solo_piezas: bool = Form(False),
    foto: UploadFile = File(...),
    _facilitador_id: int = Depends(get_current_facilitador),
) -> CapturaDatasetResponse:
    """Como /dataset/foto pero con una foto del tablero subida a mano en vez de la cámara fija."""
    imagen = await _leer_foto_subida(foto)
    try:
        resultado = dataset_propio.guardar_foto_tablero_subida(fen_piezas, imagen, solo_piezas)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return CapturaDatasetResponse(**resultado)


@router.get("/dataset/control")
def imagen_control_dataset(_facilitador_id: int = Depends(get_current_facilitador)) -> Response:
    """Última imagen de control (tablero enderezado con la grilla) como JPEG."""
    ruta = dataset_propio.ruta_imagen_control()
    if ruta is None:
        raise HTTPException(status_code=404, detail="Todavía no hay imagen de control")
    return Response(content=ruta.read_bytes(), media_type="image/jpeg")


@router.get("/dataset/resumen", response_model=ResumenDatasetResponse)
def resumen_dataset(_facilitador_id: int = Depends(get_current_facilitador)) -> ResumenDatasetResponse:
    """Muestras por clase del dataset propio."""
    return ResumenDatasetResponse(**dataset_propio.resumen())


FRONTERA_FLUJO = "cuadro"
CALIDAD_FLUJO_JPEG = 80


def _partes_del_flujo(modo: str, casillas: list[str]):
    """Genera las partes multipart del flujo en vivo: cada una lleva un JPEG y, en modo `piezas`, las predicciones en `X-Casillas`."""
    import json

    for frame in flujo_de_frames():
        cabecera_extra = ""
        try:
            if modo == "piezas":
                vista, predicciones = verificacion.analizar_tablero(frame)
                cabecera_extra = "X-Casillas: " + json.dumps([[c["casilla"], c["clase"], c["confianza"]] for c in predicciones], separators=(",", ":")) + "\r\n"
                exito, buffer = cv2.imencode(".jpg", vista, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_FLUJO_JPEG])
            elif modo == "vista":
                exito, buffer = True, np.frombuffer(dataset_propio.vista_previa(casillas, frame), dtype=np.uint8)
            else:
                exito, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_FLUJO_JPEG])
        except (ValueError, FileNotFoundError) as error:
            exito, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_FLUJO_JPEG])
            cabecera_extra = "X-Aviso: " + str(error).replace("\n", " ")[:200].encode("ascii", "replace").decode() + "\r\n"
        if not exito:
            continue
        datos = buffer.tobytes()
        yield (
            f"--{FRONTERA_FLUJO}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(datos)}\r\n{cabecera_extra}\r\n".encode() + datos + b"\r\n"
        )


@router.get("/flujo")
def flujo_en_vivo(
    modo: str = "camara", casillas: str = "", _usuario_id: int = Depends(get_current_user)
) -> StreamingResponse:
    """Video en vivo de la cámara fija (multipart/x-mixed-replace de JPEG, a la velocidad de la cámara).

    `modo=camara`: imagen tal cual. `modo=piezas`: tablero enderezado con las piezas reconocidas (predicciones en el header
    `X-Casillas` de cada parte). `modo=vista`: lo que se guardaría en el dataset para `casillas` (ej. `e4,f4`).
    """
    if modo not in {"camara", "piezas", "vista"}:
        raise HTTPException(status_code=422, detail="modo inválido")
    elegidas = [c for c in casillas.split(",") if c]
    try:
        generador = _partes_del_flujo(modo, elegidas)
        primera = next(generador)  # abre la cámara aquí para devolver 503 como error normal si no se puede
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except StopIteration as error:
        raise HTTPException(status_code=503, detail="La cámara no entrega imágenes") from error

    def con_primera():
        yield primera
        yield from generador

    return StreamingResponse(
        con_primera(),
        media_type=f"multipart/x-mixed-replace; boundary={FRONTERA_FLUJO}",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/probar-piezas")
def probar_piezas(_facilitador_id: int = Depends(get_current_facilitador)) -> dict:
    """Saca una foto y devuelve qué pieza reconoce el modelo en cada casilla, con su confianza y una imagen anotada (no guarda nada)."""
    try:
        return verificacion.probar_tablero()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=409, detail="Todavía no hay un modelo de piezas entrenado") from error


@router.get("/dataset/vista-previa")
def vista_previa_dataset(casillas: str = "", _facilitador_id: int = Depends(get_current_facilitador)) -> Response:
    """Lo que se guardaría ahora (tablero con las casillas elegidas en verde + su recorte exacto), sin guardar nada."""
    try:
        contenido = dataset_propio.vista_previa([c for c in casillas.split(",") if c])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return Response(content=contenido, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.delete("/dataset/clase/{clase}", response_model=BorrarCapturaResponse)
def borrar_clase_dataset(clase: str, _facilitador_id: int = Depends(get_current_facilitador)) -> BorrarCapturaResponse:
    """Borra todas las fotos de una clase para volver a empezar con ella."""
    try:
        return BorrarCapturaResponse(borradas=dataset_propio.borrar_clase(clase))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/dataset/export")
def exportar_dataset(_facilitador_id: int = Depends(get_current_facilitador)) -> FileResponse:
    """ZIP del dataset propio (una carpeta por clase) para entrenar en Colab."""
    try:
        ruta = dataset_propio.exportar_zip()
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return FileResponse(
        ruta,
        media_type="application/zip",
        filename="dataset_piezas.zip",
        background=BackgroundTask(ruta.unlink, missing_ok=True),
    )


@router.delete("/dataset/captura/{captura_id}", response_model=BorrarCapturaResponse)
def borrar_captura_dataset(
    captura_id: str, _facilitador_id: int = Depends(get_current_facilitador)
) -> BorrarCapturaResponse:
    """Deshace una captura borrando sus PNG."""
    try:
        return BorrarCapturaResponse(borradas=dataset_propio.borrar_captura(captura_id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/dataset/reentrenar", response_model=ReentrenarResponse)
def reentrenar_clasificador(_facilitador_id: int = Depends(get_current_facilitador)) -> ReentrenarResponse:
    """Lanza el reentrenamiento del clasificador en segundo plano."""
    try:
        dataset_propio.iniciar_reentrenamiento()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ReentrenarResponse(estado="en_curso")


@router.get("/dataset/reentrenar/estado", response_model=EstadoReentrenamientoResponse)
def estado_reentrenamiento(_facilitador_id: int = Depends(get_current_facilitador)) -> EstadoReentrenamientoResponse:
    """Estado del reentrenamiento y las últimas líneas de su salida."""
    return EstadoReentrenamientoResponse(**dataset_propio.estado_reentrenamiento())
