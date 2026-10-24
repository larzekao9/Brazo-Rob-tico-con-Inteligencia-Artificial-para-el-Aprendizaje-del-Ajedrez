"""Pinza eléctrica DH Robotics PGE-50-26 (versión para Dobot), controlada por Modbus RTU a través del controlador del brazo.

La pinza está en el conector de la herramienta (RS485). Desde el controlador V4 se llega con un maestro Modbus a `127.0.0.1:60000` en
modo RTU (el canal interno hacia ese RS485), no con `ModbusRTUCreate`, que habla con otro puerto y no recibe respuesta. Primero hay que
fijar el RS485 de la herramienta (`SetTool485`). Valores de fábrica de la pinza: ID 1, 115200 baudios, 8 bits, 1 de parada, sin paridad.

Registros (manual "PGE Series Internal Controller Short Manual", versión 3.1):
    0x0100 inicializar (1 = volver al cero, 0xA5 = recalibrar)   0x0200 estado de inicialización (0 no, 1 sí)
    0x0101 fuerza, 20 a 100 %                                    0x0201 agarre (0 moviéndose, 1 llegó, 2 sostiene un objeto, 3 se cayó)
    0x0103 posición, 0 a 1000 (milésimas del recorrido)          0x0202 posición actual
    0x0104 velocidad, 1 a 100 %

La inicialización devuelve la fuerza y la velocidad a 100 %: hay que volver a fijarlas después (`inicializar` lo hace). Con dedos
nuevos hay que recalibrar con 0xA5 (`recalibrar`), porque cambia el recorrido.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from backend.servicios.brazo.cliente_dobot import ClienteDobot, ErrorDobot

REG_INICIALIZAR = 0x0100
REG_FUERZA = 0x0101
REG_POSICION = 0x0103
REG_VELOCIDAD = 0x0104
REG_ESTADO_INICIALIZACION = 0x0200
REG_ESTADO_AGARRE = 0x0201
REG_POSICION_ACTUAL = 0x0202

ESPERA_ESTADO_VIEJO_SEGUNDOS = 1.0
"""Cuánto se espera a ver la pinza moverse antes de dar por buena una lectura de "llegó" (si ya estaba en el destino, nunca se mueve)."""
AGARRE_EN_MOVIMIENTO, AGARRE_LLEGO, AGARRE_SOSTIENE, AGARRE_SE_CAYO = 0, 1, 2, 3
POSICION_ABIERTA, POSICION_CERRADA = 1000, 0
CARRERA_MM = 26.0
"""Recorrido total entre dedos de la PGE-50-26 (ficha técnica). Solo vale con los dedos de fábrica y es una aproximación lineal."""


CAUSAS_SIN_RESPUESTA = (
    "Revisá que la pinza esté encendida (24 V en la herramienta del brazo), el cable del RS485 de la herramienta y que la pinza siga con "
    "ID 1 y 115200 baudios; después tocá «Inicializar pinza»."
)


def _causas(error: Exception) -> str:
    """Las causas probables de que la pinza no conteste, salvo que el motivo sea una parada del usuario (ahí no hay nada que revisar)."""
    return "" if "Cancelado por el usuario" in str(error) else f" {CAUSAS_SIN_RESPUESTA}"


class PinzaNoResponde(ErrorDobot):
    """La pinza no contestó o no llegó a la posición pedida a tiempo."""


@dataclass
class EstadoPinza:
    """Lectura de los registros de estado."""

    inicializada: bool
    agarre: int
    posicion: int


def posicion_para_ancho_mm(ancho_mm: float, carrera_mm: float = CARRERA_MM) -> int:
    """Posición (0 a 1000) que da una apertura de `ancho_mm` entre los dedos, suponiendo el recorrido lineal.

    Es una estimación: conviene comprobarla midiendo con una regla y corregir `carrera_mm` si hace falta.

    Raises:
        ValueError: si el ancho está fuera del recorrido de la pinza.
    """
    if not 0 <= ancho_mm <= carrera_mm:
        raise ValueError(f"El ancho {ancho_mm} mm está fuera del recorrido de la pinza (0 a {carrera_mm} mm)")
    return round(ancho_mm / carrera_mm * 1000)


def ancho_mm_para_posicion(posicion: int, carrera_mm: float = CARRERA_MM) -> float:
    """Apertura estimada, en mm, para una posición de 0 a 1000 (inversa de `posicion_para_ancho_mm`)."""
    return posicion / 1000 * carrera_mm


class PinzaDH:
    """Control de la pinza a través de un `ClienteDobot` ya conectado (modo TCP, brazo habilitado)."""

    def __init__(self, cliente: ClienteDobot, fuerza: int = 20, velocidad: int = 20, id_esclavo: int = 1, baudios: int = 115200):
        """`fuerza` y `velocidad` son porcentajes; arrancan bajos a propósito (la fuerza máxima podría marcar o romper una pieza)."""
        self._validar(fuerza, 20, 100, "fuerza")
        self._validar(velocidad, 1, 100, "velocidad")
        self.cliente, self.fuerza, self.velocidad = cliente, fuerza, velocidad
        self.id_esclavo, self.baudios = id_esclavo, baudios
        self._maestro: int | None = None

    @staticmethod
    def _validar(valor: int, minimo: int, maximo: int, nombre: str) -> None:
        if not minimo <= valor <= maximo:
            raise ValueError(f"{nombre} debe estar entre {minimo} y {maximo}, no {valor}")

    # --- comunicación -----------------------------------------------------------------------------------------------
    def conectar(self) -> None:
        """Fija el RS485 de la herramienta y abre el canal Modbus hacia la pinza."""
        self.cliente.enviar(f'SetTool485({self.baudios},"N",1)')
        respuesta = self.cliente.enviar(f'ModbusCreate("127.0.0.1",60000,{self.id_esclavo},1)')
        self._maestro = int(float(respuesta.valores))

    def desconectar(self) -> None:
        """Libera el maestro Modbus (el controlador admite solo 5 a la vez)."""
        if self._maestro is not None:
            try:
                self.cliente.enviar(f"ModbusClose({self._maestro})")
            finally:
                self._maestro = None

    def _reabrir(self) -> None:
        """Vuelve a crear el canal Modbus (suelta el maestro anterior y repite `SetTool485` y `ModbusCreate`).

        Sirve cuando el controlador perdió el canal (reinicio del RS485, un maestro viejo que se cerró solo): se nota como `ErrorID -1` al leer.
        """
        if self._maestro is not None:
            try:
                self.cliente.enviar(f"ModbusClose({self._maestro})")
            except ErrorDobot:
                pass
            self._maestro = None
        self.conectar()

    def _con_reintento(self, comando) -> object:
        """Ejecuta `comando()` (usa el maestro vigente); si el controlador devuelve error, renueva el canal Modbus y lo intenta una vez más."""
        try:
            return comando()
        except ErrorDobot:
            if getattr(self.cliente, "cancelado", False):  # el usuario paró el brazo: no se insiste ni se toca el canal
                raise
            self._reabrir()
            return comando()

    def _requiere_conexion(self) -> int:
        if self._maestro is None:
            raise RuntimeError("La pinza no está conectada: llamá a conectar() primero")
        return self._maestro

    def leer(self, direccion: int, cantidad: int = 1) -> list[int]:
        """Lee `cantidad` registros desde `direccion`. Lanza `PinzaNoResponde` si el controlador devuelve error."""
        try:
            respuesta = self._con_reintento(lambda: self.cliente.enviar(f"GetHoldRegs({self._requiere_conexion()},{direccion},{cantidad})"))
        except ErrorDobot as error:
            raise PinzaNoResponde(f"La pinza no contestó al leer 0x{direccion:04X}: {error}.{_causas(error)}") from error
        return [int(float(v)) for v in respuesta.valores.split(",") if v.strip()]

    def escribir(self, direccion: int, valor: int) -> None:
        """Escribe un registro. Lanza `PinzaNoResponde` si el controlador devuelve error."""
        try:
            self._con_reintento(lambda: self.cliente.enviar(f"SetHoldRegs({self._requiere_conexion()},{direccion},1,{{{int(valor)}}})"))
        except ErrorDobot as error:
            raise PinzaNoResponde(f"La pinza no aceptó la escritura en 0x{direccion:04X}: {error}.{_causas(error)}") from error

    def estado(self) -> EstadoPinza:
        """Estado actual: inicializada, agarre y posición."""
        inicializada, agarre, posicion = self.leer(REG_ESTADO_INICIALIZACION, 3)
        return EstadoPinza(bool(inicializada), agarre, posicion)

    # --- operaciones ------------------------------------------------------------------------------------------------
    def inicializar(self, limite_segundos: float = 10.0, recalibrar: bool = False) -> None:
        """Inicializa la pinza (se mueve unos segundos: dedos libres) y deja la fuerza y la velocidad configuradas.

        Con `recalibrar=True` escribe 0xA5, que mide de nuevo el recorrido: necesario al cambiar los dedos.
        """
        self.escribir(REG_INICIALIZAR, 0xA5 if recalibrar else 1)
        inicio = time.monotonic()
        while self.leer(REG_ESTADO_INICIALIZACION)[0] != 1:
            if time.monotonic() - inicio > limite_segundos:
                raise PinzaNoResponde("La pinza no terminó de inicializarse a tiempo")
            time.sleep(0.2)
        self.escribir(REG_FUERZA, self.fuerza)  # la inicialización los devuelve a 100 %
        self.escribir(REG_VELOCIDAD, self.velocidad)

    def mover_a(self, posicion: int, limite_segundos: float = 6.0) -> EstadoPinza:
        """Va a `posicion` (0 cerrada, 1000 abierta) y espera a que termine el movimiento. Devuelve el estado final.

        El estado de agarre dice si llegó (1), si quedó sosteniendo un objeto (2) o si se le cayó (3).
        """
        self._validar(posicion, 0, 1000, "posición")
        self.escribir(REG_POSICION, posicion)
        inicio = time.monotonic()
        se_vio_moverse = False
        while time.monotonic() - inicio < limite_segundos:
            time.sleep(0.1)
            estado = self.estado()
            if estado.agarre == AGARRE_EN_MOVIMIENTO:
                se_vio_moverse = True
            # El estado tarda en pasar a "moviéndose": hasta que se lo ve moverse (o pasa un rato, si ya estaba en destino) el
            # "llegó" que lee es el del movimiento anterior y no vale.
            elif se_vio_moverse or time.monotonic() - inicio > ESPERA_ESTADO_VIEJO_SEGUNDOS:
                return estado
        raise PinzaNoResponde(f"La pinza no terminó de moverse a {posicion} en {limite_segundos} s")

    def abrir(self) -> EstadoPinza:
        """Abre del todo."""
        return self.mover_a(POSICION_ABIERTA)

    def cerrar(self) -> EstadoPinza:
        """Cierra del todo (con una pieza entre los dedos queda en `AGARRE_SOSTIENE`)."""
        return self.mover_a(POSICION_CERRADA)

    def abrir_a_ancho_mm(self, ancho_mm: float) -> EstadoPinza:
        """Abre hasta `ancho_mm` entre los dedos (estimación lineal, ver `posicion_para_ancho_mm`)."""
        return self.mover_a(posicion_para_ancho_mm(ancho_mm))
