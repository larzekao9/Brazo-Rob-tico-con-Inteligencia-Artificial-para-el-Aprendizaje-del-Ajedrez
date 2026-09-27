"""Conecta la estrategia de jugada activa con el ejecutor de movimiento físico
(brazo simulado en PyBullet o Dobot real), sin que `servicio_partida.mover`
tenga que saber nada de Strategy/Factory de `ejecutor_movimiento.py`
(PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1/4.2; HU9).

Solo ejecuta la jugada de la estrategia (motor o modelo), nunca la del
humano — esa ya se jugó a mano sobre el tablero físico real (por eso
`mover_desde_foto` puede detectarla con la cámara); pedirle al brazo que la
"reproduzca" agarraría una pieza que ya no está en esa casilla.
"""
from __future__ import annotations

import logging
import os

import chess

from backend.modelos.partida import Partida
from backend.servicios.brazo.ejecutor_movimiento import EjecutorMovimiento
from backend.servicios.brazo.fabrica_ejecutores import crear_ejecutor_movimiento

logger = logging.getLogger(__name__)

_ejecutor: EjecutorMovimiento | None = None


def _obtener_ejecutor() -> EjecutorMovimiento:
    """Crea, una sola vez por proceso (cacheado a nivel módulo), el ejecutor
    de movimiento configurado para todo el backend.

    El modo sale de `AJEDREZ_MODO_BRAZO` — `"simulado"` por defecto. Nunca
    `"real"` por defecto (regla 3 de `CLAUDE.md`: no tocar el brazo físico
    real todavía, salvo prueba explícita en el sitio, que no pasó). Los
    kwargs de `EjecutorReal` (host, puerto) también salen de variables de
    entorno en vez de ir hardcodeados acá, porque todavía no hay un host de
    Dobot ni una calibración de sitio fijos para este proyecto.
    """
    global _ejecutor
    if _ejecutor is not None:
        return _ejecutor

    modo = os.environ.get("AJEDREZ_MODO_BRAZO", "simulado")
    kwargs: dict = {}
    if modo == "real":
        kwargs["host"] = os.environ["AJEDREZ_BRAZO_HOST"]
        puerto_dashboard = os.environ.get("AJEDREZ_BRAZO_PUERTO_DASHBOARD")
        if puerto_dashboard is not None:
            kwargs["puerto_dashboard"] = int(puerto_dashboard)
    _ejecutor = crear_ejecutor_movimiento(modo, **kwargs)
    return _ejecutor


def ejecutar_respuesta_en_brazo(
    partida: Partida, tablero_antes: chess.Board, jugada: chess.Move
) -> str | None:
    """Ejecuta en el brazo la jugada de respuesta que ya decidió la estrategia activa.

    No hace nada (devuelve `None` de inmediato) si `partida.usa_brazo` es
    `False` — la mayoría de las partidas.

    `servicio_partida.mover` llama a esto ya con la jugada de la estrategia
    resuelta (Stockfish o el modelo ya decidieron, sin errores): un fallo acá
    es siempre del brazo (desconectado, calibración sin cargar, captura
    todavía no implementada), nunca de la jugada en sí, y no debe romper el
    juego digital ni la respuesta HTTP — cualquier excepción se loguea y se
    devuelve como mensaje en vez de propagarse.

    Returns:
        `None` si no hubo error (incluido el caso `usa_brazo=False`); el
        mensaje del error en caso contrario.
    """
    if not partida.usa_brazo:
        return None
    try:
        ejecutor = _obtener_ejecutor()
        ejecutor.ejecutar_movimiento(tablero_antes, jugada)
    except Exception as error:
        logger.exception(
            "Fallo al ejecutar en el brazo la jugada de respuesta de la partida %s", partida.id
        )
        return str(error)
    return None
