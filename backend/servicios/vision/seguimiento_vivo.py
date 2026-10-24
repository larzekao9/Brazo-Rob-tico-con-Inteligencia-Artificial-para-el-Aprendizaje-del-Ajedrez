"""El seguimiento de la partida (`seguimiento_jugadas.Seguimiento`) en marcha: uno solo para todo el backend, que avanza un cuadro por cada llamada.

Quien lo usa (la pantalla) llama a `avanzar()` una vez por segundo: no hay ningún hilo ni trabajo en segundo plano, así que si se cierra la pantalla no se
gasta nada. Cada llamada toma el último cuadro de la cámara (la captura continua ya lo tiene a mano), lo compara con el anterior y con la foto base y
devuelve qué pasó (nada, movimiento, una jugada o una alerta).
"""
from __future__ import annotations

import threading

import chess

from backend.servicios.vision import seguimiento_jugadas, tablero
from backend.servicios.vision.camara import capturar_foto_tablero

_cerrojo = threading.Lock()
_actual: seguimiento_jugadas.Seguimiento | None = None
_camara = "principal"


class SinSeguimiento(Exception):
    """No hay un seguimiento iniciado."""


def _datos(seguimiento: seguimiento_jugadas.Seguimiento, camara: str) -> dict:
    return {
        "activo": True, "camara": camara, "estado": seguimiento.estado, "fen": seguimiento.fen, "jugadas": list(seguimiento.jugadas),
        "turno": "blancas" if chess.Board(seguimiento.fen).turn == chess.WHITE else "negras", "alerta": seguimiento.ultima_alerta,
        "puede_deshacer": bool(seguimiento.historial),
    }


def iniciar(fen: str | None = None, camara: str = "principal") -> dict:
    """Empieza a vigilar la partida desde `fen` (por defecto, la posición inicial) con las esquinas calibradas de `camara`.

    Raises:
        ValueError: FEN inválido o la cámara no está calibrada.
    """
    global _actual, _camara
    esquinas = tablero.cargar_esquinas_calibradas(tablero.archivo_esquinas(camara))
    if esquinas is None:
        raise ValueError(f"La cámara {camara} no está calibrada: calibrala antes de seguir una partida")
    chess.Board(fen or chess.STARTING_FEN)  # valida (ValueError)
    with _cerrojo:
        _actual = seguimiento_jugadas.Seguimiento(esquinas, fen or chess.STARTING_FEN)
        _camara = camara
        return _datos(_actual, camara)


def detener() -> dict:
    global _actual
    with _cerrojo:
        _actual = None
    return {"activo": False}


def estado() -> dict:
    with _cerrojo:
        return _datos(_actual, _camara) if _actual is not None else {"activo": False}


def fijar_posicion(fen: str) -> dict:
    """Cambia la posición conocida (por ejemplo, después de que el robot jugó) y vuelve a tomar la foto base cuando el tablero esté quieto.

    Raises:
        SinSeguimiento: no hay seguimiento. ValueError: FEN inválido.
    """
    with _cerrojo:
        if _actual is None:
            raise SinSeguimiento()
        _actual.fijar_posicion(fen)
        return _datos(_actual, _camara)


def rebasar() -> dict:
    """Vuelve a tomar la foto base con la posición que ya se sabe (las piezas quedaron bien pero la imagen no coincide con la foto).

    Raises:
        SinSeguimiento: no hay seguimiento.
    """
    with _cerrojo:
        if _actual is None:
            raise SinSeguimiento()
        _actual.rebasar()
        return _datos(_actual, _camara)


def deshacer() -> dict:
    """Quita la última jugada detectada (si se detectó mal) y vuelve a tomar la foto base. Devuelve los datos del seguimiento más `deshecha` (el SAN quitado).

    Raises:
        SinSeguimiento: no hay seguimiento. ValueError: no hay jugada que deshacer.
    """
    with _cerrojo:
        if _actual is None:
            raise SinSeguimiento()
        san = _actual.deshacer()
        return {**_datos(_actual, _camara), "deshecha": san}


def vista() -> dict:
    """Cómo decidió el último cuadro (fotos base y actual, cambios por casilla, jugadas candidatas).

    Raises:
        SinSeguimiento: no hay seguimiento.
    """
    with _cerrojo:
        if _actual is None:
            raise SinSeguimiento()
        return _actual.vista()


def avanzar(con_vista: bool = False) -> dict:
    """Procesa el último cuadro de la cámara y devuelve lo que pasó (ver `Seguimiento.actualizar`) más `activo` y `camara`; con `con_vista`, también `vista`.

    Raises:
        SinSeguimiento: no hay seguimiento. RuntimeError: la cámara no está disponible.
    """
    with _cerrojo:
        if _actual is None:
            raise SinSeguimiento()
        seguimiento, camara = _actual, _camara
    imagen = capturar_foto_tablero(camara=camara)
    with _cerrojo:
        if _actual is not seguimiento:  # se detuvo o reinició mientras se tomaba el cuadro
            raise SinSeguimiento()
        resultado = {"activo": True, "camara": camara, **seguimiento.actualizar(imagen)}
        resultado["alerta"] = seguimiento.ultima_alerta
        if con_vista:
            resultado["vista"] = seguimiento.vista()
        return resultado
