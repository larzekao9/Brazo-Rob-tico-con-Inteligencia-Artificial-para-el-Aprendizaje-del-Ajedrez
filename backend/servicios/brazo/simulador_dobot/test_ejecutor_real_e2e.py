"""Una jugada completa de `EjecutorReal` (el mismo código que mueve el brazo físico) contra el simulador por TCP."""
import chess
import pytest

FEN_DE_PRUEBA = "4k3/8/8/8/8/8/3PPP2/RN2K3 w - - 0 1"
"""Pocas piezas (la física va más rápido), con vecinas del peón y del caballo para ver que no las toca."""

from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal, PiezaNoAgarrada
from backend.servicios.brazo.simulador_dobot import calibracion_ejemplo as ejemplo
from backend.servicios.brazo.simulador_dobot import cinematica
from backend.servicios.brazo.simulador_dobot.nucleo import Simulador
from backend.servicios.brazo.simulador_dobot.protocolo import ProtocoloDobot
from backend.servicios.brazo.simulador_dobot.servidor_tcp import ServidorDashboard


@pytest.fixture(params=[True, False], ids=["con_fisica", "sin_fisica"])
def entorno(request, parametros_agarre):
    if request.param:
        pytest.importorskip("pybullet")
    calibracion = ejemplo.calibracion_ejemplo()
    simulador = Simulador(calibracion, parametros_agarre, FEN_DE_PRUEBA, request.param, escala_tiempo=30.0)
    servidor = ServidorDashboard(ProtocoloDobot(simulador), "127.0.0.1", 0)
    servidor.iniciar()
    simulador.iniciar_hilo()
    ejecutor = EjecutorReal(
        host="127.0.0.1", puerto_dashboard=servidor.puerto, posiciones_casillas=calibracion.posiciones_casillas,
        orientacion=calibracion.orientacion, angulos_cero=calibracion.angulos_cero, velocidad_global=100, parametros=parametros_agarre,
    )
    ejecutor.conectar()
    yield simulador, ejecutor
    ejecutor.desconectar()
    servidor.detener()
    simulador.cerrar()


def _casillas_ocupadas(simulador) -> dict[str, str]:
    return {pieza["casilla"]: pieza["simbolo"] for pieza in simulador.instantanea()["piezas"] if pieza["casilla"]}


def test_e2e4_mueve_el_peon_y_deja_el_resto_en_su_lugar(entorno):
    simulador, ejecutor = entorno
    tablero = chess.Board(FEN_DE_PRUEBA)
    ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci("e2e4"))
    ocupadas = _casillas_ocupadas(simulador)
    assert ocupadas.get("e4") == "P" and "e2" not in ocupadas
    esperadas = {chess.square_name(c): p.symbol() for c, p in tablero.piece_map().items()}
    esperadas.pop("e2")
    esperadas["e4"] = "P"
    assert ocupadas == esperadas
    assert simulador.modo() == 5
    assert simulador.pose[:3] == pytest.approx(cinematica.pose_para_angulos(ejecutor.angulos_cero)[:3], abs=1e-3)
    comandos = [l["texto"] for l in simulador.log if l["origen"] == "->"]
    assert any(c.startswith("MovJ(pose=") for c in comandos) and any(c.startswith("MovL(pose=") for c in comandos)
    assert any(c.startswith("SetHoldRegs(") for c in comandos)


def test_el_caballo_se_mueve_con_su_apertura_y_vuelve_a_la_posicion_cero(entorno):
    simulador, ejecutor = entorno
    tablero = chess.Board(FEN_DE_PRUEBA)
    ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci("b1c3"))
    assert _casillas_ocupadas(simulador).get("c3") == "N"
    assert simulador.pose[:3] == pytest.approx(cinematica.pose_para_angulos(ejecutor.angulos_cero)[:3], abs=1e-3)


def test_jugar_desde_una_casilla_vacia_da_pieza_no_agarrada(entorno):
    simulador, ejecutor = entorno
    simulador.cargar_fen("8/8/8/8/8/8/8/8 w - - 0 1")
    tablero = chess.Board(FEN_DE_PRUEBA)
    with pytest.raises(PiezaNoAgarrada):
        ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci("e2e4"))
