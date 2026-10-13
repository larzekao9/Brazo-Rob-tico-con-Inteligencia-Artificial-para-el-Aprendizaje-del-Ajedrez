"""Prueba de conexión de solo lectura al Dobot, contra un servidor falso que imita al controlador."""
import socket
import threading

import pytest

from scripts.probar_conexion_dobot import COMANDOS_DE_LECTURA, consultar, interpretar_respuesta


class ControladorFalso:
    """Servidor TCP que responde como el dashboard del Dobot y registra qué comandos recibió."""

    def __init__(self, respuestas: dict[str, str]) -> None:
        self.recibidos: list[str] = []
        self._respuestas = respuestas
        self._servidor = socket.socket()
        self._servidor.bind(("127.0.0.1", 0))
        self._servidor.listen(1)
        self.puerto = self._servidor.getsockname()[1]
        threading.Thread(target=self._atender, daemon=True).start()

    def _atender(self) -> None:
        conexion, _ = self._servidor.accept()
        with conexion:
            while True:
                datos = conexion.recv(1024)
                if not datos:
                    break
                comando = datos.decode("ascii")
                self.recibidos.append(comando)
                conexion.sendall(self._respuestas.get(comando, f"-10000,{{}},{comando};").encode("ascii"))
        self._servidor.close()


def test_interpreta_una_respuesta_exitosa() -> None:
    r = interpretar_respuesta("0,{5},RobotMode();")

    assert r["error_id"] == 0 and r["valores"] == "5" and r["comando"] == "RobotMode()"


def test_interpreta_una_posicion_con_varios_valores() -> None:
    r = interpretar_respuesta("0,{300.5,-20.0,150.0,0.0,0.0,90.0},GetPose();")

    assert r["error_id"] == 0 and r["valores"].split(",")[0] == "300.5" and len(r["valores"].split(",")) == 6


def test_interpreta_el_error_de_modo_de_control() -> None:
    r = interpretar_respuesta("Control Mode Is Not Tcp")

    assert r["error_id"] is None and "Not Tcp" in r["texto"]


def test_consultar_pide_solo_los_comandos_de_lectura() -> None:
    controlador = ControladorFalso({"RobotMode()": "0,{5},RobotMode();", "GetPose()": "0,{1,2,3,4,5,6},GetPose();"})

    resultados = consultar("127.0.0.1", controlador.puerto, timeout=2)

    assert controlador.recibidos == list(COMANDOS_DE_LECTURA)
    assert resultados["RobotMode()"]["valores"] == "5"
    assert resultados["GetAngle()"]["error_id"] == -10000  # el falso responde "no encontrado"


@pytest.mark.parametrize("peligroso", ["EnableRobot()", "MovJ(1,2,3,0,0,0)", "MovL(1,2,3,0,0,0)", "DO(1,1)", "PowerOn()"])
def test_se_niega_a_enviar_cualquier_comando_que_mueva_o_habilite(peligroso: str) -> None:
    with pytest.raises(ValueError):
        consultar("127.0.0.1", 9, comandos=(peligroso,))  # falla antes de abrir ninguna conexión


def test_si_no_hay_controlador_falla_con_un_error_de_red() -> None:
    puerto_libre = socket.socket()
    puerto_libre.bind(("127.0.0.1", 0))
    puerto = puerto_libre.getsockname()[1]
    puerto_libre.close()

    with pytest.raises(OSError):
        consultar("127.0.0.1", puerto, timeout=1)
