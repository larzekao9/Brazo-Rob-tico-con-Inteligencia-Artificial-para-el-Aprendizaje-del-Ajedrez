"""Factory Method: crea la estrategia de jugada correcta según el tipo de
oponente elegido (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.2).

Complemento natural de Strategy — sin esto, el `if/elif` de qué estrategia
usar termina desparramado por el código en vez de en un solo lugar.
"""
from __future__ import annotations

from backend.servicios.aprendizaje.niveles import NIVEL_MAX_MODELO
from backend.servicios.estrategias.estrategia_jugada import (
    EstrategiaJugada,
    EstrategiaModelo,
    EstrategiaStockfish,
)

TIPOS_SOPORTADOS = {"motor", "modelo"}


def crear_estrategia_jugada(tipo_oponente: str, nivel: int = 20) -> EstrategiaJugada:
    """Instancia la estrategia de jugada correspondiente al tipo de oponente.

    Args:
        tipo_oponente: `"motor"` (Stockfish) o `"modelo"` (modelo propio,
            HU4). `"participante"` (partida contra otro jugador, HU10) sigue
            siendo alcance de tesis (ver `EstrategiaJugada` en
            `estrategia_jugada.py`).
        nivel: fuerza de juego (0-20), viene del perfil del jugador. Con
            `"motor"` es el Skill Level de Stockfish y usa la escala completa.
            Con `"modelo"` el modelo propio lo usa para calibrar su
            dificultad: el techo es `NIVEL_MAX_MODELO` (18, "Maestro"), así
            que un nivel mayor se recorta a 18 — el modelo ya juega
            determinista desde ahí y 19 o 20 no lo harían más fuerte. Por
            debajo de 18 muestrea entre sus mejores candidatas. En ambos casos
            la jugada la decide el oponente elegido: el modelo nunca consulta
            a Stockfish.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía.
    """
    if tipo_oponente == "motor":
        return EstrategiaStockfish(nivel=nivel)
    if tipo_oponente == "modelo":
        return EstrategiaModelo(nivel=min(nivel, NIVEL_MAX_MODELO))
    raise ValueError(
        f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
        f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
    )
