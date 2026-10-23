"""Panel de configuración del facilitador: videos educativos por pieza."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from backend.esquemas.facilitador_esquema import VideoSubidoResponse
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.facilitador.servicio_videos import (
    borrar_video_pieza,
    guardar_video_pieza,
    listar_videos_piezas,
)

router = APIRouter(prefix="/facilitador", tags=["facilitador"])


@router.post(
    "/videos/{tipo_pieza}",
    response_model=VideoSubidoResponse,
    summary="Subir el video educativo de una pieza",
)
async def subir_video_pieza(
    tipo_pieza: str,
    archivo: UploadFile = File(...),
    usuario_id: int = Depends(get_current_facilitador),
) -> VideoSubidoResponse:
    """Sube (o reemplaza) el video del facilitador autenticado para `tipo_pieza`.

    `tipo_pieza` debe ser uno de: rey, dama, torre, alfil, caballo, peon.
    Solo acepta `.mp4`, `.webm` o `.mov`. El nuevo video reemplaza al
    anterior del mismo facilitador para esa pieza, si había uno.
    """
    contenido = await archivo.read()
    try:
        url = guardar_video_pieza(usuario_id, tipo_pieza, archivo.filename or "", contenido)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return VideoSubidoResponse(tipo_pieza=tipo_pieza, url=url)


@router.delete(
    "/videos/{tipo_pieza}",
    status_code=204,
    summary="Quitar el video propio de una pieza (los jugadores vuelven a ver el general)",
)
def quitar_video_pieza(tipo_pieza: str, usuario_id: int = Depends(get_current_facilitador)) -> Response:
    """Borra el video que el facilitador subió para `tipo_pieza`. Sus jugadores pasan a ver el video general (el
    del facilitador principal). 404 si no tenía ninguno, 400 si la pieza no es válida."""
    try:
        borrado = borrar_video_pieza(usuario_id, tipo_pieza)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not borrado:
        raise HTTPException(status_code=404, detail="No tenés un video propio para esa pieza")
    return Response(status_code=204)


@router.get(
    "/videos",
    response_model=dict[str, str],
    summary="Videos educativos subidos por el facilitador autenticado",
)
def videos_del_facilitador(usuario_id: int = Depends(get_current_facilitador)) -> dict[str, str]:
    """Mapa `tipo_pieza -> url` de los videos que el facilitador ya subió.

    Las piezas sin video propio no aparecen en el resultado: significa que
    los jugadores de este facilitador ven el video general de esa pieza (el
    del facilitador principal), no que hubo un error. Cada URL lleva `?v=`
    para que un video reemplazado no quede en la caché del navegador.
    """
    return listar_videos_piezas(usuario_id, con_version=True)
