"""Pinza DH PGE-50-26: control por Modbus contra una pinza y un controlador de mentira (sin hardware)."""
import re

import pytest

from backend.servicios.brazo.cliente_dobot import ErrorDobot, RespuestaDobot
from backend.servicios.brazo.pinza_dh import (
    AGARRE_EN_MOVIMIENTO,
    AGARRE_LLEGO,
    PinzaDH,
    PinzaNoResponde,
    ancho_mm_para_posicion,
    posicion_para_ancho_mm,
)


class ClienteConPinzaFalsa:
    """Imita al `ClienteDobot` hablando con una pinza: registros Modbus en un diccionario y movimiento en unos pocos sondeos."""

    def __init__(self, responde: bool = True, sondeos_en_movimiento: int = 2, lecturas_con_estado_viejo: int = 0):
        self.lecturas_con_estado_viejo = lecturas_con_estado_viejo
        self._viejas = 0
        self.responde = responde
        self.sondeos_en_movimiento = sondeos_en_movimiento
        self.comandos: list[str] = []
        self.registros = {0x0100: 0, 0x0101: 100, 0x0103: 1000, 0x0104: 100, 0x0200: 0, 0x0201: 1, 0x0202: 926}
        self._destino: int | None = None
        self._restantes = 0

    def enviar(self, comando: str) -> RespuestaDobot:
        self.comandos.append(comando)
        if comando.startswith("SetTool485") or comando.startswith("ModbusClose"):
            return RespuestaDobot(0, "", comando)
        if comando.startswith("ModbusCreate"):
            return RespuestaDobot(0, "0", comando)
        if not self.responde:
            raise ErrorDobot(f"{comando} -> ErrorID -1")
        lectura = re.match(r"GetHoldRegs\((\d+),(\d+),(\d+)\)", comando)
        if lectura:
            direccion, cantidad = int(lectura.group(2)), int(lectura.group(3))
            if self._destino is not None and direccion <= 0x0201 < direccion + cantidad:
                if self._viejas > 0:  # el controlador todavía informa el estado del movimiento anterior
                    self._viejas -= 1
                    self.registros[0x0201] = AGARRE_EN_MOVIMIENTO if self._viejas == 0 else self.registros[0x0201]
                else:
                    self._avanzar()
            return RespuestaDobot(0, ",".join(str(self.registros[direccion + k]) for k in range(cantidad)), comando)
        escritura = re.match(r"SetHoldRegs\((\d+),(\d+),1,\{(\d+)\}\)", comando)
        direccion, valor = int(escritura.group(2)), int(escritura.group(3))
        self.registros[direccion] = valor
        if direccion == 0x0100:  # inicializar: queda inicializada y vuelve a los valores de fábrica
            self.registros.update({0x0200: 1, 0x0101: 100, 0x0104: 100, 0x0202: 1000})
        if direccion == 0x0103:
            self._destino, self._restantes = valor, self.sondeos_en_movimiento
            self._viejas = self.lecturas_con_estado_viejo
            if self._viejas == 0:
                self.registros[0x0201] = AGARRE_EN_MOVIMIENTO
        return RespuestaDobot(0, "", comando)

    def _avanzar(self) -> None:
        if self._restantes > 0:
            self._restantes -= 1
            return
        self.registros[0x0202], self.registros[0x0201], self._destino = self._destino, AGARRE_LLEGO, None


def _pinza(**kwargs) -> tuple[PinzaDH, ClienteConPinzaFalsa]:
    cliente = ClienteConPinzaFalsa(**kwargs)
    pinza = PinzaDH(cliente)
    pinza.conectar()
    return pinza, cliente


def test_conectar_fija_el_rs485_y_abre_el_canal_interno_del_controlador() -> None:
    _, cliente = _pinza()

    assert cliente.comandos == ['SetTool485(115200,"N",1)', 'ModbusCreate("127.0.0.1",60000,1,1)']


def test_sin_conectar_da_error_claro() -> None:
    with pytest.raises(RuntimeError, match="conectar"):
        PinzaDH(ClienteConPinzaFalsa()).estado()


def test_lee_el_estado() -> None:
    pinza, _ = _pinza()

    estado = pinza.estado()

    assert (estado.inicializada, estado.agarre, estado.posicion) == (False, 1, 926)


def test_inicializar_vuelve_a_fijar_fuerza_y_velocidad_bajas() -> None:
    pinza, cliente = _pinza()

    pinza.inicializar()

    assert cliente.registros[0x0200] == 1
    assert cliente.registros[0x0101] == 20 and cliente.registros[0x0104] == 20  # la inicialización las había dejado en 100


def test_recalibrar_escribe_0xA5() -> None:
    pinza, cliente = _pinza()

    pinza.inicializar(recalibrar=True)

    assert any(c.endswith(f",{0x0100},1,{{165}})") for c in cliente.comandos)


def test_mover_espera_a_que_llegue_y_devuelve_el_estado() -> None:
    pinza, cliente = _pinza(sondeos_en_movimiento=3)
    pinza.inicializar()

    estado = pinza.cerrar()

    assert (estado.agarre, estado.posicion) == (AGARRE_LLEGO, 0)
    assert cliente.registros[0x0103] == 0


def test_no_da_por_terminado_el_movimiento_con_el_llegó_del_movimiento_anterior() -> None:
    pinza, cliente = _pinza(sondeos_en_movimiento=2, lecturas_con_estado_viejo=4)  # el estado viejo dura más de 0,15 s
    pinza.inicializar()
    cliente.registros[0x0201] = AGARRE_LLEGO

    estado = pinza.cerrar()

    assert estado.posicion == 0 and cliente.registros[0x0202] == 0  # esperó a que de verdad llegara


def test_abrir_va_a_1000() -> None:
    pinza, _ = _pinza()
    pinza.inicializar()
    pinza.cerrar()

    assert pinza.abrir().posicion == 1000


def test_rechaza_posiciones_fuerzas_y_velocidades_fuera_de_rango() -> None:
    pinza, _ = _pinza()

    with pytest.raises(ValueError):
        pinza.mover_a(1001)
    with pytest.raises(ValueError):
        pinza.mover_a(-1)
    with pytest.raises(ValueError):
        PinzaDH(ClienteConPinzaFalsa(), fuerza=10)  # la pinza no admite menos de 20 %
    with pytest.raises(ValueError):
        PinzaDH(ClienteConPinzaFalsa(), fuerza=101)
    with pytest.raises(ValueError):
        PinzaDH(ClienteConPinzaFalsa(), velocidad=0)


def test_si_la_pinza_no_responde_da_un_error_propio() -> None:
    pinza, cliente = _pinza()
    cliente.responde = False

    with pytest.raises(PinzaNoResponde):
        pinza.estado()
    with pytest.raises(PinzaNoResponde):
        pinza.mover_a(500)


def test_si_nunca_termina_de_moverse_da_error_de_tiempo() -> None:
    pinza, _ = _pinza(sondeos_en_movimiento=10_000)

    with pytest.raises(PinzaNoResponde, match="no terminó"):
        pinza.mover_a(0, limite_segundos=0.5)


def test_desconectar_libera_el_maestro_modbus() -> None:
    pinza, cliente = _pinza()

    pinza.desconectar()

    assert cliente.comandos[-1] == "ModbusClose(0)"
    with pytest.raises(RuntimeError):
        pinza.estado()


def test_conversion_entre_ancho_en_mm_y_posicion() -> None:
    assert posicion_para_ancho_mm(26.0) == 1000 and posicion_para_ancho_mm(0) == 0 and posicion_para_ancho_mm(13.0) == 500
    assert ancho_mm_para_posicion(500) == pytest.approx(13.0)
    with pytest.raises(ValueError):
        posicion_para_ancho_mm(30.0)
    with pytest.raises(ValueError):
        posicion_para_ancho_mm(-1.0)
