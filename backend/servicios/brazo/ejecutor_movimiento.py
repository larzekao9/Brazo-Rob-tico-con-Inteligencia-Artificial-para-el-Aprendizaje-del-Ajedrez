"""Patrón Strategy: intercambia quién ejecuta el movimiento físico de una
jugada (simulado en PyBullet o real contra el Dobot CR5AS) sin que el resto
del backend lo note (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1; HU9).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import chess

from backend.servicios.brazo.calibracion_brazo import ParametrosAgarre
from backend.servicios.brazo.cliente_dobot import ClienteDobot
from backend.servicios.brazo.pinza_dh import AGARRE_SOSTIENE, POSICION_ABIERTA, PinzaDH


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


class PiezaNoAgarrada(RuntimeError):
    """La pinza cerró y no sintió ninguna pieza (cerró en el aire) o se le cayó mientras la subía."""


class EjecutorReal(EjecutorMovimiento):
    """Mueve una pieza con el brazo físico real, un Dobot CR5AS con la pinza DH PGE-50-26, por TCP/IP.

    Usa `ClienteDobot` (comandos del controlador V4 y espera a que termine cada movimiento) y `PinzaDH` (la pinza por Modbus).
    Secuencia de una jugada sin captura, a baja velocidad, con los dedos girados en diagonal (`ParametrosAgarre`):
    abre la pinza a la apertura de aproximación, va sobre la casilla de origen a altura segura, baja hasta 3 mm del tablero, cierra
    hasta sentir la pieza (agarre = 2), sube y comprueba que la sigue sosteniendo, se traslada a altura segura, baja, suelta, sube y
    vuelve a la posición cero. Si la pinza no agarró nada, la abre, sube y lanza `PiezaNoAgarrada`.

    Requisitos antes de mover (falla de forma explícita si falta alguno, nunca inventa valores):
    - `posiciones_casillas` (calibración del tablero), `orientacion` `(rx, ry, rz)` de la herramienta y `parametros.z_tope`.
    - el brazo encendido y habilitado en modo TCP, y la pinza inicializada (`conectar()` la inicializa si hace falta).

    Todavía no resuelve capturas (retirar la pieza del destino), enroque, captura al paso ni coronación.
    """

    def __init__(
        self,
        host: str,
        puerto_dashboard: int = 29999,
        timeout_segundos: float = 5.0,
        posiciones_casillas: dict[str, tuple[float, float, float]] | None = None,
        orientacion: tuple[float, float, float] | None = None,
        angulos_cero: tuple[float, ...] | None = None,
        velocidad_global: int = 20,
        parametros: ParametrosAgarre | None = None,
        cliente: ClienteDobot | None = None,
        pinza: PinzaDH | None = None,
    ):
        """
        Args:
            host: IP del controlador del Dobot (192.168.5.1 de fábrica en LAN 1).
            posiciones_casillas: resultado de `calcular_posiciones_casillas`; solo se usan X e Y (la altura sale de `parametros`).
            orientacion: `(rx, ry, rz)` de la herramienta con la pinza apuntando al tablero; al `rz` se le suma el giro en diagonal.
            angulos_cero: ángulos de la posición cero, adonde vuelve al terminar. `None` = no vuelve.
            velocidad_global: `SpeedFactor` al conectar (1 a 100); bajo por seguridad.
            parametros: alturas, giro y apertura de agarre (ver `ParametrosAgarre`).
            cliente, pinza: ya armados (para pruebas); si no, se crean con `host`.
        """
        self.parametros = parametros or ParametrosAgarre()
        self.cliente = cliente or ClienteDobot(host, puerto_dashboard, timeout_segundos, velocidad_global)
        self.pinza = pinza or PinzaDH(self.cliente, self.parametros.fuerza, self.parametros.velocidad_pinza)
        self.posiciones_casillas = posiciones_casillas
        self.orientacion = orientacion
        self.angulos_cero = angulos_cero

    def conectar(self, inicializar_pinza: bool = True) -> None:
        """Abre la conexión con el brazo y con la pinza, y la inicializa si hace falta (los dedos se mueven unos segundos: libres)."""
        self.cliente.conectar()
        self.pinza.conectar()
        if inicializar_pinza and not self.pinza.estado().inicializada:
            self.pinza.inicializar()

    def desconectar(self) -> None:
        """Cierra las conexiones (el brazo queda habilitado, como estaba)."""
        self.pinza.desconectar()
        self.cliente.cerrar()

    def _pose(self, casilla: str, sobre_mm: float = 0.0) -> tuple[float, ...]:
        """Pose de la herramienta sobre `casilla`: altura de agarre más `sobre_mm`, con el giro en diagonal."""
        x, y, _ = self.posiciones_casillas[casilla]
        rx, ry, rz = self.orientacion
        return (x, y, self.parametros.z_agarre + sobre_mm, rx, ry, rz + self.parametros.giro_diagonal_grados)

    def bajar_a(self, casilla: str, tipo_pieza: str = "p") -> None:
        """Baja con la pinza abierta (a la apertura de aproximación de `tipo_pieza`) hasta la altura de agarre sobre `casilla`, sin cerrarla.

        Sirve para ver si los dedos quedan bien centrados alrededor de la pieza antes de probar un agarre. Se sube con `subir_de`.
        """
        self.pinza.mover_a(self.parametros.apertura_para(tipo_pieza))
        self.cliente.mover_a_pose(self._pose(casilla, self.parametros.altura_segura_mm))
        self.cliente.mover_a_pose(self._pose(casilla), lineal=True)

    def subir_de(self, casilla: str, tipo_pieza: str = "p") -> None:
        """Sube a altura segura sobre `casilla` con la pinza abierta (el paso inverso de `bajar_a`)."""
        self._retirarse(casilla, self.parametros.apertura_para(tipo_pieza))

    def _retirarse(self, casilla: str, apertura: int) -> None:
        """Deja la pinza abierta a `apertura` y sube a altura segura, para no arrastrar piezas si algo salió mal."""
        self.pinza.mover_a(apertura)
        self.cliente.mover_a_pose(self._pose(casilla, self.parametros.altura_segura_mm), lineal=True)

    def ejecutar_movimiento(self, tablero_antes: chess.Board, jugada: chess.Move) -> None:
        """Mueve la pieza de `jugada` (sin captura) y deja el brazo en la posición cero.

        Raises:
            RuntimeError: si falta la calibración, la orientación o la altura del tablero, o la pinza no está inicializada.
            NotImplementedError: si `jugada` captura una pieza (retirar la capturada es el siguiente paso).
            PiezaNoAgarrada: si la pinza cierra sin sentir una pieza o la pierde al subirla.
        """
        if self.posiciones_casillas is None:
            raise RuntimeError("No se cargó la calibración del tablero todavía — llamá calcular_posiciones_casillas() con puntos medidos primero.")
        if self.orientacion is None:
            raise RuntimeError("Falta la orientación (rx, ry, rz) de la herramienta: tomala de GetPose() con la pinza apuntando al tablero.")
        _ = self.parametros.z_agarre  # falla con un mensaje claro si falta la altura del tablero
        if tablero_antes.is_capture(jugada):
            raise NotImplementedError("Retirar piezas capturadas del tablero físico es el siguiente paso, no implementado todavía.")
        self.parametros.apertura_para(tablero_antes.piece_at(jugada.from_square).symbol())  # falla si falta medirla
        if not self.pinza.estado().inicializada:
            raise RuntimeError("La pinza no está inicializada: llamá a conectar() o a pinza.inicializar() antes de mover piezas.")

        origen = chess.square_name(jugada.from_square)
        destino = chess.square_name(jugada.to_square)
        seguro = self.parametros.altura_segura_mm
        apertura = self.parametros.apertura_para(tablero_antes.piece_at(jugada.from_square).symbol())

        self.pinza.mover_a(apertura)
        self.cliente.mover_a_pose(self._pose(origen, seguro))
        self.cliente.mover_a_pose(self._pose(origen), lineal=True)
        cierre = self.pinza.cerrar()
        if cierre.agarre != AGARRE_SOSTIENE:
            self._retirarse(origen, apertura)
            raise PiezaNoAgarrada(
                f"La pinza cerró en {origen} y no sintió ninguna pieza (agarre={cierre.agarre}, posición={cierre.posicion}): "
                "¿está en esa casilla?"
            )
        self.cliente.mover_a_pose(self._pose(origen, seguro), lineal=True)
        if self.pinza.estado().agarre != AGARRE_SOSTIENE:
            self._retirarse(origen, apertura)
            raise PiezaNoAgarrada(f"Se le cayó la pieza de {origen} al subirla")
        self.cliente.mover_a_pose(self._pose(destino, seguro), lineal=True)
        self.cliente.mover_a_pose(self._pose(destino), lineal=True)
        self.pinza.mover_a(min(POSICION_ABIERTA, apertura + self.parametros.apertura_extra_soltar))  # soltar, más abierta que al agarrar
        self.cliente.mover_a_pose(self._pose(destino, seguro), lineal=True)
        if self.angulos_cero is not None:
            self.cliente.mover_a_angulos(self.angulos_cero)
