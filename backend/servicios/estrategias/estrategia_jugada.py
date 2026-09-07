"""Patrón Strategy: intercambia quién decide la jugada de respuesta sin que
`servicio_partida.py` lo note (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.servicios.motor.motor_ajedrez import calcular_jugada


class EstrategiaJugada(ABC):
    """Interfaz común para cualquier forma de decidir la jugada de respuesta."""

    @abstractmethod
    def decidir_jugada(self, fen: str) -> str:
        """Devuelve la jugada elegida para la posición dada, en notación SAN."""


class EstrategiaStockfish(EstrategiaJugada):
    """Stockfish decide la jugada — la única estrategia implementada por ahora.

    Las demás (`EstrategiaModelo`, con el modelo propio de HU3/HU4;
    `EstrategiaHumano`, para partida contra otro jugador de HU10) son alcance
    de tesis — se agregan recién cuando exista lo que necesitan.
    """

    def __init__(self, nivel: int = 20):
        self.nivel = nivel

    def decidir_jugada(self, fen: str) -> str:
        return calcular_jugada(fen, nivel=self.nivel)
