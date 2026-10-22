import chess
import pytest

from backend.servicios.brazo.calibracion_brazo import ParametrosAgarre
from backend.servicios.brazo.calibracion_tablero import (
    PuntoCalibracion,
    calcular_posiciones_casillas,
)
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal, PiezaNoAgarrada
from backend.servicios.brazo.pinza_dh import AGARRE_LLEGO, AGARRE_SOSTIENE, EstadoPinza

HOST_DOCUMENTACION = "192.0.2.1"

PUNTOS_CALIBRACION_SINTETICOS = [
    PuntoCalibracion(casilla="a1", x=0.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="h1", x=700.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="a8", x=0.0, y=700.0, z=10.0),
]
APERTURA = 560
PARAMETROS = ParametrosAgarre(z_tope=100.0, margen_agarre_mm=3.0, giro_diagonal_grados=45.0, apertura_aproximacion=APERTURA, altura_segura_mm=80.0)


class ClienteFalso:
    """Reemplaza a `ClienteDobot`: anota lo que se le pide en orden, sin red ni brazo."""

    def __init__(self, historial: list) -> None:
        self.llamadas = historial

    def mover_a_pose(self, pose, lineal=False, **_):
        self.llamadas.append(("MovL" if lineal else "MovJ", tuple(pose)))

    def mover_a_angulos(self, angulos, **_):
        self.llamadas.append(("joint", tuple(angulos)))

    def conectar(self):
        self.llamadas.append(("conectar",))

    def cerrar(self):
        self.llamadas.append(("cerrar",))


class PinzaFalsa:
    """Reemplaza a `PinzaDH`: cerrar sobre una pieza deja `agarre = 2`; sin pieza, `agarre = 1` (cerró en el aire)."""

    def __init__(self, historial: list, inicializada: bool = True, hay_pieza: bool = True, se_cae_al_subir: bool = False) -> None:
        self.llamadas = historial
        self.inicializada = inicializada
        self.hay_pieza = hay_pieza
        self.se_cae_al_subir = se_cae_al_subir
        self._agarre = AGARRE_LLEGO

    def conectar(self):
        self.llamadas.append(("pinza_conectar",))

    def desconectar(self):
        self.llamadas.append(("pinza_desconectar",))

    def inicializar(self, **_):
        self.llamadas.append(("pinza_inicializar",))
        self.inicializada = True

    def estado(self) -> EstadoPinza:
        if self.se_cae_al_subir and any(l[0] == "MovL" for l in self.llamadas[self._marca_cierre():]):
            self._agarre = AGARRE_LLEGO
        return EstadoPinza(self.inicializada, self._agarre, 0)

    def _marca_cierre(self) -> int:
        cierres = [i for i, l in enumerate(self.llamadas) if l == ("pinza_cerrar",)]
        return cierres[-1] if cierres else len(self.llamadas)

    def mover_a(self, posicion):
        self.llamadas.append(("pinza_abrir_a", posicion))
        self._agarre = AGARRE_LLEGO

    def cerrar(self) -> EstadoPinza:
        self.llamadas.append(("pinza_cerrar",))
        self._agarre = AGARRE_SOSTIENE if self.hay_pieza else AGARRE_LLEGO
        return EstadoPinza(self.inicializada, self._agarre, 0)


def _ejecutor(parametros=PARAMETROS, **kwargs_pinza) -> tuple[EjecutorReal, list]:
    historial: list = []
    posiciones = calcular_posiciones_casillas(PUNTOS_CALIBRACION_SINTETICOS)
    ejecutor = EjecutorReal(
        host=HOST_DOCUMENTACION,
        posiciones_casillas=posiciones,
        orientacion=(-180.0, 0.0, -120.0),
        parametros=parametros,
        cliente=ClienteFalso(historial),
        pinza=PinzaFalsa(historial, **kwargs_pinza),
    )
    return ejecutor, historial


def _jugar(ejecutor: EjecutorReal, uci: str = "e2e4") -> None:
    tablero = chess.Board()
    ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci(uci))


def test_parametros_de_agarre_z_agarre_es_tope_mas_margen():
    assert PARAMETROS.z_agarre == pytest.approx(103.0)


def test_apertura_por_pieza_usa_la_medida_de_cada_una_y_nunca_la_del_peon_por_defecto():
    parametros = ParametrosAgarre(apertura_aproximacion=560, aperturas_por_pieza={"n": 800})

    assert parametros.apertura_para("p") == 560 and parametros.apertura_para("N") == 800
    with pytest.raises(RuntimeError, match="'q'"):
        parametros.apertura_para("q")


def test_ejecutor_real_baja_con_la_apertura_de_la_pieza_y_suelta_mas_abierta():
    parametros = ParametrosAgarre(z_tope=100.0, apertura_aproximacion=560, apertura_extra_soltar=150, aperturas_por_pieza={"n": 800})
    ejecutor, historial = _ejecutor(parametros=parametros)

    tablero = chess.Board()
    ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci("b1c3"))

    assert [l[1] for l in historial if l[0] == "pinza_abrir_a"] == [800, 950]  # al soltar se abre 150 más, hasta 1000 como mucho


def test_ejecutor_real_sin_apertura_medida_para_la_pieza_no_mueve_nada():
    ejecutor, historial = _ejecutor()

    tablero = chess.Board()
    with pytest.raises(RuntimeError, match="'n'"):
        ejecutor.ejecutar_movimiento(tablero, tablero.parse_uci("b1c3"))
    assert historial == []


def test_parametros_de_agarre_sin_altura_del_tablero_falla_con_mensaje_claro():
    with pytest.raises(RuntimeError, match="z_tope"):
        ParametrosAgarre().z_agarre


def test_ejecutor_real_sin_calibracion_lanza_runtime_error():
    ejecutor, historial = _ejecutor()
    ejecutor.posiciones_casillas = None

    with pytest.raises(RuntimeError, match="calibración"):
        _jugar(ejecutor)
    assert historial == []


def test_ejecutor_real_sin_orientacion_lanza_runtime_error():
    ejecutor, historial = _ejecutor()
    ejecutor.orientacion = None

    with pytest.raises(RuntimeError, match="orientación"):
        _jugar(ejecutor)
    assert historial == []  # no movió nada


def test_ejecutor_real_sin_altura_del_tablero_no_mueve_nada():
    ejecutor, historial = _ejecutor(parametros=ParametrosAgarre())

    with pytest.raises(RuntimeError, match="z_tope"):
        _jugar(ejecutor)
    assert historial == []


def test_ejecutor_real_con_pinza_sin_inicializar_no_mueve_nada():
    ejecutor, historial = _ejecutor(inicializada=False)

    with pytest.raises(RuntimeError, match="inicializada"):
        _jugar(ejecutor)
    assert historial == []


def test_ejecutor_real_con_captura_lanza_not_implemented_error():
    ejecutor, historial = _ejecutor()
    tablero_antes = chess.Board()
    tablero_antes.push_san("e4")
    tablero_antes.push_san("d5")

    with pytest.raises(NotImplementedError):
        ejecutor.ejecutar_movimiento(tablero_antes, tablero_antes.parse_uci("e4d5"))
    assert historial == []


def test_ejecutor_real_secuencia_de_una_jugada_sin_captura():
    ejecutor, historial = _ejecutor()

    _jugar(ejecutor)

    pasos = [(l[0], l[1][2] if l[0] in ("MovJ", "MovL") else None) for l in historial]
    assert pasos == [
        ("pinza_abrir_a", None),
        ("MovJ", 183.0),  # sobre e2, a altura segura
        ("MovL", 103.0),  # baja hasta 3 mm del tablero
        ("pinza_cerrar", None),
        ("MovL", 183.0),  # sube con la pieza
        ("MovL", 183.0),  # se traslada a e4
        ("MovL", 103.0),  # baja
        ("pinza_abrir_a", None),  # suelta
        ("MovL", 183.0),
    ]
    assert [l[1] for l in historial if l[0] == "pinza_abrir_a"] == [APERTURA, min(1000, APERTURA + ParametrosAgarre().apertura_extra_soltar)]


def test_ejecutor_real_bajar_y_subir_no_cierran_la_pinza():
    ejecutor, historial = _ejecutor()

    ejecutor.bajar_a("e2")
    ejecutor.subir_de("e2")

    assert ("pinza_cerrar",) not in historial
    alturas = [l[1][2] for l in historial if l[0] in ("MovJ", "MovL")]
    assert alturas == [183.0, 103.0, 183.0]


def test_ejecutor_real_gira_la_herramienta_en_diagonal_y_respeta_la_orientacion_medida():
    ejecutor, historial = _ejecutor()

    _jugar(ejecutor)

    poses = [l[1] for l in historial if l[0] in ("MovJ", "MovL")]
    assert all(p[3:] == (-180.0, 0.0, -75.0) for p in poses)  # rz = -120 + 45


def test_ejecutor_real_vuelve_a_la_posicion_cero_si_hay_angulos():
    cero = (303.8, -1.1, -83.3, 6.1, 16.0, 227.0)
    ejecutor, historial = _ejecutor()
    ejecutor.angulos_cero = cero

    _jugar(ejecutor)

    assert historial[-1] == ("joint", cero)


def test_ejecutor_real_si_no_agarra_nada_abre_sube_y_avisa_sin_trasladarse():
    ejecutor, historial = _ejecutor(hay_pieza=False)

    with pytest.raises(PiezaNoAgarrada, match="e2"):
        _jugar(ejecutor)

    movimientos = [l for l in historial if l[0] in ("MovJ", "MovL")]
    assert len(movimientos) == 3  # sobre e2, baja, sube: nunca fue a e4
    assert historial[-2] == ("pinza_abrir_a", APERTURA)
    assert historial[-1][0] == "MovL" and historial[-1][1][2] == pytest.approx(183.0)


def test_ejecutor_real_si_se_le_cae_la_pieza_al_subir_no_sigue():
    ejecutor, historial = _ejecutor(se_cae_al_subir=True)

    with pytest.raises(PiezaNoAgarrada, match="cayó"):
        _jugar(ejecutor)

    destino_y = ejecutor.posiciones_casillas["e4"][1]  # e2 y e4 comparten columna: se distinguen por la Y
    assert not any(l[0] == "MovL" and l[1][1] == pytest.approx(destino_y) for l in historial)


def test_ejecutor_real_conectar_inicializa_la_pinza_solo_si_hace_falta():
    ejecutor, historial = _ejecutor(inicializada=False)
    ejecutor.conectar()
    assert historial == [("conectar",), ("pinza_conectar",), ("pinza_inicializar",)]

    ejecutor, historial = _ejecutor(inicializada=True)
    ejecutor.conectar()
    assert historial == [("conectar",), ("pinza_conectar",)]


def test_ejecutor_real_desconectar_cierra_pinza_y_cliente():
    ejecutor, historial = _ejecutor()

    ejecutor.desconectar()

    assert historial == [("pinza_desconectar",), ("cerrar",)]
