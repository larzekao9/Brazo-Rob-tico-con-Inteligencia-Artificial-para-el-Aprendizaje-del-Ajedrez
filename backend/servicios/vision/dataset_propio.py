"""Servicio del dataset propio de casillas etiquetadas y del reentrenamiento del clasificador de piezas.

Decisión de diseño: la captura reutiliza `training.capturar_dataset_propio` (importado de forma perezosa, para no cargar
`training` al arrancar el backend) en vez de duplicar la lógica; el reentrenamiento corre como subproceso
(`python -m training.reentrenar_con_dataset_propio`) para no bloquear el servidor ni cargar torch de entrenamiento
dentro del proceso web. El estado del subproceso vive en memoria del proceso (no persiste entre reinicios).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

import cv2

from backend.servicios.vision import piezas

MINIMO_RECOMENDADO = 1500
MINIMO_PARA_REENTRENAR = 300
LINEAS_DE_LOG = 40
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
_PATRON_CAPTURA_ID = re.compile(r"^\d+$")


def _carpeta() -> Path:
    from training import capturar_dataset_propio

    return Path(capturar_dataset_propio.CARPETA_DATASET)


def capturar_foto_etiquetada(fen_piezas: str, solo_piezas: bool = False) -> dict[str, int | str]:
    """Saca una foto de la cámara fija y guarda las 64 casillas etiquetadas según `fen_piezas`.

    Con `solo_piezas` guarda únicamente las casillas ocupadas (ninguna "vacia").

    Raises:
        ValueError: FEN de piezas inválido, `solo_piezas` sin ninguna pieza en el FEN o tablero no detectado.
        RuntimeError: la cámara no está disponible.
    """
    from training.capturar_dataset_propio import capturar_muestras_con_id

    captura_id, guardadas = capturar_muestras_con_id(fen_piezas, solo_piezas=solo_piezas)
    return {"captura_id": captura_id, "guardadas": guardadas, "total": resumen()["total"]}


def guardar_foto_tablero_subida(fen_piezas: str, imagen, solo_piezas: bool = False) -> dict[str, int | str]:
    """Guarda las 64 casillas etiquetadas de una foto del tablero subida a mano (misma lógica que la cámara).

    Raises:
        ValueError: FEN de piezas inválido o tablero no detectado.
    """
    from training.capturar_dataset_propio import capturar_muestras_con_id

    captura_id, guardadas = capturar_muestras_con_id(fen_piezas, imagen=imagen, solo_piezas=solo_piezas)
    return {"captura_id": captura_id, "guardadas": guardadas, "total": resumen()["total"]}


def guardar_fotos_pieza(clase: str, imagenes: list) -> dict[str, int]:
    """Guarda tal cual (PNG) fotos de una pieza o casilla vacía en `<dataset>/<clase>/sub_<ms>_<i>.png`.

    Raises:
        ValueError: `clase` no es una de las 13 clases del clasificador, o una imagen no se pudo escribir.
    """
    from backend.servicios.vision.modelo_piezas import CLASES

    if clase not in CLASES:
        raise ValueError(f"Clase inválida: {clase!r}")
    carpeta_clase = _carpeta() / clase
    carpeta_clase.mkdir(parents=True, exist_ok=True)
    marca_tiempo = time.time_ns() // 1_000_000
    guardadas = 0
    for indice, imagen in enumerate(imagenes):
        if cv2.imwrite(str(carpeta_clase / f"sub_{marca_tiempo}_{indice}.png"), imagen):
            guardadas += 1
    return {"guardadas": guardadas, "total_clase": len(list(carpeta_clase.glob("*.png")))}


def ruta_imagen_control() -> Path | None:
    """Ruta de la última imagen de control con grilla, o `None` si todavía no hay."""
    ruta = _carpeta() / "_ultima_captura.jpg"
    return ruta if ruta.is_file() else None


def resumen() -> dict:
    """Muestras por clase, total, cantidad de capturas distintas y mínimo recomendado."""
    carpeta = _carpeta()
    por_clase: dict[str, int] = {}
    ids: set[str] = set()
    if carpeta.exists():
        for sub in sorted(carpeta.iterdir()):
            if not sub.is_dir():
                continue
            archivos = list(sub.glob("*.png"))
            por_clase[sub.name] = len(archivos)
            ids.update(
                    id_captura for archivo in archivos if (id_captura := archivo.name.split("_", 1)[0]).isdigit()
                )
    return {
        "por_clase": por_clase,
        "total": sum(por_clase.values()),
        "capturas": len(ids),
        "minimo_recomendado": MINIMO_RECOMENDADO,
    }


def borrar_captura(captura_id: str) -> int:
    """Borra los PNG de una captura y devuelve cuántos borró.

    Raises:
        ValueError: si `captura_id` no son solo dígitos (evita path traversal).
    """
    if not _PATRON_CAPTURA_ID.fullmatch(captura_id):
        raise ValueError("captura_id debe contener solo dígitos")
    borradas = 0
    carpeta = _carpeta()
    if not carpeta.exists():
        return 0
    for archivo in carpeta.glob(f"*/{captura_id}_*.png"):
        archivo.unlink()
        borradas += 1
    return borradas


class _Reentrenamiento:
    def __init__(self) -> None:
        self.estado = "inactivo"
        self.lineas: deque[str] = deque(maxlen=LINEAS_DE_LOG)
        self.cerrojo = threading.Lock()


_reentrenamiento = _Reentrenamiento()


def _vigilar(proceso: subprocess.Popen) -> None:
    for linea in proceso.stdout:
        _reentrenamiento.lineas.append(linea.rstrip())
    codigo = proceso.wait()
    with _reentrenamiento.cerrojo:
        if codigo == 0:
            piezas.invalidar_modelo()
            _reentrenamiento.estado = "terminado"
        else:
            _reentrenamiento.lineas.append(f"El proceso terminó con código {codigo}")
            _reentrenamiento.estado = "error"


def iniciar_reentrenamiento() -> None:
    """Lanza el reentrenamiento como subproceso en segundo plano.

    Raises:
        RuntimeError: si ya hay uno corriendo.
        ValueError: si hay menos de `MINIMO_PARA_REENTRENAR` muestras.
    """
    with _reentrenamiento.cerrojo:
        if _reentrenamiento.estado == "en_curso":
            raise RuntimeError("Ya hay un reentrenamiento en curso")
        total = resumen()["total"]
        if total < MINIMO_PARA_REENTRENAR:
            raise ValueError(f"Hacen falta al menos {MINIMO_PARA_REENTRENAR} muestras, hay {total}")
        entorno = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "PYTHONUNBUFFERED": "1"}
        proceso = subprocess.Popen(
            [sys.executable, "-m", "training.reentrenar_con_dataset_propio"],
            cwd=RAIZ_REPOSITORIO,
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _reentrenamiento.lineas.clear()
        _reentrenamiento.estado = "en_curso"
    threading.Thread(target=_vigilar, args=(proceso,), daemon=True).start()


def estado_reentrenamiento() -> dict[str, str]:
    """Estado del reentrenamiento y las últimas líneas de su salida."""
    return {"estado": _reentrenamiento.estado, "log": "\n".join(_reentrenamiento.lineas)}
