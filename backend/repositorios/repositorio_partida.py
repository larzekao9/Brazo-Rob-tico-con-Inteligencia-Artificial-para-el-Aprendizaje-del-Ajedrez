"""Patrón Repository: desacopla el guardado de partidas de la lógica de
`servicio_partida.py` (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.3).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modelos.partida import Partida


class RepositorioPartidas(ABC):
    """Interfaz común para guardar y consultar partidas, sin importar dónde vivan."""

    @abstractmethod
    def guardar(self, partida: Partida) -> None:
        """Guarda (o actualiza) una partida."""

    @abstractmethod
    def obtener(self, partida_id: str) -> Partida:
        """Busca una partida por id.

        Raises:
            KeyError: si no existe una partida con ese id.
        """

    @abstractmethod
    def listar(self) -> list[Partida]:
        """Devuelve todas las partidas guardadas, más reciente primero."""


class RepositorioPartidasEnMemoria(RepositorioPartidas):
    """Guarda las partidas en un dict del proceso — se pierden al reiniciar.

    Esto ya es un registro real (todas las partidas que se juegan mientras
    el backend está corriendo quedan acá, consultables), solo que no
    sobrevive un reinicio del servidor. El día que llegue HU11 con
    PostgreSQL (sección 7 del plan), se agrega `RepositorioPartidasPostgres`
    con esta misma interfaz, sin tocar `servicio_partida.py` ni las rutas.
    """

    def __init__(self) -> None:
        self._partidas: dict[str, Partida] = {}

    def guardar(self, partida: Partida) -> None:
        self._partidas[partida.id] = partida

    def obtener(self, partida_id: str) -> Partida:
        if partida_id not in self._partidas:
            raise KeyError(f"No existe una partida con id {partida_id}")
        return self._partidas[partida_id]

    def listar(self) -> list[Partida]:
        return list(reversed(self._partidas.values()))
