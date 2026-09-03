from backend.simulation import cerrar_escena, crear_escena, resaltar_jugada


def test_crear_escena_devuelve_64_casillas():
    client_id, casillas = crear_escena(modo_gui=False)
    try:
        assert len(casillas) == 64
        assert "e4" in casillas
    finally:
        cerrar_escena(client_id)


def test_resaltar_jugada_no_tira_excepcion():
    client_id, casillas = crear_escena(modo_gui=False)
    try:
        resaltar_jugada(casillas, "e2", "e4", client_id)
    finally:
        cerrar_escena(client_id)
