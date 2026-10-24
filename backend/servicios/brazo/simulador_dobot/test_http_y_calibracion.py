"""Front web (API JSON y página) y calibración de ejemplo del simulador."""
import json
import urllib.error
import urllib.request

import pytest

from backend.servicios.brazo.calibracion_brazo import cargar_calibracion_brazo, cargar_parametros_agarre
from backend.servicios.brazo.simulador_dobot import calibracion_ejemplo as ejemplo
from backend.servicios.brazo.simulador_dobot.servidor_http import ServidorWeb


@pytest.fixture
def web(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    servidor = ServidorWeb(simulador, "127.0.0.1", 0)
    servidor.iniciar()
    yield simulador, f"http://127.0.0.1:{servidor.puerto}"
    servidor.detener()


def _pedir(url: str, cuerpo: dict | None = None):
    pedido = urllib.request.Request(url, data=None if cuerpo is None else json.dumps(cuerpo).encode(), method="GET" if cuerpo is None else "POST")
    with urllib.request.urlopen(pedido, timeout=5) as respuesta:
        return respuesta.status, respuesta.read()


def test_pagina_principal_declara_viewport_y_trae_los_controles(web):
    _, base = web
    estado, cuerpo = _pedir(base + "/")
    html = cuerpo.decode("utf-8")
    assert estado == 200 and 'name="viewport"' in html
    for identificador in ("cenital", "lateral", "reiniciar", "fen", "pausa", "escala", "log"):
        assert f'id="{identificador}"' in html


def test_estado_trae_pose_pinza_piezas_y_tablero(web):
    simulador, base = web
    _, cuerpo = _pedir(base + "/api/estado")
    estado = json.loads(cuerpo)
    assert estado["modo"] == 5 and len(estado["pose"]) == 6 and estado["pinza"]["agarre"] == 1
    assert len(estado["piezas"]) == 3 and estado["tablero"]["z_tope"] == simulador.z_tope  # la del FEN y las dos damas de reserva de los parámetros de ejemplo
    assert set(estado["perfiles"]) == {"p", "n", "b", "r", "q", "k"}


def test_pausa_velocidad_fen_reinicio_y_fallos_por_http(web):
    simulador, base = web
    _pedir(base + "/api/pausa", {"pausado": True})
    assert simulador.pausado
    _pedir(base + "/api/velocidad", {"escala": 4})
    assert simulador.escala_tiempo == 4
    _pedir(base + "/api/velocidad", {"escala": 500})
    assert simulador.escala_tiempo == 20
    _pedir(base + "/api/fen", {"fen": "8/8/8/8/4P3/8/8/8 w - - 0 1"})
    assert [p.casilla_inicial for p in simulador.mundo.piezas() if p.casilla_inicial != "reserva"] == ["e4"]  # y las damas de reserva siguen en su sitio
    _pedir(base + "/api/fallo", {"tipo": "pinza_no_responde", "valor": True})
    assert simulador.fallos.pinza_no_responde
    _pedir(base + "/api/reiniciar", {})
    assert len(simulador.mundo.piezas()) == 34 and not simulador.fallos.pinza_no_responde  # las 32 del tablero y las 2 damas de reserva
    _pedir(base + "/api/limpiar_log", {})
    assert len(simulador.log) == 0


def test_fen_invalido_y_fallo_desconocido_dan_400(web):
    _, base = web
    for ruta, cuerpo in (("/api/fen", {"fen": "esto no es un fen"}), ("/api/fallo", {"tipo": "inventado"})):
        with pytest.raises(urllib.error.HTTPError) as error:
            _pedir(base + ruta, cuerpo)
        assert error.value.code == 400


def test_ruta_inexistente_da_404(web):
    _, base = web
    with pytest.raises(urllib.error.HTTPError) as error:
        _pedir(base + "/nada")
    assert error.value.code == 404


def test_calibracion_de_ejemplo_es_valida_y_se_escribe_en_formato_brazo_json(tmp_path):
    calibracion = ejemplo.calibracion_ejemplo()
    assert calibracion.avisos == ()
    assert calibracion.orientacion == (-180.0, 0.0, -120.0)
    ruta = ejemplo.escribir_calibracion_ejemplo(tmp_path / "brazo_ejemplo.json")
    leida, agarre = cargar_calibracion_brazo(ruta), cargar_parametros_agarre(ruta)
    assert leida.posiciones_casillas["e2"] == pytest.approx(calibracion.posiciones_casillas["e2"])
    assert agarre.z_tope == ejemplo.Z_TOPE_EJEMPLO and agarre.apertura_para("n") == 860


def test_todas_las_casillas_de_ejemplo_estan_al_alcance_del_brazo():
    from backend.servicios.brazo.simulador_dobot import cinematica

    calibracion = ejemplo.calibracion_ejemplo()
    zs = ejemplo.Z_TOPE_EJEMPLO
    assert all(cinematica.esta_al_alcance(x, y, zs + 83.0) for x, y, _ in calibracion.posiciones_casillas.values())


def test_mundo_sin_fisica_sostiene_y_mueve_la_pieza_entre_los_dedos(crear_simulador):
    from backend.servicios.brazo import pinza_dh
    from backend.servicios.brazo.simulador_dobot.conftest import mover_y_esperar, pose_agarre

    simulador = crear_simulador(con_fisica=False)
    simulador.pinza.escribir(pinza_dh.REG_INICIALIZAR, 1)
    simulador.avanzar(2.5)
    mover_y_esperar(simulador, pose_agarre(simulador, "e2", 80), articular=True, velocidad_pct=50)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 560)
    simulador.avanzar(1.5)
    mover_y_esperar(simulador, pose_agarre(simulador, "e2"), velocidad_pct=30)
    simulador.pinza.escribir(pinza_dh.REG_POSICION, 0)
    simulador.avanzar(2.0)
    assert simulador.pinza.agarre == pinza_dh.AGARRE_SOSTIENE
    mover_y_esperar(simulador, pose_agarre(simulador, "e4", 80), velocidad_pct=30)
    assert simulador.mundo.piezas()[0].z > simulador.geometria.z_superficie + 60
