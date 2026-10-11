"""El reloj es parte de la partida: control de tiempo, tiempo restante y tiempo de cada jugada."""
from backend.rutas.test_ruta_tiempo_agotado import contexto  # noqa: F401  (fixture compartida)

DIEZ_MIN = 600_000


def _crear(cliente, headers, control: int = DIEZ_MIN) -> dict:
    respuesta = cliente.post("/partida", json={"nivel": 3, "control_tiempo_ms": control}, headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_la_partida_nace_con_el_control_de_tiempo_elegido(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")

    partida = _crear(cliente, headers)

    assert partida["control_tiempo_ms"] == DIEZ_MIN
    assert partida["tiempo_blancas_ms"] == DIEZ_MIN and partida["tiempo_negras_ms"] == DIEZ_MIN
    assert partida["tiempos_jugadas_ms"] == []


def test_sin_reloj_no_hay_tiempos_restantes(contexto) -> None:
    cliente, registrar = contexto
    partida = _crear(cliente, registrar("a@test.com"), control=0)

    assert partida["control_tiempo_ms"] == 0
    assert partida["tiempo_blancas_ms"] is None and partida["tiempo_negras_ms"] is None


def test_control_de_tiempo_invalido_da_400(contexto) -> None:
    cliente, registrar = contexto
    respuesta = cliente.post("/partida", json={"nivel": 3, "control_tiempo_ms": 5}, headers=registrar("a@test.com"))

    assert respuesta.status_code == 400


def test_mover_guarda_el_tiempo_de_cada_jugada_y_el_reloj(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)["id"]

    respuesta = cliente.post(
        f"/partida/{partida_id}/mover",
        json={"jugada": "e2e4", "tiempo_jugada_ms": 4200, "reloj_blancas_ms": 595_800},
        headers=headers,
    )

    assert respuesta.status_code == 200
    reloj = respuesta.json()["reloj"]
    assert reloj["blancas_ms"] == 595_800
    assert 0 <= DIEZ_MIN - reloj["negras_ms"] < 20_000  # el rival gastó lo que tardó en decidir
    estado = cliente.get(f"/partida/{partida_id}", headers=headers).json()
    assert len(estado["tiempos_jugadas_ms"]) == 2
    assert estado["tiempos_jugadas_ms"][0] == 4200 and estado["tiempos_jugadas_ms"][1] >= 0
    assert estado["tiempo_blancas_ms"] == 595_800 and estado["tiempo_negras_ms"] == reloj["negras_ms"]


def test_mover_sin_tiempos_deja_la_jugada_sin_medir(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers, control=0)["id"]

    respuesta = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"}, headers=headers)

    assert respuesta.json()["reloj"] is None
    assert cliente.get(f"/partida/{partida_id}", headers=headers).json()["tiempos_jugadas_ms"][0] is None


def test_el_reloj_guardado_solo_puede_bajar(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)["id"]

    bajo = cliente.put(f"/partida/{partida_id}/reloj", json={"blancas_ms": 480_000}, headers=headers).json()
    mayor = cliente.put(f"/partida/{partida_id}/reloj", json={"blancas_ms": 590_000}, headers=headers).json()

    assert bajo["tiempo_blancas_ms"] == 480_000
    assert mayor["tiempo_blancas_ms"] == 480_000


def test_el_reloj_no_lo_toca_otro_usuario(contexto) -> None:
    cliente, registrar = contexto
    dueno, intruso = registrar("dueno@test.com"), registrar("intruso@test.com")
    partida_id = _crear(cliente, dueno)["id"]

    assert cliente.put(f"/partida/{partida_id}/reloj", json={"blancas_ms": 1}, headers=intruso).status_code == 403
    assert cliente.put(f"/partida/{partida_id}/reloj", json={"blancas_ms": 1}).status_code == 401


def test_el_control_de_tiempo_solo_se_cambia_antes_de_la_primera_jugada(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)["id"]

    cambiado = cliente.put(f"/partida/{partida_id}/reloj", json={"control_tiempo_ms": 300_000}, headers=headers)
    assert cambiado.status_code == 200 and cambiado.json()["tiempo_blancas_ms"] == 300_000

    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"}, headers=headers)
    tarde = cliente.put(f"/partida/{partida_id}/reloj", json={"control_tiempo_ms": 900_000}, headers=headers)
    assert tarde.status_code == 400


def test_partida_sin_reloj_rechaza_guardar_tiempos(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers, control=0)["id"]

    assert cliente.put(f"/partida/{partida_id}/reloj", json={"blancas_ms": 1000}, headers=headers).status_code == 400


def test_el_analisis_trae_el_tiempo_de_cada_jugada_y_el_promedio(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4", "tiempo_jugada_ms": 3000}, headers=headers)
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "d2d4", "tiempo_jugada_ms": 5000}, headers=headers)

    analisis = cliente.get(f"/partida/{partida_id}/analisis-completo", headers=headers).json()

    jugadas = analisis["jugadas"]
    assert jugadas[0]["tiempo_ms"] == 3000 and jugadas[2]["tiempo_ms"] == 5000
    assert analisis["resumen"]["tiempo_medio_jugador_ms"] == 4000
    assert analisis["resumen"]["control_tiempo_ms"] == DIEZ_MIN
    assert analisis["resumen"]["duracion_ms"] >= 8000


def test_tiempo_agotado_deja_ese_lado_en_cero(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("a@test.com")
    partida_id = _crear(cliente, headers)["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4", "reloj_blancas_ms": 3000}, headers=headers)

    cerrada = cliente.post(f"/partida/{partida_id}/tiempo-agotado", json={"lado": "blancas"}, headers=headers).json()

    assert cerrada["tiempo_blancas_ms"] == 0 and cerrada["resultado"] == "0-1"
