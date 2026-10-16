"""Patrón Strategy: intercambia quién ejecuta el movimiento físico de una
jugada (simulado en PyBullet o real contra el Dobot CR5AS) sin que el resto
del backend lo note (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1; HU9).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import chess

from backend.servicios.brazo.cliente_dobot import ClienteDobot


class EjecutorMovimiento(ABC):
    """Interfaz común para ejecutar un movimiento ya resuelto en el tablero.

    Recibe `tablero_antes` (la posición real inmediatamente antes de la
    jugada) y el objeto `chess.Move` ya resuelto — nunca mantiene su propia
    copia del tablero entre llamadas. Quien implementa deriva acá mismo
    `origen`/`destino` (`chess.square_name`), `captura`
    (`tablero_antes.is_capture(jugada)`) y la promoción (ya viene resuelta en
    `jugada.promotion`, python-chess la arma al parsear la jugada). Este
    ejecutor solo recibe la jugada de la estrategia activa (motor o modelo),
    nunca la del humano — esa ya se jugó a mano sobre el tablero físico real.
    """

    @abstractmethod
    def ejecutar_movimiento(self, tablero_antes: chess.Board, jugada: chess.Move) -> None:
        """Ejecuta `jugada`, tal como estaba la posición antes de jugarla.

        Args:
            tablero_antes: posición real inmediatamente antes de `jugada` —
                nunca el tablero interno del ejecutor (no existe tal cosa),
                para no desincronizarse si el ejecutor se salta jugadas del
                humano.
            jugada: la jugada ya resuelta a aplicar.
        """


class EjecutorSimulado(EjecutorMovimiento):
    """Ejecuta movimientos contra la escena simulada de PyBullet
    (`backend.servicios.simulacion.escena`).

    El import de `escena` queda diferido al constructor y a cada método,
    porque esa dependencia carga `pybullet`, no instalado en todas las
    máquinas del equipo (mismo motivo que el import diferido de `torch` en
    `EstrategiaModelo`, ver `estrategia_jugada.py`) — un import a nivel de
    módulo rompería `EjecutorReal` para quien no tenga pybullet instalado.
    """

    def __init__(self, modo_gui: bool = False):
        from backend.servicios.simulacion.escena import (
            cargar_formas_visuales_piezas,
            crear_escena,
        )

        self.client_id, self.casillas, self.piezas = crear_escena(modo_gui=modo_gui)
        self.formas_visuales = cargar_formas_visuales_piezas(self.client_id)

    def ejecutar_movimiento(self, tablero_antes: chess.Board, jugada: chess.Move) -> None:
        """Mueve la pieza de `jugada` en la escena de PyBullet.

        No mantiene tablero propio entre llamadas — `tablero_antes` (copiado
        acá, nunca mutado) más `jugada` alcanzan para recalcular la escena
        completa cada vez, así que no hay estado interno que se pueda
        desincronizar. `sincronizar_piezas` recrea la escena completa desde
        el tablero resultante, así que una pieza capturada simplemente deja
        de aparecer sin lógica especial.
        """
        from backend.servicios.simulacion.escena import resaltar_jugada, sincronizar_piezas

        origen = chess.square_name(jugada.from_square)
        destino = chess.square_name(jugada.to_square)
        tablero_despues = tablero_antes.copy()
        tablero_despues.push(jugada)

        resaltar_jugada(self.casillas, origen, destino, self.client_id)
        self.piezas = sincronizar_piezas(
            self.client_id, self.piezas, tablero_despues, self.formas_visuales
        )

    def cerrar(self) -> None:
        """Cierra la conexión a PyBullet asociada a esta escena."""
        from backend.servicios.simulacion.escena import cerrar_escena

        cerrar_escena(self.client_id)


class EjecutorReal(EjecutorMovimiento):
    """Ejecuta movimientos contra el brazo físico real, un Dobot CR5AS (colaborativo, 6 ejes), por TCP/IP.

    Usa `ClienteDobot` (`cliente_dobot.py`), que habla el protocolo del controlador V4 por el puerto 29999 con la sintaxis del
    manual (`MovJ(pose={x,y,z,rx,ry,rz},a=..,v=..)`) y espera a que termine cada movimiento antes de mandar el siguiente.
    Está implementado con el módulo estándar `socket`, sin el SDK oficial, para no sumar una dependencia nueva.

    Requisitos antes de mover (el ejecutor falla explícitamente si falta alguno, nunca inventa valores):
    - `posiciones_casillas`: calibración del tablero (`calcular_posiciones_casillas`), con las coordenadas XYZ reales.
    - `orientacion`: `(rx, ry, rz)` de la herramienta con la pinza apuntando al tablero, tomada de `GetPose()` en el robot real.
    - el brazo ya encendido y habilitado (esta clase no manda `PowerOn` ni `EnableRobot`).

    Todavía no resuelve capturas (retirar la pieza que ocupa el destino), enroque, captura al paso ni coronación.
    """

    def __init__(
        self,
        host: str,
        puerto_dashboard: int = 29999,
        timeout_segundos: float = 5.0,
        posiciones_casillas: dict[str, tuple[float, float, float]] | None = None,
        altura_segura_mm: float = 50.0,
        pin_efector_do: int = 1,
        orientacion: tuple[float, float, float] | None = None,
        angulos_cero: tuple[float, ...] | None = None,
        velocidad_global: int = 20,
        cliente: ClienteDobot | None = None,
    ):
        """
        Args:
            host: IP del Dobot en la red local (192.168.5.1 por defecto de fábrica en LAN 1).
            posiciones_casillas: resultado de `calcular_posiciones_casillas`, con las coordenadas reales medidas en el sitio.
            altura_segura_mm: cuánto sube sobre una casilla antes de trasladarse, para no arrastrar piezas. El valor de
                partida **no está verificado contra las piezas reales**: se ajusta con la pieza más alta (el rey).
            pin_efector_do: salida digital `DO(índice, estado)` que activa el efector. Es un **placeholder** hasta confirmar
                cómo está comandada la pinza DH (salida digital o Modbus RS485).
            orientacion: `(rx, ry, rz)` fijo de la herramienta durante toda la jugada.
            angulos_cero: ángulos de las 6 articulaciones de la posición cero, a la que vuelve al terminar. `None` = no vuelve.
            velocidad_global: `SpeedFactor` al conectar (1 a 100); bajo por seguridad.
            cliente: cliente ya armado (para pruebas); si no, se crea uno con `host` y `puerto_dashboard`.
        """
        self.cliente = cliente or ClienteDobot(host, puerto_dashboard, timeout_segundos, velocidad_global)
        self.posiciones_casillas = posiciones_casillas
        self.altura_segura_mm = altura_segura_mm
        self.pin_efector_do = pin_efector_do
        self.orientacion = orientacion
        self.angulos_cero = angulos_cero

    def conectar(self) -> None:
        """Abre la conexión y fija la velocidad global. No enciende ni habilita el brazo."""
        self.cliente.conectar()

    def desconectar(self) -> None:
        """Cierra la conexión (el brazo queda habilitado, como estaba)."""
        self.cliente.cerrar()

    def _efector(self, activo: bool) -> None:
        """Cierra (`True`) o abre (`False`) el efector y espera a que se ejecute."""
        self.cliente.enviar(f"DO({self.pin_efector_do},{1 if activo else 0})")
        self.cliente.esperar_fin()

    def _pose(self, casilla: str, sobre_la_casilla_mm: float = 0.0) -> tuple[float, ...]:
        x, y, z = self.posiciones_casillas[casilla]
        return (x, y, z + sobre_la_casilla_mm, *self.orientacion)

    def ejecutar_movimiento(self, tablero_antes: chess.Board, jugada: chess.Move) -> None:
        """Ejecuta un movimiento simple (sin captura) en el brazo físico real.

        `origen`, `destino` y `captura` se derivan de `tablero_antes`/`jugada`, nunca de un tablero guardado entre llamadas.

        Secuencia (cada paso espera a que el brazo termine): sobre el origen a altura segura (`MovJ`), baja hasta la pieza
        (`MovL`), cierra el efector, sube, se traslada sobre el destino (`MovJ`), baja, abre el efector, sube y, si hay
        `angulos_cero`, vuelve a la posición cero.

        Raises:
            RuntimeError: si falta la calibración del tablero o la orientación de la herramienta.
            NotImplementedError: si `jugada` captura una pieza (retirar la capturada es el siguiente paso, no implementado).
        """
        if self.posiciones_casillas is None:
            raise RuntimeError(
                "No se cargó la calibración del tablero todavía — llamá calcular_posiciones_casillas() con puntos medidos primero."
            )
        if self.orientacion is None:
            raise RuntimeError(
                "Falta la orientación (rx, ry, rz) de la herramienta: tomala de GetPose() con la pinza apuntando al tablero."
            )
        if tablero_antes.is_capture(jugada):
            raise NotImplementedError(
                "Retirar piezas capturadas del tablero físico es el siguiente paso, no implementado todavía."
            )

        origen = chess.square_name(jugada.from_square)
        destino = chess.square_name(jugada.to_square)
        segura = self.altura_segura_mm

        self.cliente.mover_a_pose(self._pose(origen, segura))
        self.cliente.mover_a_pose(self._pose(origen), lineal=True)
        self._efector(True)
        self.cliente.mover_a_pose(self._pose(origen, segura), lineal=True)
        self.cliente.mover_a_pose(self._pose(destino, segura))
        self.cliente.mover_a_pose(self._pose(destino), lineal=True)
        self._efector(False)
        self.cliente.mover_a_pose(self._pose(destino, segura), lineal=True)
        if self.angulos_cero is not None:
            self.cliente.mover_a_angulos(self.angulos_cero)
