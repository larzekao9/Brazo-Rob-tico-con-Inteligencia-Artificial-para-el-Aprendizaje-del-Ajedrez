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

    Movimientos sin captura ya arman y envían la secuencia real de comandos
    (`MovJ`/`MovL`/`DO`) una vez cargada la calibración del tablero (ver
    `calcular_posiciones_casillas` en `calibracion_tablero.py`). Todavía no
    resuelve la lógica de captura (retirar del tablero físico la pieza en
    `destino` antes de mover la propia) — ver `ejecutar_movimiento` — ni trae
    cinemática inversa propia: usa directamente las coordenadas XYZ
    calibradas para cada casilla, que el propio Dobot resuelve internamente
    al recibir `MovJ`/`MovL`.
    """

    def __init__(
        self,
        host: str,
        puerto_dashboard: int = 29999,
        timeout_segundos: float = 5.0,
        posiciones_casillas: dict[str, tuple[float, float, float]] | None = None,
        altura_segura_mm: float = 50.0,
        pin_efector_do: int = 1,
    ):
        """Guarda la configuración de conexión y de calibración del tablero.

        Args:
            host: IP del Dobot en la red local.
            puerto_dashboard: puerto de comandos de control (29999 por
                defecto).
            timeout_segundos: timeout del socket TCP.
            posiciones_casillas: resultado de `calcular_posiciones_casillas`
                (`calibracion_tablero.py`), con las coordenadas XYZ reales en
                mm de cada casilla del tablero físico, medidas en el sitio.
                `None` hasta que se cargue esa calibración —
                `ejecutar_movimiento` falla explícitamente mientras tanto, no
                inventa coordenadas.
            altura_segura_mm: cuánto sube en Z, en mm, sobre una casilla
                antes de trasladarse lateralmente, para no arrastrar piezas
                al pasar por encima de otras. El default de 50.0 es un valor
                de partida razonable, **no verificado contra las piezas
                reales** — hay que ajustarlo con la altura real medida en el
                sitio el día de la prueba.
            pin_efector_do: índice del `DO(index, status)` del dashboard del
                Dobot que activa/desactiva el efector final. El default de 1
                es un **placeholder** — hay que confirmarlo contra cómo esté
                cableado el efector real (gripper, ventosa, u otro mecanismo;
                todavía no se sabe cuál es).
        """
        self.host = host
        self.puerto_dashboard = puerto_dashboard
        self.timeout_segundos = timeout_segundos
        self.posiciones_casillas = posiciones_casillas
        self.altura_segura_mm = altura_segura_mm
        self.pin_efector_do = pin_efector_do
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
        """Ejecuta un movimiento simple (sin captura) en el brazo físico real.

        Secuencia enviada por el puerto dashboard: sube a altura segura sobre
        `origen` (`MovJ`), baja en línea recta hasta la pieza (`MovL`), activa
        el efector (`DO`), vuelve a subir a altura segura (`MovL`), se
        traslada en `MovJ` sobre `destino`, baja (`MovL`), desactiva el
        efector (`DO`) y sube a altura segura otra vez (`MovL`) — 8 comandos
        en total. `rx`, `ry`, `rz` van fijos en 0 (orientación fija de la
        herramienta, no se varía).

        La lógica de captura (retirar del tablero físico la pieza que ocupa
        `destino` antes de mover la propia) todavía no está implementada — es
        el siguiente paso una vez validado este movimiento simple.

        Raises:
            RuntimeError: si todavía no se cargó `self.posiciones_casillas`
                (falta correr `calcular_posiciones_casillas` con puntos
                medidos reales primero).
            NotImplementedError: si `captura` es `True` — retirar piezas
                capturadas del tablero físico es el siguiente paso, no
                implementado todavía.
        """
        if self.posiciones_casillas is None:
            raise RuntimeError(
                "No se cargó la calibración del tablero todavía — llamá "
                "calcular_posiciones_casillas() con puntos medidos primero."
            )
        if captura:
            raise NotImplementedError(
                "Retirar piezas capturadas del tablero físico es el siguiente paso, "
                "no implementado todavía."
            )

        x_origen, y_origen, z_origen = self.posiciones_casillas[origen]
        x_destino, y_destino, z_destino = self.posiciones_casillas[destino]
        z_segura_origen = z_origen + self.altura_segura_mm
        z_segura_destino = z_destino + self.altura_segura_mm

        self._enviar_comando(f"MovJ({x_origen},{y_origen},{z_segura_origen},0,0,0)")
        self._enviar_comando(f"MovL({x_origen},{y_origen},{z_origen},0,0,0)")
        self._enviar_comando(f"DO({self.pin_efector_do},1)")
        self._enviar_comando(f"MovL({x_origen},{y_origen},{z_segura_origen},0,0,0)")
        self._enviar_comando(f"MovJ({x_destino},{y_destino},{z_segura_destino},0,0,0)")
        self._enviar_comando(f"MovL({x_destino},{y_destino},{z_destino},0,0,0)")
        self._enviar_comando(f"DO({self.pin_efector_do},0)")
        self._enviar_comando(f"MovL({x_destino},{y_destino},{z_segura_destino},0,0,0)")
