"""Cliente del Dobot V4 contra un controlador de mentira (servidor TCP local): no toca ningún brazo."""
import socket
import threading

import pytest

from backend.servicios.brazo.cliente_dobot import ClienteDobot, ErrorDobot, interpretar_respuesta


class ControladorFalso:
    """Servidor TCP que responde como el dashboard del Dobot: registra los comandos y saca los modos de una lista."""

    def __init__(self, modos: list[int], respuestas: dict[str, str] | None = None):
        self.modos = list(modos)  # lo que va devolviendo RobotMode(); el último se repite
        self.respuestas = respuestas or {}
        self.comandos: list[str] = []
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
                    return
                comando = datos.decode()
                self.comandos.append(comando)
                conexion.sendall(self._responder(comando).encode())

    def _responder(self, comando: str) -> str:
        if comando in self.respuestas:
            return self.respuestas[comando]
        if comando == "RobotMode()":
            modo = self.modos.pop(0) if len(self.modos) > 1 else self.modos[0]
            return f"0,{{{modo}}},RobotMode();"
        if comando == "GetPose()":
            return "0,{60.5,-537.1,605.2,108,29.6,-44.6},GetPose();"
        if comando == "GetAngle()":
            return "0,{303.8,-1.1,-83.3,6.1,16,227},GetAngle();"
        return f"0,{{}},{comando};"


def _cliente(controlador: ControladorFalso, **kwargs) -> ClienteDobot:
    return ClienteDobot("127.0.0.1", controlador.puerto, timeout_segundos=2.0, **kwargs)


# --- interpretación de respuestas ------------------------------------------------------------------------------------
def test_interpreta_una_respuesta_con_valores() -> None:
    respuesta = interpretar_respuesta("0,{5},RobotMode();")

    assert (respuesta.error_id, respuesta.valores, respuesta.comando) == (0, "5", "RobotMode()")


def test_interpreta_una_respuesta_con_varios_valores_y_comando_con_comas() -> None:
    respuesta = interpretar_respuesta("0,{2},MovJ(pose={1,2,3,4,5,6},a=10,v=20);")

    assert respuesta.valores == "2" and respuesta.comando == "MovJ(pose={1,2,3,4,5,6},a=10,v=20)"


def test_una_respuesta_que_no_es_del_dashboard_da_error() -> None:
    with pytest.raises(ErrorDobot):
        interpretar_respuesta("Control Mode Is Not Tcp")


# --- conexión y lecturas ---------------------------------------------------------------------------------------------
def test_al_conectar_fija_la_velocidad_global_y_no_habilita_ni_enciende_nada() -> None:
    controlador = ControladorFalso([5])
    cliente = _cliente(controlador, velocidad_global=20)

    cliente.conectar()
    cliente.cerrar()

    assert controlador.comandos == ["RobotMode()", "SpeedFactor(20)"]


def test_no_conecta_si_el_brazo_esta_en_colision() -> None:
    controlador = ControladorFalso([11])
    cliente = _cliente(controlador)

    with pytest.raises(ErrorDobot, match="colisión"):
        cliente.conectar()
    cliente.cerrar()


def test_lee_pose_y_angulos() -> None:
    controlador = ControladorFalso([5])
    cliente = _cliente(controlador)
    cliente.conectar()

    assert cliente.pose() == (60.5, -537.1, 605.2, 108.0, 29.6, -44.6)
    assert cliente.angulos() == (303.8, -1.1, -83.3, 6.1, 16.0, 227.0)
    cliente.cerrar()


def test_un_error_id_distinto_de_cero_levanta_error() -> None:
    controlador = ControladorFalso([5], {"MovJ(pose={0,0,0,0,0,0},a=10,v=20)": "-1,{},MovJ();"})
    cliente = _cliente(controlador)
    cliente.conectar()

    with pytest.raises(ErrorDobot):
        cliente.enviar("MovJ(pose={0,0,0,0,0,0},a=10,v=20)")
    cliente.cerrar()


def test_enviar_sin_conectar_da_error_claro() -> None:
    with pytest.raises(RuntimeError, match="conectar"):
        ClienteDobot("127.0.0.1").enviar("RobotMode()")


# --- movimientos -----------------------------------------------------------------------------------------------------
def test_mover_a_pose_usa_la_sintaxis_v4_y_espera_a_que_termine() -> None:
    controlador = ControladorFalso([5, 7, 7, 5])  # conectar ve 5; el movimiento pasa por 7 y vuelve a 5
    cliente = _cliente(controlador)
    cliente.conectar()

    cliente.mover_a_pose((100, 200, 300, 180, 0, 90), lineal=True)

    assert "MovL(pose={100,200,300,180,0,90},a=10,v=20)" in controlador.comandos
    assert controlador.comandos.count("RobotMode()") >= 4  # sondeó hasta verlo libre
    cliente.cerrar()


def test_mover_a_angulos_usa_joint() -> None:
    controlador = ControladorFalso([5, 7, 5])
    cliente = _cliente(controlador)
    cliente.conectar()

    cliente.mover_a_angulos((303.8, -1.1, -83.3, 6.1, 16, 227))

    assert "MovJ(joint={303.8,-1.1,-83.3,6.1,16,227},a=10,v=20)" in controlador.comandos
    cliente.cerrar()


def test_mover_relativo_manda_un_desplazamiento_lento_en_la_base() -> None:
    controlador = ControladorFalso([5, 7, 5])
    cliente = _cliente(controlador)
    cliente.conectar()

    cliente.mover_relativo(dz=10)

    assert "RelMovLUser(0,0,10,0,0,0,user=0,a=10,speed=20)" in controlador.comandos
    cliente.cerrar()


def test_si_hay_una_colision_durante_el_movimiento_frena_y_avisa() -> None:
    controlador = ControladorFalso([5, 7, 11])
    cliente = _cliente(controlador)
    cliente.conectar()

    with pytest.raises(ErrorDobot, match="colisión"):
        cliente.mover_a_pose((1, 2, 3, 0, 0, 0))

    assert "Stop()" in controlador.comandos
    cliente.cerrar()


def test_la_pose_debe_tener_seis_valores() -> None:
    cliente = ClienteDobot("127.0.0.1")

    with pytest.raises(ValueError):
        cliente.mover_a_pose((1, 2, 3))
    with pytest.raises(ValueError):
        cliente.mover_a_angulos((1, 2, 3))


def test_robot_sin_modo_tcp_da_el_motivo_en_vez_de_un_timeout() -> None:
    """El controlador contesta `Control Mode Is Not Tcp` sin `;` final: antes el cliente esperaba hasta el timeout ("timed out")."""
    controlador = ControladorFalso([5], respuestas={"RobotMode()": "Control Mode Is Not Tcp\t"})
    cliente = ClienteDobot("127.0.0.1", controlador.puerto, timeout_segundos=3.0)
    with pytest.raises(ErrorDobot, match="modo de control TCP/IP"):
        cliente.conectar()
