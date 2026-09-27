from unittest.mock import MagicMock

import chess
import pytest

from backend.modelos.partida import Partida
from backend.servicios.brazo import servicio_brazo


@pytest.fixture(autouse=True)
def _limpiar_ejecutor_cacheado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(servicio_brazo, "_ejecutor", None)


def _tablero_y_jugada() -> tuple[chess.Board, chess.Move]:
    tablero = chess.Board()
    return tablero, tablero.parse_uci("e2e4")


def test_ejecutar_respuesta_en_brazo_no_hace_nada_si_usa_brazo_es_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _crear_ejecutor_fake(modo: str, **kwargs):
        raise AssertionError("no debería crearse un ejecutor si usa_brazo es False")

    monkeypatch.setattr(servicio_brazo, "crear_ejecutor_movimiento", _crear_ejecutor_fake)
    partida = Partida(usa_brazo=False)
    tablero_antes, jugada = _tablero_y_jugada()

    resultado = servicio_brazo.ejecutar_respuesta_en_brazo(partida, tablero_antes, jugada)

    assert resultado is None


def test_ejecutar_respuesta_en_brazo_llama_al_ejecutor_con_los_argumentos_correctos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ejecutor_mock = MagicMock()
    monkeypatch.setattr(
        servicio_brazo, "crear_ejecutor_movimiento", lambda modo, **kwargs: ejecutor_mock
    )
    partida = Partida(usa_brazo=True)
    tablero_antes, jugada = _tablero_y_jugada()

    resultado = servicio_brazo.ejecutar_respuesta_en_brazo(partida, tablero_antes, jugada)

    assert resultado is None
    ejecutor_mock.ejecutar_movimiento.assert_called_once_with(tablero_antes, jugada)


def test_ejecutar_respuesta_en_brazo_captura_el_error_del_ejecutor_y_lo_devuelve_como_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ejecutor_mock = MagicMock()
    ejecutor_mock.ejecutar_movimiento.side_effect = RuntimeError("brazo desconectado")
    monkeypatch.setattr(
        servicio_brazo, "crear_ejecutor_movimiento", lambda modo, **kwargs: ejecutor_mock
    )
    partida = Partida(usa_brazo=True)
    tablero_antes, jugada = _tablero_y_jugada()

    resultado = servicio_brazo.ejecutar_respuesta_en_brazo(partida, tablero_antes, jugada)

    assert resultado == "brazo desconectado"


def test_ejecutar_respuesta_en_brazo_modo_real_sin_host_configurado_no_rompe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Si alguien prende usa_brazo con AJEDREZ_MODO_BRAZO=real pero sin
    # configurar el host, _obtener_ejecutor lanza KeyError al leer la
    # variable de entorno — no debe filtrarse como excepción sin capturar.
    monkeypatch.setenv("AJEDREZ_MODO_BRAZO", "real")
    monkeypatch.delenv("AJEDREZ_BRAZO_HOST", raising=False)
    partida = Partida(usa_brazo=True)
    tablero_antes, jugada = _tablero_y_jugada()

    resultado = servicio_brazo.ejecutar_respuesta_en_brazo(partida, tablero_antes, jugada)

    assert resultado is not None


def test_obtener_ejecutor_usa_simulado_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[tuple[str, dict]] = []

    def _crear_ejecutor_fake(modo: str, **kwargs):
        llamadas.append((modo, kwargs))
        return MagicMock()

    monkeypatch.setattr(servicio_brazo, "crear_ejecutor_movimiento", _crear_ejecutor_fake)
    monkeypatch.delenv("AJEDREZ_MODO_BRAZO", raising=False)

    servicio_brazo._obtener_ejecutor()

    assert llamadas == [("simulado", {})]


def test_obtener_ejecutor_modo_real_lee_host_de_variable_de_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas: list[tuple[str, dict]] = []

    def _crear_ejecutor_fake(modo: str, **kwargs):
        llamadas.append((modo, kwargs))
        return MagicMock()

    monkeypatch.setattr(servicio_brazo, "crear_ejecutor_movimiento", _crear_ejecutor_fake)
    monkeypatch.setenv("AJEDREZ_MODO_BRAZO", "real")
    monkeypatch.setenv("AJEDREZ_BRAZO_HOST", "192.0.2.1")
    monkeypatch.delenv("AJEDREZ_BRAZO_PUERTO_DASHBOARD", raising=False)

    servicio_brazo._obtener_ejecutor()

    assert llamadas == [("real", {"host": "192.0.2.1"})]


def test_obtener_ejecutor_cachea_la_instancia_entre_llamadas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contador = {"veces": 0}

    def _crear_ejecutor_fake(modo: str, **kwargs):
        contador["veces"] += 1
        return MagicMock()

    monkeypatch.setattr(servicio_brazo, "crear_ejecutor_movimiento", _crear_ejecutor_fake)

    primero = servicio_brazo._obtener_ejecutor()
    segundo = servicio_brazo._obtener_ejecutor()

    assert contador["veces"] == 1
    assert primero is segundo
