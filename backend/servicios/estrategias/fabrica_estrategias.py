"""Factory Method: crea la estrategia de jugada correcta según el tipo de
oponente elegido (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.2).

Complemento natural de Strategy — sin esto, el `if/elif` de qué estrategia
usar termina desparramado por el código en vez de en un solo lugar.
"""
from __future__ import annotations

from backend.servicios.estrategias.estrategia_jugada import EstrategiaJugada, EstrategiaStockfish

TIPOS_SOPORTADOS = {"motor"}


def crear_estrategia_jugada(tipo_oponente: str, nivel: int = 20) -> EstrategiaJugada:
    """Instancia la estrategia de jugada correspondiente al tipo de oponente.

    Args:
        tipo_oponente: hoy solo `"motor"` (Stockfish) está soportado.
            `"modelo"` y `"participante"` son alcance de tesis (ver
            `EstrategiaJugada` en `estrategia_jugada.py`).
        nivel: fuerza de juego — solo aplica a la estrategia `"motor"`.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía.
    """
    if tipo_oponente == "motor":
        return EstrategiaStockfish(nivel=nivel)
    raise ValueError(
        f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
        f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
    )
