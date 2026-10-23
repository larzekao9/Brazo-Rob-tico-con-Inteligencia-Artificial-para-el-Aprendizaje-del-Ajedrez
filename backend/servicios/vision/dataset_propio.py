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
import tempfile
import time
import zipfile
from collections import deque
from pathlib import Path

import cv2

from backend.servicios.vision import piezas

MINIMO_RECOMENDADO = 1500
MINIMO_PARA_REENTRENAR = 300
PREFIJO_CORRECCION = "corr"
"""Prefijo del id de las muestras que salen de corregir una casilla en el probador: el entrenamiento del candidato las busca por él."""
LINEAS_DE_LOG = 40
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
_PATRON_CAPTURA_ID = re.compile(r"^\d+$")


def _carpeta() -> Path:
    from training import capturar_dataset_propio

    return Path(capturar_dataset_propio.CARPETA_DATASET)


def camaras_para_capturar() -> list[str]:
    """Las cámaras de las que se captura a la vez: la principal y, si está configurada y calibrada, la secundaria."""
    from backend.servicios.vision import tablero
    from backend.servicios.vision.camara import camaras_configuradas

    return [c for c in camaras_configuradas() if c == "principal" or tablero.archivo_esquinas(c).exists()]


def capturar_foto_etiquetada(fen_piezas: str, solo_piezas: bool = False, camaras: list[str] | None = None) -> dict:
    """Saca una foto de cada cámara y guarda las casillas etiquetadas según `fen_piezas`.

    Con `solo_piezas` guarda únicamente las casillas ocupadas (ninguna "vacia"). Las fotos de todas las cámaras se toman juntas y
    comparten `grupo`, así al validar el entrenamiento no se mezcla una vista en entrenamiento y otra en validación.

    Returns:
        `{captura_id, capturas, guardadas, total, camaras, avisos}`: `captura_id` es la de la cámara principal y `capturas` todas.
        Si una cámara secundaria falla se sigue con las demás y se informa en `avisos`; si falla la principal, se lanza el error.

    Raises:
        ValueError: FEN de piezas inválido, `solo_piezas` sin ninguna pieza en el FEN o tablero no detectado.
        RuntimeError: la cámara principal no está disponible.
    """
    from backend.servicios.vision.camara import capturar_foto_tablero
    from training.capturar_dataset_propio import capturar_muestras_con_id

    elegidas = camaras or camaras_para_capturar()
    fotos: dict[str, object] = {}
    avisos: list[str] = []
    for camara in elegidas:  # primero todas las fotos (casi al mismo tiempo), después se recortan
        try:
            fotos[camara] = capturar_foto_tablero(camara=camara)
        except RuntimeError as error:
            if camara == "principal":
                raise
            avisos.append(f"Cámara {camara}: {error}")
    capturas: list[str] = []
    guardadas = 0
    grupo: str | None = None
    usadas: list[str] = []
    for camara, imagen in fotos.items():
        try:
            captura_id, cantidad = capturar_muestras_con_id(fen_piezas, imagen=imagen, solo_piezas=solo_piezas, camara=camara, grupo=grupo)
        except ValueError as error:
            if camara == "principal":
                raise
            avisos.append(f"Cámara {camara}: {error}")
            continue
        grupo = grupo or captura_id
        capturas.append(captura_id)
        usadas.append(camara)
        guardadas += cantidad
        if not solo_piezas and fen_sin_piezas(fen_piezas):
            _actualizar_referencia_vacia(camara, imagen)
    return {"captura_id": capturas[0], "capturas": capturas, "guardadas": guardadas, "total": resumen()["total"], "camaras": usadas, "avisos": avisos}


def fen_sin_piezas(fen_piezas: str) -> bool:
    """Si el FEN de piezas describe el tablero vacío (`8/8/8/8/8/8/8/8`)."""
    return all(caracter in "8/" for caracter in fen_piezas.strip())


def _actualizar_referencia_vacia(camara: str, imagen) -> None:
    """Con una foto del tablero vacío, renueva la referencia de `camara` con la que se detecta en qué casilla está una pieza
    (`referencia_vacia`). Sin esquinas calibradas no hace nada."""
    from backend.servicios.vision import referencia_vacia, tablero

    esquinas = tablero.cargar_esquinas_calibradas(tablero.archivo_esquinas(camara))
    if esquinas is not None:
        referencia_vacia.guardar_referencia(camara, [(imagen, esquinas)])


def guardar_foto_tablero_subida(fen_piezas: str, imagen, solo_piezas: bool = False) -> dict[str, int | str]:
    """Guarda las 64 casillas etiquetadas de una foto del tablero subida a mano (misma lógica que la cámara).

    Raises:
        ValueError: FEN de piezas inválido o tablero no detectado.
    """
    from training.capturar_dataset_propio import capturar_muestras_con_id

    captura_id, guardadas = capturar_muestras_con_id(fen_piezas, imagen=imagen, solo_piezas=solo_piezas)
    return {"captura_id": captura_id, "guardadas": guardadas, "total": resumen()["total"]}


def guardar_casilla_corregida(casilla: str, clase: str, camaras: list[str] | None = None) -> dict:
    """Guarda como muestra de `clase` el recorte de UNA casilla, tomado ahora de cada cámara (corrección de un error del reconocimiento).

    Es lo mismo que una captura etiquetada pero con una sola casilla: el recorte justo, el ampliado y el de volumen 3D, para que el
    próximo reentrenamiento aprenda de lo que el modelo leyó mal. Las fotos de las cámaras comparten `grupo` como en `capturar_foto_etiquetada`.

    Returns:
        `{guardadas, camaras, avisos, total_clase}`; si una cámara secundaria falla se sigue con las demás y se informa en `avisos`.

    Raises:
        ValueError: `casilla` o `clase` inválidas, o el tablero no se detectó en ninguna cámara.
        RuntimeError: la cámara principal no está disponible.
    """
    from backend.servicios.vision.camara import capturar_foto_tablero
    from backend.servicios.vision.modelo_piezas import CLASES
    from training.capturar_dataset_propio import _CASILLAS, _guardar_recortes
    from backend.servicios.vision.reconocimiento import esquinas_y_margen
    from backend.servicios.vision.tablero import dividir_en_casillas, enderezar_tablero

    if casilla not in _CASILLAS:
        raise ValueError(f"Casilla inválida: {casilla!r}")
    if clase not in CLASES:
        raise ValueError(f"Clase inválida: {clase!r}")
    marca = f"{PREFIJO_CORRECCION}{time.time_ns() // 1_000_000}"
    guardadas, usadas, avisos = 0, [], []
    for camara in camaras or camaras_para_capturar():
        try:
            imagen = capturar_foto_tablero(camara=camara)
            esquinas, margen = esquinas_y_margen(imagen, camara)
            recortes = dividir_en_casillas(enderezar_tablero(imagen, esquinas), margen)
        except (RuntimeError, ValueError) as error:
            if camara == "principal":
                raise
            avisos.append(f"Cámara {camara}: {error}")
            continue
        guardadas += _guardar_recortes(f"{marca}_{camara}", imagen, esquinas, {casilla: clase}, camara, recortes, ampliar=not margen)
        usadas.append(camara)
    total_clase = len(list((_carpeta() / clase).glob("*.png")))
    return {"guardadas": guardadas, "camaras": usadas, "avisos": avisos, "total_clase": total_clase}


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
    from training import capturar_dataset_propio

    for sufijo in ("jpg", "json"):
        (capturar_dataset_propio.carpeta_cuadros() / f"{captura_id}.{sufijo}").unlink(missing_ok=True)
    for carpeta_extra in (capturar_dataset_propio.carpeta_ampliados(), capturar_dataset_propio.carpeta_volumen()):
        for archivo in carpeta_extra.glob(f"*/{captura_id}_*.png"):
            archivo.unlink(missing_ok=True)
    return borradas


def vista_previa_imagen(casillas: list[str], imagen=None, camara: str = "principal"):
    """JPEG de lo que se guardaría ahora: el tablero con el marco y las `casillas` en verde, y debajo el recorte exacto de cada una.

    Saca una foto de la cámara fija (no guarda nada). Con esquinas calibradas el tablero lleva marco y letras.

    Raises:
        ValueError: nombre de casilla inválido o tablero no detectado.
        RuntimeError: la cámara no está disponible.
    """
    import numpy as np

    from backend.servicios.vision.camara import capturar_foto_tablero
    from backend.servicios.vision.reconocimiento import esquinas_y_margen
    from backend.servicios.vision.tablero import (
        dibujar_grilla_debug,
        dividir_en_casillas,
        enderezar_tablero,
        imagen_control_ampliada,
        recortes_ampliados,
    )

    validas = {f"{c}{f}" for c in "abcdefgh" for f in "12345678"}
    elegidas = [c for c in casillas if c in validas][:8]
    if len(elegidas) != len(casillas):
        raise ValueError("Casilla inválida")
    if imagen is None:
        imagen = capturar_foto_tablero(camara=camara)
    esquinas, margen = esquinas_y_margen(imagen, camara)
    plano = enderezar_tablero(imagen, esquinas)
    tablero_vista = imagen_control_ampliada(imagen, esquinas, resaltar=tuple(elegidas)) if not margen else dibujar_grilla_debug(plano)
    if elegidas:
        recortes = dividir_en_casillas(plano, margen)
        ampliados = recortes_ampliados(imagen, esquinas) if not margen else {}
        lado = 120
        fila = np.full((lado + 24, tablero_vista.shape[1], 3), 30, dtype=np.uint8)
        x = 8
        for nombre in elegidas:
            for recorte, etiqueta in ((recortes[nombre], nombre), (ampliados.get(nombre), f"{nombre} ampliado")):
                if recorte is None or x + lado > fila.shape[1]:
                    continue
                fila[24 : 24 + lado, x : x + lado] = cv2.resize(recorte, (lado, lado))
                cv2.putText(fila, etiqueta, (x, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                x += lado + 8
        tablero_vista = np.vstack([tablero_vista, fila])
    return tablero_vista


def vista_previa(casillas: list[str], imagen=None, camara: str = "principal") -> bytes:
    """`vista_previa_imagen` codificada como JPEG."""
    exito, buffer = cv2.imencode(".jpg", vista_previa_imagen(casillas, imagen, camara))
    if not exito:
        raise RuntimeError("No se pudo codificar la vista previa")
    return buffer.tobytes()


def borrar_clase(clase: str) -> int:
    """Borra todas las fotos de una clase (ej. "black-pawn") y devuelve cuántas borró.

    Raises:
        ValueError: si `clase` no es una de las 13 clases del clasificador.
    """
    from backend.servicios.vision.modelo_piezas import CLASES

    if clase not in CLASES:
        raise ValueError(f"Clase inválida: {clase!r}")
    carpeta = _carpeta() / clase
    borradas = 0
    if carpeta.is_dir():
        for archivo in carpeta.glob("*.png"):
            archivo.unlink()
            borradas += 1
    from training import capturar_dataset_propio

    for carpeta_extra in (capturar_dataset_propio.carpeta_ampliados(), capturar_dataset_propio.carpeta_volumen()):
        for archivo in (carpeta_extra / clase).glob("*.png"):
            archivo.unlink(missing_ok=True)
    return borradas


def regenerar_ampliados() -> dict[str, int]:
    """Vuelve a escribir todos los recortes ampliados a partir de los cuadros completos y borra los que ya no tienen su recorte justo.

    Sirve para las capturas hechas antes de que se guardaran (que sí tienen su cuadro) o cuando cambia la geometría del recorte.

    Returns:
        `{escritos, borrados, sin_cuadro}`: `sin_cuadro` son recortes justos de capturas viejas, de las que no hay foto completa y no
        se pueden ampliar.
    """
    import json

    import numpy as np

    from backend.servicios.vision.tablero import recortes_ampliados
    from training import capturar_dataset_propio

    from backend.servicios.vision import geometria3d

    raiz = capturar_dataset_propio.carpeta_ampliados()
    raiz_volumen = capturar_dataset_propio.carpeta_volumen()
    escritos = 0
    esperados: set[Path] = set()
    esperados_volumen: set[Path] = set()
    cuadros = capturar_dataset_propio.carpeta_cuadros()
    for manifiesto in sorted(cuadros.glob("*.json")) if cuadros.is_dir() else []:
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is None:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        esquinas = np.array(datos["esquinas"], dtype=np.float32)
        recortes = recortes_ampliados(cuadro, esquinas)
        try:
            alto, ancho = cuadro.shape[:2]
            volumen = geometria3d.recortes_volumen(cuadro, esquinas[::-1], geometria3d.cargar_lente(datos.get("camara", "principal"), ancho, alto))
        except ValueError:
            volumen = {}
        for casilla, clase in datos["etiquetas"].items():
            if not (_carpeta() / clase / f"{manifiesto.stem}_{casilla}.png").exists():
                continue
            destino = raiz / clase / f"{manifiesto.stem}_{casilla}.png"
            destino.parent.mkdir(parents=True, exist_ok=True)
            if cv2.imwrite(str(destino), recortes[casilla]):
                escritos += 1
                esperados.add(destino)
            if casilla in volumen:
                destino_volumen = raiz_volumen / clase / f"{manifiesto.stem}_{casilla}.png"
                destino_volumen.parent.mkdir(parents=True, exist_ok=True)
                if cv2.imwrite(str(destino_volumen), volumen[casilla]):
                    esperados_volumen.add(destino_volumen)
    borrados = 0
    for carpeta, vigentes in ((raiz, esperados), (raiz_volumen, esperados_volumen)):
        for archivo in carpeta.glob("*/*.png") if carpeta.is_dir() else []:
            if archivo not in vigentes:
                archivo.unlink()
                borrados += 1
    con_cuadro = {a.name for a in esperados}
    sin_cuadro = sum(1 for a in _carpeta().glob("*/*.png") if a.name not in con_cuadro) if _carpeta().is_dir() else 0
    return {"escritos": escritos, "volumen": len(esperados_volumen), "borrados": borrados, "sin_cuadro": sin_cuadro}


def _recortes_del_dataset():
    """`(clase/archivo.png, recorte ampliado, recorte de volumen o None, manifiesto)` de cada casilla guardada que tiene su cuadro completo.

    Los recortes se vuelven a calcular desde la foto completa con la geometría de HOY (esquinas de la captura, lente actual de la cámara): son
    los mismos que va a ver el backend al reconocer, que es lo que importa para entrenar.
    """
    import json

    import numpy as np

    from backend.servicios.vision import geometria3d
    from backend.servicios.vision.tablero import recortes_ampliados
    from training import capturar_dataset_propio

    carpeta_cuadros = capturar_dataset_propio.carpeta_cuadros()
    if not carpeta_cuadros.is_dir():
        return
    for manifiesto in sorted(carpeta_cuadros.glob("*.json")):
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is None:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        esquinas = np.array(datos["esquinas"], dtype=np.float32)
        ampliados = recortes_ampliados(cuadro, esquinas)
        try:
            alto, ancho = cuadro.shape[:2]
            volumen = geometria3d.recortes_volumen(cuadro, esquinas[::-1], geometria3d.cargar_lente(datos.get("camara", "principal"), ancho, alto))
        except ValueError:
            volumen = {}
        for casilla, clase in datos["etiquetas"].items():
            if (_carpeta() / clase / f"{manifiesto.stem}_{casilla}.png").exists():  # sigue en el dataset (no se borró)
                yield f"{clase}/{manifiesto.stem}_{casilla}.png", ampliados[casilla], volumen.get(casilla), {**datos, "id": manifiesto.stem}


COLUMNAS_METADATOS = ("archivo", "recorte", "clase", "captura", "casilla", "camara", "grupo")
"""Columnas de `metadatos.csv` en el ZIP: una fila por recorte. `recorte` es justo, ampliado o volumen; `camara` y `grupo` quedan vacíos en las
fotos viejas (sin foto completa) y en las subidas a mano; las capturas con foto completa de antes de las dos cámaras son de la principal. Las
fotos de un mismo `grupo` son del mismo instante (una por cámara)."""


def exportar_zip() -> Path:
    """Empaqueta el dataset en un ZIP listo para subir a Colab y entrenar (ver `training/colab_vision_piezas.ipynb`).

    Contenido: `<clase>/<archivo>.png` (recorte justo, como siempre), `ampliado/<clase>/…` y `volumen/<clase>/…` (de las capturas con foto
    completa), `metadatos.csv` (ver `COLUMNAS_METADATOS`) y `clases.json`. Devuelve la ruta de un archivo temporal; quien lo sirva debe borrarlo.

    Raises:
        ValueError: si el dataset no tiene ninguna muestra.
    """
    import csv
    import io
    import json

    carpeta = _carpeta()
    archivos = [a for sub in sorted(carpeta.iterdir()) if sub.is_dir() for a in sorted(sub.glob("*.png"))] if carpeta.exists() else []
    if not archivos:
        raise ValueError("Todavía no hay muestras para exportar")
    descriptor, ruta_temporal = tempfile.mkstemp(suffix=".zip", prefix="dataset_piezas_")
    os.close(descriptor)
    por_clase: dict[str, int] = {}
    filas: list[dict] = []
    datos_por_archivo: dict[str, dict] = {}
    with zipfile.ZipFile(ruta_temporal, "w", zipfile.ZIP_STORED) as zip_salida:
        for nombre, ampliado, volumen, datos in _recortes_del_dataset():
            datos_por_archivo[nombre] = datos
            for recorte, imagen in (("ampliado", ampliado), ("volumen", volumen)):
                exito, buffer = cv2.imencode(".png", imagen) if imagen is not None else (False, None)
                if exito:
                    zip_salida.writestr(f"{recorte}/{nombre}", buffer.tobytes())
                    filas.append(_fila_metadatos(f"{recorte}/{nombre}", recorte, nombre, datos))
        for archivo in archivos:
            nombre = f"{archivo.parent.name}/{archivo.name}"
            zip_salida.write(archivo, nombre)
            por_clase[archivo.parent.name] = por_clase.get(archivo.parent.name, 0) + 1
            filas.append(_fila_metadatos(nombre, "justo", nombre, datos_por_archivo.get(nombre)))
        texto = io.StringIO()
        escritor = csv.DictWriter(texto, fieldnames=COLUMNAS_METADATOS)
        escritor.writeheader()
        escritor.writerows(filas)
        zip_salida.writestr("metadatos.csv", texto.getvalue())
        zip_salida.writestr("clases.json", json.dumps({"clases": sorted(por_clase), "muestras_por_clase": por_clase}, indent=2))
    return Path(ruta_temporal)


def _fila_metadatos(archivo: str, recorte: str, nombre: str, datos: dict | None) -> dict:
    """Una fila de `metadatos.csv` para el recorte `archivo` de la casilla `nombre` (`<clase>/<captura>_<casilla>.png`)."""
    clase, base = nombre.split("/", 1)
    captura, _, casilla = Path(base).stem.rpartition("_")
    datos = datos or {}
    return {
        "archivo": archivo, "recorte": recorte, "clase": clase, "captura": datos.get("id", captura),
        "casilla": casilla if re.fullmatch(r"[a-h][1-8]", casilla) else "",
        "camara": datos.get("camara", "principal") if datos else "", "grupo": datos.get("grupo", datos.get("id", "")),
    }


class _Reentrenamiento:
    def __init__(self) -> None:
        self.estado = "inactivo"
        self.lineas: deque[str] = deque(maxlen=LINEAS_DE_LOG)
        self.cerrojo = threading.Lock()


_reentrenamiento = _Reentrenamiento()


_candidato = _Reentrenamiento()


def _vigilar(proceso: subprocess.Popen, entrenamiento: _Reentrenamiento | None = None) -> None:
    entrenamiento = entrenamiento or _reentrenamiento
    for linea in proceso.stdout:
        entrenamiento.lineas.append(linea.rstrip())
    codigo = proceso.wait()
    with entrenamiento.cerrojo:
        if codigo == 0:
            piezas.invalidar_modelo()
            entrenamiento.estado = "terminado"
        else:
            entrenamiento.lineas.append(f"El proceso terminó con código {codigo}")
            entrenamiento.estado = "error"


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
        entorno = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "PYTHONUNBUFFERED": "1", "PYTORCH_ENABLE_MPS_FALLBACK": "1"}
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


def iniciar_entrenamiento_candidato() -> None:
    """Lanza `training.entrenar_candidato` en segundo plano (GPU del Mac si hay): entrena un candidato y solo reemplaza al modelo actual si lo supera.

    Raises:
        RuntimeError: si ya hay uno corriendo.
        ValueError: si hay menos de `MINIMO_PARA_REENTRENAR` muestras.
    """
    with _candidato.cerrojo:
        if _candidato.estado == "en_curso":
            raise RuntimeError("Ya hay un entrenamiento en curso")
        total = resumen()["total"]
        if total < MINIMO_PARA_REENTRENAR:
            raise ValueError(f"Hacen falta al menos {MINIMO_PARA_REENTRENAR} muestras, hay {total}")
        entorno = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "PYTHONUNBUFFERED": "1", "PYTORCH_ENABLE_MPS_FALLBACK": "1"}
        proceso = subprocess.Popen(
            [sys.executable, "-m", "training.entrenar_candidato"],
            cwd=RAIZ_REPOSITORIO,
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _candidato.lineas.clear()
        _candidato.estado = "en_curso"
    threading.Thread(target=_vigilar, args=(proceso, _candidato), daemon=True).start()


def estado_entrenamiento_candidato() -> dict:
    """`{estado, progreso, resultado, log}`: `progreso` es la última línea de época («Época 12/50 …»), `resultado` la línea `RESULTADO: …`."""
    lineas = list(_candidato.lineas)
    ultima = lambda prefijo: next((linea for linea in reversed(lineas) if linea.startswith(prefijo)), None)  # noqa: E731
    resultado = ultima("RESULTADO:")
    return {
        "estado": _candidato.estado,
        "progreso": ultima("Época"),
        "resultado": resultado.removeprefix("RESULTADO:").strip() if resultado else None,
        "log": "\n".join(lineas),
    }
