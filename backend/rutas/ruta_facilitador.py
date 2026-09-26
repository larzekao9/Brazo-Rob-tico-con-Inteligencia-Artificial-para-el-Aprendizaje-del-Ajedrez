"""Panel de configuración del facilitador: videos educativos por pieza."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.esquemas.facilitador_esquema import VideoSubidoResponse
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.facilitador.servicio_videos import (
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


@router.get(
    "/videos",
    response_model=dict[str, str],
    summary="Videos educativos subidos por el facilitador autenticado",
)
def videos_del_facilitador(usuario_id: int = Depends(get_current_facilitador)) -> dict[str, str]:
    """Mapa `tipo_pieza -> url` de los videos que el facilitador ya subió.

    Las piezas sin video propio no aparecen en el resultado: el frontend
    debe interpretar su ausencia como "usar el video por defecto del
    sistema", no como un error.
    """
    return listar_videos_piezas(usuario_id)
