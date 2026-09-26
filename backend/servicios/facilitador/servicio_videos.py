"""Videos educativos por pieza que sube el facilitador (panel de configuración).

Los archivos se guardan en disco bajo `backend/media/videos_piezas/`, con
nombre `{usuario_id_facilitador}_{tipo_pieza}{extension}` — así cada
facilitador tiene los suyos propios sin pisarse entre sí, y el nombre de
archivo mismo sirve de índice: no hace falta ninguna tabla ni repositorio
nuevo para saber qué tiene subido cada uno. La carpeta está en `.gitignore`
porque es contenido subido por el usuario, no código (ver `backend/main.py`
para el mount estático que la sirve por URL).
"""
from __future__ import annotations

from pathlib import Path

MEDIA_VIDEOS_DIR = Path(__file__).resolve().parent.parent.parent / "media" / "videos_piezas"

URL_BASE_VIDEOS_PIEZAS = "/media/videos_piezas"

TIPOS_PIEZA_VALIDOS: tuple[str, ...] = ("rey", "dama", "torre", "alfil", "caballo", "peon")

EXTENSIONES_VIDEO_VALIDAS: tuple[str, ...] = (".mp4", ".webm", ".mov")

TAMANO_MAXIMO_BYTES = 50 * 1024 * 1024


def _validar_tipo_pieza(tipo_pieza: str) -> None:
    if tipo_pieza not in TIPOS_PIEZA_VALIDOS:
        raise ValueError(
            f"Tipo de pieza inválido: '{tipo_pieza}'. Usá uno de: {', '.join(TIPOS_PIEZA_VALIDOS)}"
        )


def _extension_valida(nombre_archivo_original: str) -> str:
    extension = Path(nombre_archivo_original).suffix.lower()
    if extension not in EXTENSIONES_VIDEO_VALIDAS:
        raise ValueError(
            f"Formato de video no soportado: '{extension or 'sin extensión'}'. "
            f"Usá uno de: {', '.join(EXTENSIONES_VIDEO_VALIDAS)}"
        )
    return extension


def guardar_video_pieza(
    usuario_id: int,
    tipo_pieza: str,
    nombre_archivo_original: str,
    contenido: bytes,
) -> str:
    """Guarda el video de `tipo_pieza` subido por el facilitador `usuario_id`.

    Reemplaza cualquier video anterior del mismo facilitador para esa pieza,
    incluso si tenía otra extensión. Devuelve la URL pública del archivo
    guardado (servida por el mount estático de `backend/main.py`).
    """
    _validar_tipo_pieza(tipo_pieza)
    extension = _extension_valida(nombre_archivo_original)
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ValueError(
            f"El video supera el tamaño máximo permitido ({TAMANO_MAXIMO_BYTES // (1024 * 1024)}MB)"
        )

    MEDIA_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    for archivo_previo in MEDIA_VIDEOS_DIR.glob(f"{usuario_id}_{tipo_pieza}.*"):
        archivo_previo.unlink()

    nombre_archivo = f"{usuario_id}_{tipo_pieza}{extension}"
    (MEDIA_VIDEOS_DIR / nombre_archivo).write_bytes(contenido)
    return f"{URL_BASE_VIDEOS_PIEZAS}/{nombre_archivo}"


def listar_videos_piezas(usuario_id: int) -> dict[str, str]:
    """Videos que `usuario_id` (facilitador) tiene subidos actualmente, por pieza.

    Las piezas sin video subido no aparecen en el dict devuelto — el
    frontend interpreta la ausencia como "usar el video por defecto del
    sistema", no como un error.
    """
    videos: dict[str, str] = {}
    if not MEDIA_VIDEOS_DIR.is_dir():
        return videos
    for tipo_pieza in TIPOS_PIEZA_VALIDOS:
        coincidencias = sorted(MEDIA_VIDEOS_DIR.glob(f"{usuario_id}_{tipo_pieza}.*"))
        if coincidencias:
            videos[tipo_pieza] = f"{URL_BASE_VIDEOS_PIEZAS}/{coincidencias[0].name}"
    return videos
