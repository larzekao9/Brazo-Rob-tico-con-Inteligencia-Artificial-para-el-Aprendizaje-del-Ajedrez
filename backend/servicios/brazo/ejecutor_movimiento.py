"""Patrón Strategy: intercambia quién ejecuta el movimiento físico de una
jugada (simulado en PyBullet o real contra el Dobot CR5AS) sin que el resto
del backend lo note (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1; HU9).
"""
from __future__ import annotations

import socket
from abc import ABC, abstractmethod

import chess


class EjecutorMovimiento(ABC):
    """Interfaz común para ejecutar un movimiento ya resuelto en el tablero.

    `origen`/`destino` son casillas en notación algebraica (ej. "e2"/"e4") —
    la conversión de SAN a UCI ya se hizo antes de llegar acá, con
    `move.uci()` de `python-chess`.
    """

    @abstractmethod
    def ejecutar_movimiento(self, origen: str, destino: str, captura: bool) -> None:
        """Ejecuta el movimiento de `origen` a `destino`.

        Args:
            origen: casilla de origen en notación algebraica.
            destino: casilla de destino en notación algebraica.
            captura: si la jugada captura una pieza rival. Sin efecto en
                `EjecutorSimulado` (PyBullet recrea la escena completa desde
                el tablero), pero necesario en `EjecutorReal`, que primero
                debe retirar del tablero físico la pieza capturada.
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
        self.tablero = chess.Board()
        self.formas_visuales = cargar_formas_visuales_piezas(self.client_id)

    def ejecutar_movimiento(self, origen: str, destino: str, captura: bool) -> None:
        """Mueve la pieza de `origen` a `destino` en la escena de PyBullet.

        Si es un peón llegando a la última fila, promueve a dama por
        defecto (ver nota en `docs/plan_sprints.md`: "la promoción de peón
        siempre es a dama"). `captura` no cambia la lógica acá:
        `sincronizar_piezas` recrea la escena completa desde `self.tablero`,
        así que una pieza capturada simplemente deja de aparecer.
        """
        from backend.servicios.simulacion.escena import resaltar_jugada, sincronizar_piezas

        pieza = self.tablero.piece_at(chess.parse_square(origen))
        es_promocion = (
            pieza is not None
            and pieza.piece_type == chess.PAWN
            and destino[1] in ("1", "8")
        )
        uci = origen + destino + ("q" if es_promocion else "")
        movimiento = chess.Move.from_uci(uci)

        resaltar_jugada(self.casillas, origen, destino, self.client_id)
        self.tablero.push(movimiento)
        self.piezas = sincronizar_piezas(
            self.client_id, self.piezas, self.tablero, self.formas_visuales
        )

    def cerrar(self) -> None:
        """Cierra la conexión a PyBullet asociada a esta escena."""
        from backend.servicios.simulacion.escena import cerrar_escena

        cerrar_escena(self.client_id)


class EjecutorReal(EjecutorMovimiento):
    """Ejecuta movimientos contra el brazo físico real, un Dobot CR5AS
    (colaborativo, 6 ejes), por TCP/IP.

    Habla por el puerto **29999** (dashboard: comandos de control como texto
    plano, ej. `EnableRobot()`, `DisableRobot()`, `ClearError()`,
    `MovJ(x,y,z,rx,ry,rz)`, `MovL(x,y,z,rx,ry,rz)` — se escriben como string
    ASCII por el socket y se lee de vuelta una respuesta de texto). El
    puerto **30004** (feedback en tiempo real) queda fuera de este esqueleto.

    Implementado a mano con el módulo estándar `socket`, no con el SDK
    oficial `Dobot-Arm/TCP-IP-Python-V4` (ese repo es código fuente para
    copiar, no un paquete de PyPI, y esto evita sumar una dependencia nueva
    sin pinear).

    Todavía no mueve el brazo real: falta la cinemática inversa (casilla del
    tablero físico -> coordenadas XYZ del Dobot) y la calibración del
    tablero físico contra el espacio de trabajo del robot — ver
    `ejecutar_movimiento` y `docs/plan_sprints.md`, sección HU9,
    "Todavía sin empezar (el núcleo real de HU9)".
    """

    def __init__(
        self,
        host: str,
        puerto_dashboard: int = 29999,
        timeout_segundos: float = 5.0,
    ):
        self.host = host
        self.puerto_dashboard = puerto_dashboard
        self.timeout_segundos = timeout_segundos
        self._socket: socket.socket | None = None

    def conectar(self) -> None:
        """Abre la conexión TCP con el puerto dashboard (29999) y habilita el robot."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout_segundos)
        self._socket.connect((self.host, self.puerto_dashboard))
        self._enviar_comando("EnableRobot()")

    def desconectar(self) -> None:
        """Deshabilita el robot y cierra la conexión TCP, si había una abierta."""
        if self._socket is None:
            return
        try:
            self._enviar_comando("DisableRobot()")
        finally:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def _enviar_comando(self, comando: str) -> str:
        """Envía `comando` como texto ASCII por el socket y devuelve la respuesta.

        Args:
            comando: comando del dashboard del Dobot, ej. `"EnableRobot()"`.

        Raises:
            RuntimeError: si todavía no se llamó a `conectar()`.
        """
        if self._socket is None:
            raise RuntimeError(
                "No hay conexión abierta con el Dobot: llamá a conectar() antes de "
                "enviar comandos por el puerto dashboard (29999)."
            )
        self._socket.sendall(comando.encode("ascii"))
        return self._socket.recv(1024).decode("ascii", errors="replace")

    def ejecutar_movimiento(self, origen: str, destino: str, captura: bool) -> None:
        """Sin implementar todavía: falta la cinemática inversa real.

        Raises:
            NotImplementedError: siempre. Traducir `origen`/`destino` (casillas
                del tablero físico) a coordenadas XYZ del Dobot requiere
                calibrar el tablero físico contra el espacio de trabajo del
                robot, trabajo pendiente documentado en `docs/plan_sprints.md`
                bajo HU9 y todavía no hecho. No se inventa una tabla de
                calibración de relleno acá: sería peor que dejarlo explícito,
                porque parecería funcionar mientras en realidad movería el
                brazo a un lugar arbitrario.
        """
        raise NotImplementedError(
            "EjecutorReal.ejecutar_movimiento no está implementado todavía: falta la "
            "cinemática inversa real (casilla del tablero físico -> coordenadas XYZ del "
            "Dobot CR5AS) y la calibración del tablero físico contra el espacio de "
            "trabajo del robot (ver docs/plan_sprints.md, sección HU9)."
        )
