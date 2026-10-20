"""Captura una foto del tablero desde una cámara fija conectada a esta
máquina (HU1, RF06).

Solo toma la foto — pasarla por `reconocer_tablero` (en `reconocimiento.py`)
y mostrarla en una pantalla es responsabilidad de HU6, no de acá.

La fuente de la cámara se puede fijar por variable de entorno `CAMARA_FUENTE`
(mismo patrón que `DATABASE_URL` en `backend/database.py` — nada hardcodeado
en el código), para no depender de la webcam integrada de la laptop, que no
se puede reorientar hacia el tablero y suele tener peor calidad que un
celular:

- Sin configurar: cámara 0, la webcam por defecto de la máquina.
- Un número (ej. `CAMARA_FUENTE=1`): otro índice de cámara local — el caso
  de un celular conectado como cámara "virtual" vía USB con DroidCam o Iriun
  Webcam, que aparece como una webcam más para Windows.
- Una URL (ej. `CAMARA_FUENTE=http://192.168.1.23:8080/video`): un stream de
  red, el caso de la app "IP Webcam" (Android) — sirve tanto conectando el
  celular y la laptop a la misma red WiFi como compartiendo el propio
  hotspot del celular a la laptop (más estable si el WiFi de la facultad es
  lento, porque no depende de esa red para nada).
"""
from __future__ import annotations

import os
import threading
import time

import cv2
import numpy as np


# Una cámara solo la puede abrir un proceso a la vez: la vista en vivo, el estado y el reconocimiento llegan en paralelo
# y, sin esto, el segundo `VideoCapture` falla con "no se pudo abrir" (503) mientras el primero la tiene tomada.
_CERROJO_CAMARA = threading.Lock()


def _fuente_por_defecto() -> int | str:
    """Resuelve `CAMARA_FUENTE` del entorno a lo que espera `cv2.VideoCapture`."""
    valor = os.environ.get("CAMARA_FUENTE", "").strip()
    if not valor:
        return 0
    if valor.isdigit():
        return int(valor)
    return valor


def _api_por_defecto() -> int | None:
    """Backend de captura de Windows según `CAMARA_API` (`MSMF` o `DSHOW`); `None` deja que OpenCV elija.

    Con varias cámaras (reales y virtuales como Iriun o DroidCam) cada backend las numera distinto: el índice 5 de MSMF no es el
    5 de DirectShow. Por eso, cuando la cámara se eligió por número, conviene fijar también el backend con el que se midió.
    """
    nombre = os.environ.get("CAMARA_API", "").strip().upper()
    return {"MSMF": cv2.CAP_MSMF, "DSHOW": cv2.CAP_DSHOW}.get(nombre)


def capturar_foto_tablero(fuente: int | str | None = None) -> np.ndarray:
    """Toma una foto desde la cámara/fuente indicada.

    Args:
        fuente: índice de cámara local (int) o URL de un stream de red
            (str). Si no se pasa, se resuelve desde `CAMARA_FUENTE` (ver
            docstring del módulo).

    Returns:
        La imagen capturada, en el mismo formato BGR que espera
        `reconocer_tablero` (el que devuelve `cv2.imread`).

    Raises:
        RuntimeError: si no se pudo abrir la cámara/fuente o capturar un frame.
    """
    fuente_resuelta = fuente if fuente is not None else _fuente_por_defecto()
    with _CERROJO_CAMARA:
        return _captura_continua(fuente_resuelta).ultimo_frame()


SEGUNDOS_INACTIVA = 15.0
"""Sin pedidos de fotos durante este tiempo, la cámara se suelta (otra app puede usarla) y se reabre al siguiente pedido."""


class _CapturaContinua:
    """Mantiene la cámara abierta leyendo frames en un hilo, para que pedir una foto sea instantáneo y siempre actual.

    Abrir la cámara y esperar su autoexposición en cada foto (lo que se hacía antes) tardaba ~2 s; además una cámara que se
    queda abierta sin leer acumula frames viejos en el búfer (más atraso en streams de red). Aquí el hilo lee siempre y la foto
    es el último frame leído. El hilo termina solo tras `SEGUNDOS_INACTIVA` sin pedidos.
    """

    def __init__(self, fuente: int | str) -> None:
        self.fuente = fuente
        self._frame: np.ndarray | None = None
        self._error: str | None = None
        self._vivo = True
        self._ultimo_pedido = time.monotonic()
        self._listo = threading.Event()
        self._condicion = threading.Condition()
        self._numero = 0
        api = _api_por_defecto() if isinstance(fuente, int) else None
        self._camara = cv2.VideoCapture(fuente, api) if api is not None else cv2.VideoCapture(fuente)
        if not self._camara.isOpened():
            self._camara.release()
            raise RuntimeError(f"No se pudo abrir la cámara/fuente {fuente!r}")
        self._camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._hilo = threading.Thread(target=self._leer, daemon=True, name="captura-continua")
        self._hilo.start()

    def detener(self) -> None:
        """Suelta la cámara ya (no espera a la inactividad); sirve para abrir otra fuente."""
        self._ultimo_pedido = float("-inf")
        self._hilo.join(timeout=3.0)

    @property
    def vivo(self) -> bool:
        return self._vivo

    def _leer(self) -> None:
        fallos = 0
        leidos = 0
        try:
            while time.monotonic() - self._ultimo_pedido < SEGUNDOS_INACTIVA:
                exito, imagen = self._camara.read()
                if not exito:
                    fallos += 1
                    if fallos > 30:
                        self._error = f"No se pudo capturar una foto de la fuente {self.fuente!r}"
                        break
                    time.sleep(0.1)
                    continue
                fallos = 0
                leidos += 1
                with self._condicion:
                    self._frame = imagen
                    self._numero += 1
                    self._condicion.notify_all()
                # Una webcam necesita unos frames para ajustar exposición y balance de blancos: los primeros salen oscuros.
                if leidos >= (12 if isinstance(self.fuente, int) else 1):
                    self._listo.set()
        finally:
            self._vivo = False
            self._camara.release()
            self._listo.set()
            with self._condicion:
                self._condicion.notify_all()

    def esperar_frame(self, despues_de: int, timeout: float = 5.0) -> tuple[int, np.ndarray] | None:
        """Bloquea hasta que haya un frame posterior al número `despues_de`; `None` si no llega o la cámara se cerró."""
        self._ultimo_pedido = time.monotonic()
        with self._condicion:
            self._condicion.wait_for(lambda: self._numero > despues_de or not self._vivo, timeout=timeout)
            if self._numero <= despues_de or self._frame is None:
                return None
            return self._numero, self._frame.copy()

    def ultimo_frame(self) -> np.ndarray:
        self._ultimo_pedido = time.monotonic()
        if not self._listo.wait(timeout=10.0) or self._frame is None:
            raise RuntimeError(self._error or f"No se pudo capturar una foto de la fuente {self.fuente!r}")
        return self._frame.copy()


_captura: _CapturaContinua | None = None


def _captura_continua(fuente: int | str) -> _CapturaContinua:
    """La captura en curso para `fuente`; abre una nueva si no hay, murió o cambió la fuente."""
    global _captura
    if _captura is not None and (not _captura.vivo or _captura.fuente != fuente):
        _captura.detener()
        _captura = None
    if _captura is None:
        _captura = _CapturaContinua(fuente)
    return _captura


def _capturar_sin_cerrojo(fuente: int | str | None) -> np.ndarray:
    """Cuerpo de `capturar_foto_tablero`, ya con la cámara reservada para esta llamada."""
    fuente_resuelta = fuente if fuente is not None else _fuente_por_defecto()
    api = _api_por_defecto() if isinstance(fuente_resuelta, int) else None
    camara = cv2.VideoCapture(fuente_resuelta, api) if api is not None else cv2.VideoCapture(fuente_resuelta)
    try:
        if not camara.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara/fuente {fuente_resuelta!r}")
        # Sin esto, algunas cámaras virtuales (ej. Iriun Webcam) devuelven un
        # frame con un formato/tiling raro en vez de la imagen completa —
        # pedir la resolución explícitamente antes de leer lo evita.
        camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        # Las cámaras virtuales a veces fallan el primer frame justo después
        # de abrirse (necesitan un instante para "calentar") — un par de
        # reintentos cortos alcanza, sin agregar demora perceptible a una
        # cámara física que siempre responde a la primera.
        # Una webcam USB necesita unos frames para ajustar exposición y balance de blancos: los primeros salen oscuros.
        ultima = None
        for _ in range(12 if isinstance(fuente_resuelta, int) else 1):
            exito, imagen = camara.read()
            if exito:
                ultima = imagen
        if ultima is not None:
            return ultima
        for intento in range(3):
            exito, imagen = camara.read()
            if exito:
                return imagen
            time.sleep(0.3)
        raise RuntimeError(f"No se pudo capturar una foto de la fuente {fuente_resuelta!r}")
    finally:
        camara.release()


def flujo_de_frames(fuente: int | str | None = None):
    """Generador de frames BGR EN VIVO de la cámara fija: cada uno es el más reciente (se saltea los que no dio tiempo a procesar).

    Termina si la cámara deja de entregar imágenes. Lanza `RuntimeError` al inicio si no se puede abrir.
    """
    fuente_resuelta = fuente if fuente is not None else _fuente_por_defecto()
    with _CERROJO_CAMARA:
        captura = _captura_continua(fuente_resuelta)
        captura.ultimo_frame()  # espera el primer frame (y la exposición) con el cerrojo, una sola vez
    ultimo = 0
    while True:
        entrega = captura.esperar_frame(ultimo)
        if entrega is None:
            return
        ultimo, frame = entrega
        yield frame
