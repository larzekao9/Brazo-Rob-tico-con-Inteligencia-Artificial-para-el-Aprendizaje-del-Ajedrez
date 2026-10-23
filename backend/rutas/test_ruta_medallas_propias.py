"""Medallas propias: un facilitador crea, edita, entrega y borra las suyas (SQLite en memoria)."""
import pytest
from sqlalchemy import select

from backend.modelos.tablas_orm import MedallaGanadaORM, MedallaPersonalizadaORM
from backend.rutas.test_ruta_cursos import _crear, _solo_principal, _unirse
from backend.rutas.test_ruta_gestion_usuarios import contexto  # noqa: F401  (fixture compartida)
from backend.rutas.test_ruta_medallas import PNG, _album, _ganadas, _imagenes_en_carpeta_temporal, _jugar  # noqa: F401
from backend.servicios.medallas.catalogo import PLANTILLAS, REGLAS


def _nueva(cliente, quien, **cambios):
    cuerpo = {"nombre": "Guerrero Constante", "descripcion": "Ganá 2 partidas.", "nivel": "plata", "pieza": "torre", "regla": "victorias", "meta": 2}
    cuerpo.update(cambios)
    return cliente.post("/medallas", json=cuerpo, headers=quien["headers"])


def _codigos(cliente, jugador) -> list[str]:
    return [m["codigo"] for m in _album(cliente, jugador)["medallas"]]


def test_las_opciones_traen_reglas_niveles_e_ideas_y_solo_las_ve_un_facilitador(contexto) -> None:
    cliente, registrar, _ = contexto
    profe, jugador = registrar("prof@test.com", "facilitador"), registrar("j@test.com")

    cuerpo = cliente.get("/medallas/opciones", headers=profe["headers"]).json()

    reglas = {r["codigo"]: r for r in cuerpo["reglas"]}
    assert set(reglas) == set(REGLAS) | {"manual"} and reglas["manual"]["tipo"] == "manual"
    assert reglas["victorias"]["tipo"] == "contador" and (reglas["victorias"]["minimo"], reglas["victorias"]["maximo"]) == (1, 500)
    assert cuerpo["niveles"] == ["bronce", "plata", "oro", "legendaria"] and len(cuerpo["plantillas"]) == len(PLANTILLAS)
    assert cliente.get("/medallas/opciones", headers=jugador["headers"]).status_code == 403
    # toda idea listada es válida: se puede crear tal cual
    for idea in cuerpo["plantillas"]:
        assert _nueva(cliente, profe, **idea).status_code == 201, idea


def test_crear_valida_los_datos_y_el_alcance(contexto, monkeypatch) -> None:
    cliente, registrar, _ = contexto
    principal, comun = registrar("admin@test.com", "facilitador"), registrar("comun@test.com", "facilitador")
    _solo_principal(monkeypatch, "admin@test.com")

    creada = _nueva(cliente, comun)
    assert creada.status_code == 201 and creada.json()["codigo"].startswith("propia_")
    assert (creada.json()["general"], creada.json()["es_mia"], creada.json()["imagen_url"], creada.json()["ganada_por"]) == (False, True, None, 0)

    assert _nueva(cliente, comun, general=True).status_code == 403  # solo el principal crea generales
    assert _nueva(cliente, principal, general=True).json()["general"] is True
    for malo in (
        {"nombre": "x"}, {"descripcion": "ab"}, {"nivel": "diamante"}, {"pieza": "reina"}, {"regla": "inventada"},
        {"meta": 0}, {"meta": 9999}, {"regla": "mejor_precision", "meta": 20},
    ):
        assert _nueva(cliente, comun, **malo).status_code in (400, 422), malo
    sin_numero = _nueva(cliente, comun, regla="corono", meta=77).json()  # las de sí o no ignoran la cantidad
    assert sin_numero["meta"] == 1
    assert _nueva(cliente, comun, regla="manual", meta=40).json()["meta"] == 1


def test_una_medalla_automatica_se_gana_jugando_y_solo_la_ven_los_alumnos_de_su_facilitador(contexto, monkeypatch) -> None:
    cliente, registrar, fabrica = contexto
    profe, otro, alumno, ajeno, solo = (
        registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador"), registrar("a@test.com"),
        registrar("x@test.com"), registrar("s@test.com"),
    )
    _solo_principal(monkeypatch, "nadie@test.com")
    propia = _nueva(cliente, profe).json()["codigo"]
    _unirse(cliente, alumno, _crear(cliente, profe)["codigo"])
    _unirse(cliente, ajeno, _crear(cliente, otro)["codigo"])
    for jugador in (alumno, ajeno, solo):
        _jugar(fabrica, jugador["id"])
        _jugar(fabrica, jugador["id"])

    assert propia in _codigos(cliente, alumno) and propia in _ganadas(cliente, alumno)
    assert propia not in _codigos(cliente, ajeno) and propia not in _codigos(cliente, solo)
    # si el alumno deja el curso, la medalla ya ganada se conserva
    cliente.post("/cursos/salir", headers=alumno["headers"])
    assert propia in _ganadas(cliente, alumno)


def test_una_medalla_general_la_ven_todos(contexto, monkeypatch) -> None:
    cliente, registrar, _ = contexto
    principal, jugador = registrar("admin@test.com", "facilitador"), registrar("j@test.com")
    _solo_principal(monkeypatch, "admin@test.com")
    general = _nueva(cliente, principal, general=True).json()["codigo"]

    assert general in _codigos(cliente, jugador)


def test_la_manual_se_entrega_a_un_curso_o_a_jugadores_y_se_avisa_como_nueva(contexto, monkeypatch) -> None:
    cliente, registrar, _ = contexto
    profe, otro = registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador")
    uno, dos, ajeno = registrar("a@test.com"), registrar("b@test.com"), registrar("x@test.com")
    _solo_principal(monkeypatch, "nadie@test.com")
    curso = _crear(cliente, profe)
    for jugador in (uno, dos):
        _unirse(cliente, jugador, curso["codigo"])
    _unirse(cliente, ajeno, _crear(cliente, otro)["codigo"])
    manual = _nueva(cliente, profe, regla="manual", nombre="Campeón de la clase").json()["codigo"]
    automatica = _nueva(cliente, profe).json()["codigo"]

    entrega = cliente.post(f"/medallas/{manual}/otorgar", json={"curso_id": curso["id"]}, headers=profe["headers"])
    assert entrega.json() == {"otorgadas": 2, "ya_la_tenian": 0}
    assert cliente.post(f"/medallas/{manual}/otorgar", json={"usuario_ids": [uno["id"]]}, headers=profe["headers"]).json() == {"otorgadas": 0, "ya_la_tenian": 1}
    assert manual in _album(cliente, uno)["nuevas"] and manual in _ganadas(cliente, dos)

    assert cliente.post(f"/medallas/{manual}/otorgar", json={"usuario_ids": [ajeno["id"]]}, headers=profe["headers"]).status_code == 400  # no es de sus cursos
    assert cliente.post(f"/medallas/{manual}/otorgar", json={}, headers=profe["headers"]).status_code == 400
    assert cliente.post(f"/medallas/{automatica}/otorgar", json={"curso_id": curso["id"]}, headers=profe["headers"]).status_code == 400  # se gana jugando
    assert cliente.post(f"/medallas/{manual}/otorgar", json={"curso_id": curso["id"]}, headers=otro["headers"]).status_code == 403


def test_editar_y_borrar_son_del_creador_o_del_principal(contexto, monkeypatch) -> None:
    cliente, registrar, fabrica = contexto
    principal, profe, otro, jugador = registrar("admin@test.com", "facilitador"), registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador"), registrar("j@test.com")
    _solo_principal(monkeypatch, "admin@test.com")
    codigo = _nueva(cliente, profe, regla="manual").json()["codigo"]
    _unirse(cliente, jugador, _crear(cliente, profe)["codigo"])
    cliente.post(f"/medallas/{codigo}/otorgar", json={"usuario_ids": [jugador["id"]]}, headers=profe["headers"])

    assert cliente.patch(f"/medallas/{codigo}", json={"nombre": "Robada"}, headers=otro["headers"]).status_code == 403
    assert cliente.delete(f"/medallas/{codigo}", headers=otro["headers"]).status_code == 403
    cambiada = cliente.patch(f"/medallas/{codigo}", json={"nombre": "Nombre nuevo", "nivel": "oro"}, headers=profe["headers"])
    assert cambiada.status_code == 200 and (cambiada.json()["nombre"], cambiada.json()["nivel"], cambiada.json()["ganada_por"]) == ("Nombre nuevo", "oro", 1)
    assert cliente.patch(f"/medallas/{codigo}", json={"regla": "victorias", "meta": 9999}, headers=profe["headers"]).status_code == 400
    assert cliente.patch("/medallas/propia_inexistente", json={"nombre": "Algo"}, headers=profe["headers"]).status_code == 404
    assert [m["codigo"] for m in cliente.get("/medallas/mias", headers=otro["headers"]).json()] == []
    assert [m["codigo"] for m in cliente.get("/medallas/mias", headers=principal["headers"]).json()] == [codigo]  # el principal ve todas

    assert cliente.delete(f"/medallas/{codigo}", headers=principal["headers"]).status_code == 204
    assert codigo not in _codigos(cliente, jugador)
    with fabrica() as sesion:
        assert sesion.scalars(select(MedallaPersonalizadaORM)).all() == [] and sesion.scalars(select(MedallaGanadaORM).where(MedallaGanadaORM.codigo == codigo)).all() == []


def test_el_creador_sube_la_imagen_de_su_medalla_y_no_la_de_otro_ni_las_de_fabrica(contexto, monkeypatch) -> None:
    cliente, registrar, _ = contexto
    principal, profe, otro = registrar("admin@test.com", "facilitador"), registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador")
    _solo_principal(monkeypatch, "admin@test.com")
    codigo = _nueva(cliente, profe).json()["codigo"]

    def subir(quien, cod):
        return cliente.post(f"/facilitador/medallas/{cod}/imagen", files={"archivo": ("dibujo.png", PNG, "image/png")}, headers=quien["headers"])

    assert subir(otro, codigo).status_code == 403
    assert subir(profe, "primer_peon").status_code == 403  # las de fábrica, solo el principal
    subida = subir(profe, codigo)
    assert subida.status_code == 200 and subida.json()["imagen_url"].startswith(f"/media/medallas/{codigo}.png")
    assert cliente.get("/medallas/mias", headers=profe["headers"]).json()[0]["imagen_url"] == subida.json()["imagen_url"]
    assert subir(principal, codigo).status_code == 200 and subir(principal, "primer_peon").status_code == 200
    assert cliente.delete(f"/facilitador/medallas/{codigo}/imagen", headers=otro["headers"]).status_code == 403
    assert cliente.delete(f"/facilitador/medallas/{codigo}/imagen", headers=profe["headers"]).status_code == 204


def test_eliminar_cuentas_limpia_sus_medallas(contexto, monkeypatch) -> None:
    cliente, registrar, fabrica = contexto
    admin, profe, jugador = registrar("admin@test.com", "facilitador"), registrar("prof@test.com", "facilitador"), registrar("j@test.com")
    _solo_principal(monkeypatch, "admin@test.com")
    codigo = _nueva(cliente, profe, regla="manual").json()["codigo"]
    _unirse(cliente, jugador, _crear(cliente, profe)["codigo"])
    cliente.post(f"/medallas/{codigo}/otorgar", json={"usuario_ids": [jugador["id"]]}, headers=profe["headers"])
    _jugar(fabrica, jugador["id"])
    assert len(_ganadas(cliente, jugador)) >= 2

    assert cliente.delete(f"/auth/usuarios/{jugador['id']}", headers=admin["headers"]).status_code in (200, 204)  # antes fallaba por la FK de medalla_ganada
    with fabrica() as sesion:
        assert sesion.scalars(select(MedallaGanadaORM)).all() == []

    assert cliente.delete(f"/auth/usuarios/{profe['id']}", headers=admin["headers"]).status_code in (200, 204)
    with fabrica() as sesion:
        assert sesion.scalars(select(MedallaPersonalizadaORM)).all() == []
