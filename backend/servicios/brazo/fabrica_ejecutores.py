"""Factory Method: crea el ejecutor de movimiento correcto según el modo
elegido (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.2).

Complemento natural de Strategy — sin esto, el `if/elif` de qué ejecutor usar
termina desparramado por el código en vez de en un solo lugar.
"""
from __future__ import annotations

from backend.servicios.brazo.ejecutor_movimiento import (
    EjecutorMovimiento,
    EjecutorReal,
    EjecutorSimulado,
)

TIPOS_SOPORTADOS = {"simulado", "real"}


def crear_ejecutor_movimiento(modo: str, **kwargs) -> EjecutorMovimiento:
    """Instancia el ejecutor de movimiento correspondiente al modo elegido.

    Args:
        modo: `"simulado"` (PyBullet, `EjecutorSimulado`) o `"real"` (Dobot
            CR5AS por TCP/IP, `EjecutorReal` — todavía sin cinemática
            inversa real, ver `EjecutorReal.ejecutar_movimiento`).
        **kwargs: argumentos propios de cada ejecutor. `"real"` requiere al
            menos `host`; si falta, el `TypeError` nativo de la
            instanciación ya explica el problema.

    Raises:
        ValueError: si `modo` no es un modo soportado todavía.
    """
    if modo == "simulado":
        return EjecutorSimulado(**kwargs)
    if modo == "real":
        return EjecutorReal(**kwargs)
    raise ValueError(
        f"Modo de ejecutor '{modo}' no soportado todavía (disponibles: {sorted(TIPOS_SOPORTADOS)})"
    )
