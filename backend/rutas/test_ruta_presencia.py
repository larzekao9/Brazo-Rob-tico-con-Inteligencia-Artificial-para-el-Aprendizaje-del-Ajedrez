"""Señal de vida de una partida con reloj: `POST /partida/{id}/presencia` (una partida con reloj no se puede dejar)."""
from backend.rutas.test_ruta_tiempo_agotado import contexto  # noqa: F401  (fixture compartida)

DIEZ_MIN = 600_000


def _crear(cliente, headers, control: int = DIEZ_MIN) -> str:
    respuesta = cliente.post("/partida", json={"nivel": 3, "control_tiempo_ms": control}, headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["id"]


def test_la_senal_de_vida_devuelve_el_estado_de_la_partida(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)

    respuesta = cliente.post(f"/partida/{partida_id}/presencia", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "en_curso"
    assert respuesta.json()["terminada"] is False


def test_sin_reloj_la_senal_de_vida_no_hace_nada(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers, control=0)

    respuesta = cliente.post(f"/partida/{partida_id}/presencia", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "en_curso"


def test_la_senal_de_vida_es_solo_del_dueno(contexto) -> None:
    cliente, registrar = contexto
    partida_id = _crear(cliente, registrar("a@test.com"))

    respuesta = cliente.post(f"/partida/{partida_id}/presencia", headers=registrar("b@test.com"))

    assert respuesta.status_code == 403


def test_la_senal_de_vida_de_una_partida_inexistente_da_404(contexto) -> None:
    cliente, registrar = contexto

    respuesta = cliente.post("/partida/no-existe/presencia", headers=registrar("a@test.com"))

    assert respuesta.status_code == 404
