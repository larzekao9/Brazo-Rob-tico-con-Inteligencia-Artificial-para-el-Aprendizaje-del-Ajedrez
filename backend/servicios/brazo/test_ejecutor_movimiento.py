import chess
import pytest

from backend.servicios.brazo.calibracion_tablero import (
    PuntoCalibracion,
    calcular_posiciones_casillas,
)
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal

HOST_DOCUMENTACION = "192.0.2.1"

PUNTOS_CALIBRACION_SINTETICOS = [
    PuntoCalibracion(casilla="a1", x=0.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="h1", x=700.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="a8", x=0.0, y=700.0, z=10.0),
]


class ClienteFalso:
    """Reemplaza a `ClienteDobot`: anota lo que se le pide en orden, sin red ni brazo."""

    def __init__(self) -> None:
        self.llamadas: list[tuple] = []

    def mover_a_pose(self, pose, lineal=False, **_):
        self.llamadas.append(("MovL" if lineal else "MovJ", tuple(pose)))

    def mover_a_angulos(self, angulos, **_):
        self.llamadas.append(("joint", tuple(angulos)))

    def enviar(self, comando):
        self.llamadas.append(("enviar", comando))

    def esperar_fin(self, **_):
        self.llamadas.append(("esperar",))

    def conectar(self):
        self.llamadas.append(("conectar",))

    def cerrar(self):
        self.llamadas.append(("cerrar",))


def _ejecutor(**kwargs) -> tuple[EjecutorReal, ClienteFalso]:
    cliente = ClienteFalso()
    posiciones = calcular_posiciones_casillas(PUNTOS_CALIBRACION_SINTETICOS)
    kwargs.setdefault("posiciones_casillas", posiciones)
    kwargs.setdefault("orientacion", (180.0, 0.0, 90.0))
    return EjecutorReal(host=HOST_DOCUMENTACION, cliente=cliente, **kwargs), cliente


def test_ejecutor_real_sin_calibracion_lanza_runtime_error():
    ejecutor, _ = _ejecutor(posiciones_casillas=None)
    ejecutor.posiciones_casillas = None
    tablero_antes = chess.Board()

    with pytest.raises(RuntimeError, match="calibración"):
        ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e2e4"))


def test_ejecutor_real_sin_orientacion_lanza_runtime_error():
    ejecutor, cliente = _ejecutor()
    ejecutor.orientacion = None
    tablero_antes = chess.Board()

    with pytest.raises(RuntimeError, match="orientación"):
        ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e2e4"))
    assert cliente.llamadas == []  # no movió nada


def test_ejecutor_real_con_captura_lanza_not_implemented_error():
    ejecutor, cliente = _ejecutor()
    tablero_antes = chess.Board()
    tablero_antes.push_san("e4")
    tablero_antes.push_san("d5")

    with pytest.raises(NotImplementedError):
        ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e4d5"))
    assert cliente.llamadas == []


def test_ejecutor_real_secuencia_de_una_jugada_sin_captura():
    ejecutor, cliente = _ejecutor(altura_segura_mm=50.0, pin_efector_do=1)
    tablero_antes = chess.Board()

    ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e2e4"))

    movimientos = [(l[0], l[1]) for l in cliente.llamadas if l[0] in ("MovJ", "MovL")]
    assert [m[0] for m in movimientos] == ["MovJ", "MovL", "MovL", "MovJ", "MovL", "MovL"]
    efector = [l[1] for l in cliente.llamadas if l[0] == "enviar"]
    assert efector == ["DO(1,1)", "DO(1,0)"]
    # La orientación de la herramienta es siempre la medida, nunca un valor inventado.
    assert all(m[1][3:] == (180.0, 0.0, 90.0) for m in movimientos)
    # Sube a altura segura antes de trasladarse y baja hasta la casilla para agarrar y soltar.
    z = [m[1][2] for m in movimientos]
    assert z[0] == z[2] == z[3] == z[5] == 10.0 + 50.0 and z[1] == z[4] == 10.0


def test_ejecutor_real_vuelve_a_la_posicion_cero_si_hay_angulos():
    cero = (303.8, -1.1, -83.3, 6.1, 16.0, 227.0)
    ejecutor, cliente = _ejecutor(angulos_cero=cero)
    tablero_antes = chess.Board()

    ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e2e4"))

    assert cliente.llamadas[-1] == ("joint", cero)


def test_ejecutor_real_espera_a_que_el_efector_actue_antes_de_seguir():
    ejecutor, cliente = _ejecutor()
    tablero_antes = chess.Board()

    ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e2e4"))

    posiciones_do = [i for i, l in enumerate(cliente.llamadas) if l[0] == "enviar"]
    assert all(cliente.llamadas[i + 1] == ("esperar",) for i in posiciones_do)


def test_ejecutor_real_conectar_y_desconectar_delegan_en_el_cliente():
    ejecutor, cliente = _ejecutor()

    ejecutor.conectar()
    ejecutor.desconectar()

    assert cliente.llamadas == [("conectar",), ("cerrar",)]


pytest.importorskip("pybullet")
from backend.servicios.brazo.ejecutor_movimiento import EjecutorSimulado


def test_ejecutor_simulado_ejecuta_movimiento_legal_y_actualiza_tablero():
    ejecutor = EjecutorSimulado(modo_gui=False)
    try:
        tablero_antes = chess.Board()
        jugada = tablero_antes.parse_uci("e2e4")

        ejecutor.ejecutar_movimiento(tablero_antes, jugada)

        assert "e4" in ejecutor.piezas
        assert "e2" not in ejecutor.piezas
        assert len(ejecutor.piezas) == 32
        # el tablero que pasó el llamador no se muta ni queda referenciado
        # como estado interno del ejecutor (fix de sincronización).
        assert tablero_antes.fen() == chess.STARTING_FEN
    finally:
        ejecutor.cerrar()


def test_ejecutor_simulado_dos_jugadas_de_estrategia_no_consecutivas_no_se_desincroniza():
    # Reproduce el escenario real: el ejecutor solo recibe la jugada de la
    # estrategia (nunca la del humano) — dos llamadas sucesivas representan
    # la 2da y 4ta jugada real de la partida, con jugadas del humano en el
    # medio que el ejecutor nunca vio. Con un tablero interno acumulado
    # (el bug original) esto se desincronizaba; con `tablero_antes` pasado
    # en cada llamada, cada una es independiente y correcta.
    ejecutor = EjecutorSimulado(modo_gui=False)
    try:
        tablero_1 = chess.Board()
        tablero_1.push_san("e4")
        tablero_1.push_san("e5")
        jugada_1 = tablero_1.parse_uci("g1f3")
        ejecutor.ejecutar_movimiento(tablero_1, jugada_1)

        tablero_2 = tablero_1.copy()
        tablero_2.push(jugada_1)
        tablero_2.push_san("Nc6")
        jugada_2 = tablero_2.parse_uci("f1c4")
        ejecutor.ejecutar_movimiento(tablero_2, jugada_2)

        assert "c4" in ejecutor.piezas
        assert "f1" not in ejecutor.piezas
        assert "f3" in ejecutor.piezas
    finally:
        ejecutor.cerrar()
