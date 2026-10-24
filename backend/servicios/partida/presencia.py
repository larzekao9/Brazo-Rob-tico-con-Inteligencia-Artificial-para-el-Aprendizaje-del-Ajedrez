"""Señales de vida de las partidas con reloj: cuándo fue la última vez que el jugador estuvo en la pantalla.

Una partida con reloj no se puede dejar: si el jugador se va (cierra la pestaña, cambia de pestaña, pierde la conexión) y
pasan más de `ciclo_vida.SEGUNDOS_AUSENCIA_CON_RELOJ` sin que la pantalla avise, la partida se da por perdida (como en
Lichess). La pantalla avisa cada pocos segundos con `POST /partida/{id}/presencia` mientras la partida está a la vista.

Es memoria del proceso a propósito: una señal de vida dura segundos, no vale la pena escribirla en la base cada 5 segundos
por jugador. Solo cuenta una partida de la que ya llegó alguna señal; si no hay (la pantalla es una versión que no avisa,
como la app móvil, o el servidor se reinició) esa partida no se da por perdida por ausencia y queda sujeta a la regla de
inactividad de los 2 días. El backend corre en un solo proceso (`deploy/Dockerfile`): con varios procesos habría que
guardar esto en la base.
"""
from __future__ import annotations

import time

_ultima_senal: dict[str, float] = {}
"""`id de partida` -> instante (`time.monotonic()`) de la última señal de vida."""


def registrar(partida_id: str, ahora: float | None = None) -> None:
    """Anota que el jugador está en la pantalla de esta partida en este momento."""
    _ultima_senal[partida_id] = time.monotonic() if ahora is None else ahora


def segundos_sin_senal(partida_id: str, ahora: float | None = None) -> float | None:
    """Segundos desde la última señal de vida, o `None` si nunca llegó una de esta partida."""
    ultima = _ultima_senal.get(partida_id)
    if ultima is None:
        return None
    return (time.monotonic() if ahora is None else ahora) - ultima


def olvidar(partida_id: str) -> None:
    """Borra lo anotado de una partida (cuando ya terminó o se cerró)."""
    _ultima_senal.pop(partida_id, None)


def olvidar_salvo(vigentes: set[str]) -> None:
    """Deja solo las partidas `vigentes`: barre lo que quedó de partidas que ya no están en curso."""
    for partida_id in list(_ultima_senal):
        if partida_id not in vigentes:
            del _ultima_senal[partida_id]
