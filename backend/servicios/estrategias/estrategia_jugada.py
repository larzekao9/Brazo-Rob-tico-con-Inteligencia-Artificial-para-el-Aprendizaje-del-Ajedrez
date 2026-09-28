"""Patrón Strategy: intercambia quién decide la jugada de respuesta sin que
`servicio_partida.py` lo note (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from backend.servicios.motor.motor_ajedrez import calcular_jugada


class EstrategiaJugada(ABC):
    """Interfaz común para cualquier forma de decidir la jugada de respuesta."""

    @abstractmethod
    def decidir_jugada(self, fen: str) -> str:
        """Devuelve la jugada elegida para la posición dada, en notación SAN."""


class EstrategiaStockfish(EstrategiaJugada):
    """Stockfish decide la jugada.

    `EstrategiaModelo` usa el modelo propio de HU3/HU4. `EstrategiaHumano`,
    para partida contra otro jugador (HU10), sigue siendo alcance de tesis —
    se agrega recién cuando exista lo que necesita.
    """

    def __init__(self, nivel: int = 20):
        self.nivel = nivel

    def decidir_jugada(self, fen: str) -> str:
        return calcular_jugada(fen, nivel=self.nivel)


class EstrategiaModelo(EstrategiaJugada):
    """El modelo propio (HU4) decide la jugada, en vez de Stockfish.

    El import de `inferencia` es diferido a `decidir_jugada` porque esa
    dependencia carga `torch`, no instalado en todas las máquinas del equipo
    (ver `pytest.importorskip("torch")` en `test_modelo_jugadas.py`) — un
    import a nivel de módulo rompería el oponente `"motor"` para quien no
    tenga torch instalado.

    `nivel` (0-20, el del perfil del jugador) calibra qué tan fuerte juega el
    modelo: `None` o >= 18 es el modo maestro determinista; por debajo, el modelo
    muestrea entre sus mejores candidatas (ver `predecir_jugada_maestra`). En
    ningún caso interviene Stockfish.
    """

    def __init__(self, ruta_checkpoint: str | Path | None = None, nivel: int | None = None):
        self.ruta_checkpoint = ruta_checkpoint
        self.nivel = nivel

    def decidir_jugada(self, fen: str) -> str:
        from backend.servicios.aprendizaje.inferencia import (
            RUTA_CHECKPOINT_POR_DEFECTO,
            predecir_jugada_maestra,
        )

        ruta = self.ruta_checkpoint if self.ruta_checkpoint is not None else RUTA_CHECKPOINT_POR_DEFECTO
        return predecir_jugada_maestra(fen, ruta, nivel=self.nivel)
