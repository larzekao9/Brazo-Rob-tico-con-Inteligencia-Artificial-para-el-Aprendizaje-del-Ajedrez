"""Pinza y piezas con física: el estado de agarre (0 a 3) y los choques salen de la simulación, no de una tabla."""
import pytest

from backend.servicios.brazo import pinza_dh
from backend.servicios.brazo.simulador_dobot.conftest import FEN_UN_CABALLO, mover_y_esperar, pose_agarre
from backend.servicios.brazo.simulador_dobot.mundo import MundoFisico
from backend.servicios.brazo.simulador_dobot.parametros import PERFILES_PIEZAS, ParametrosFisicos

pytest.importorskip("pybullet")


def _inicializar(simulador, fuerza_pct: int = 40) -> None:
    simulador.pinza.escribir(pinza_dh.REG_INICIALIZAR, 1)
    simulador.avanzar(2.5)
    assert simulador.pinza.inicializada
    simulador.pinza.escribir(pinza_dh.REG_FUERZA, fuerza_pct)


def _bajar_sobre(simulador, casilla: str, apertura: int, desplazamiento=(0.0, 0.0)) -> None:
    mover_y_esperar(simulador, pose_agarre(simulador, casilla, 80, desplazamiento), articular=True, velocidad_pct=50)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, apertura)
    simulador.avanzar(1.2)
    mover_y_esperar(simulador, pose_agarre(simulador, casilla, 0, desplazamiento), velocidad_pct=20)


def _subir(simulador, casilla: str, sobre_mm: float = 80) -> None:
    mover_y_esperar(simulador, pose_agarre(simulador, casilla, sobre_mm), velocidad_pct=40)
    simulador.avanzar(0.5)


def _pieza(simulador):
    return simulador.mundo.piezas()[0]


def test_parametros_de_la_pinza_coinciden_con_pinza_dh():
    assert ParametrosFisicos().carrera_mm == pinza_dh.CARRERA_MM


def test_aperturas_medidas_con_el_brazo_real_dejan_pasar_las_piezas_de_ejemplo():
    gap_peon = pinza_dh.ancho_mm_para_posicion(560)
    gap_caballo = pinza_dh.ancho_mm_para_posicion(860)
    assert PERFILES_PIEZAS["p"].ancho_maximo_mm < gap_peon < PERFILES_PIEZAS["n"].ancho_maximo_mm * 1.0 + 1
    assert PERFILES_PIEZAS["n"].ancho_maximo_mm < gap_caballo


def test_cerrar_en_el_aire_da_agarre_uno_y_posicion_cero(crear_simulador):
    simulador = crear_simulador()
    _inicializar(simulador)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(3.0)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_LLEGO
    assert simulador.pinza.posicion_actual == 0


def test_cerrar_sobre_un_peon_da_agarre_dos_y_la_pieza_sube_con_los_dedos(crear_simulador):
    simulador = crear_simulador()
    _inicializar(simulador, 40)
    _bajar_sobre(simulador, "e2", 560)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.0)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_SOSTIENE
    assert 0 < simulador.pinza.posicion_actual < 560
    assert simulador.pinza.fuerza_contacto_n == pytest.approx(41.0, rel=0.15)
    _subir(simulador, "e2")
    assert simulador.pinza.agarre == pinza_dh.AGARRE_SOSTIENE
    assert _pieza(simulador).z > simulador.geometria.z_superficie + 60


def test_soltar_la_pieza_vuelve_a_agarre_uno_y_la_pieza_queda_apoyada(crear_simulador):
    simulador = crear_simulador()
    _inicializar(simulador)
    _bajar_sobre(simulador, "e2", 560)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.0)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 560)
    simulador.avanzar(2.0)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_LLEGO
    assert _pieza(simulador).z == pytest.approx(simulador.geometria.z_superficie, abs=0.6)


def test_la_pieza_se_cae_al_subir_con_fuerza_baja_y_se_sostiene_con_fuerza_alta(crear_simulador):
    resultados = {}
    for fuerza in (20, 100):
        simulador = crear_simulador()
        simulador.inyectar_fallo("dedos_resbaladizos", True)
        _inicializar(simulador, fuerza)
        _bajar_sobre(simulador, "e2", 560)
        simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
        simulador.avanzar(2.0)
        _subir(simulador, "e2")
        resultados[fuerza] = (simulador.pinza.agarre, _pieza(simulador).z)
    assert resultados[20][0] == pinza_dh.AGARRE_SE_CAYO
    assert resultados[20][1] < resultados[100][1] - 40
    assert resultados[100][0] == pinza_dh.AGARRE_SOSTIENE


def test_fallo_soltar_la_pieza_afloja_los_dedos_y_la_pieza_cae(crear_simulador):
    simulador = crear_simulador()
    _inicializar(simulador, 40)
    _bajar_sobre(simulador, "e2", 560)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.0)
    _subir(simulador, "e2")
    simulador.inyectar_fallo("pieza_cae")
    simulador.avanzar(2.0)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_SE_CAYO
    assert _pieza(simulador).z < simulador.geometria.z_superficie + 5


def test_apertura_chica_sobre_el_caballo_choca_con_la_cabeza_y_no_agarra(crear_simulador):
    simulador = crear_simulador(FEN_UN_CABALLO)
    _inicializar(simulador)
    _bajar_sobre(simulador, "b1", 560)
    assert simulador.choque
    assert any("chocando" in l["texto"] for l in simulador.log)
    assert simulador.mundo.desviacion_herramienta_mm() > 10
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.0)
    assert simulador.pinza.agarre != pinza_dh.AGARRE_SOSTIENE
    assert any(pieza_dano for pieza_dano in simulador.piezas_danadas)


def test_apertura_de_860_deja_agarrar_el_caballo(crear_simulador):
    simulador = crear_simulador(FEN_UN_CABALLO)
    _inicializar(simulador, 40)
    _bajar_sobre(simulador, "b1", 860)
    assert not simulador.choque
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.5)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_SOSTIENE
    _subir(simulador, "b1")
    assert _pieza(simulador).z > simulador.geometria.z_superficie + 60
    assert not simulador.piezas_danadas


def test_dedos_que_barren_la_fila_empujan_a_la_pieza_vecina(crear_simulador):
    simulador = crear_simulador()
    _inicializar(simulador)
    x0, y0 = simulador.geometria.centro_casilla("e2")
    mover_y_esperar(simulador, pose_agarre(simulador, "e2", 80, (0.0, -45.0)), articular=True, velocidad_pct=50)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 1000)
    simulador.avanzar(1.5)
    mover_y_esperar(simulador, pose_agarre(simulador, "e2", 0, (0.0, -45.0)), velocidad_pct=20)
    mover_y_esperar(simulador, pose_agarre(simulador, "e2", 0, (0.0, 5.0)), velocidad_pct=15)
    pieza = _pieza(simulador)
    desplazamiento = ((pieza.x - x0) ** 2 + (pieza.y - y0) ** 2) ** 0.5
    assert desplazamiento > 5.0 or pieza.inclinacion_grados > 20


def test_cada_dedo_aprieta_con_la_mitad_de_la_fuerza_total_configurada():
    fisicos = ParametrosFisicos()
    from backend.servicios.brazo.simulador_dobot.calibracion_ejemplo import calibracion_ejemplo
    from backend.servicios.brazo.simulador_dobot.mundo import GeometriaTablero

    calibracion = calibracion_ejemplo()
    geometria = GeometriaTablero.desde_posiciones(calibracion.posiciones_casillas, 70.0)
    x, y = geometria.centro_casilla("e2")
    for fuerza_total in (28.0, 60.0):
        mundo = MundoFisico(geometria, fisicos, "8/8/8/8/8/8/4P3/8 w - - 0 1", 45.0, (x, y, 73.0))
        try:
            mundo.fijar_herramienta((x, y, 73.0), 45.0 + geometria.angulo_u_grados)
            mundo.fijar_dedos(26.0, fuerza_total, 40.0)
            mundo.avanzar(300)
            mundo.fijar_dedos(0.0, fuerza_total, 40.0)
            mundo.avanzar(500)
            assert mundo.fuerza_de_contacto_con_piezas_n() == pytest.approx(fuerza_total, rel=0.1)
        finally:
            mundo.cerrar()


def test_dos_mundos_pueden_convivir_porque_cada_llamada_lleva_su_cliente(crear_simulador):
    uno, otro = crear_simulador(), crear_simulador()
    assert uno.mundo.cliente != otro.mundo.cliente
    otro.cargar_fen("8/8/8/8/8/8/8/8 w - - 0 1")
    assert len(uno.mundo.piezas()) == 1 and len(otro.mundo.piezas()) == 0
