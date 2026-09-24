"""Rutas /auth (registro, login, me) contra una SQLite en memoria — sin Postgres."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.rutas.ruta_auth import get_db


@pytest.fixture
def cliente():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    # Restaura el override anterior (si había uno, ej. el de `backend/test_main.py`,
    # que queda instalado a nivel de módulo durante toda la sesión de tests) en
    # vez de simplemente sacarlo — de lo contrario, correr esta suite junto a
    # otras deja `get_db` sin override para los tests que se ejecutan después.
    override_anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _db
    try:
        yield TestClient(app)
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


JUGADOR = {"email": "ana@test.com", "nombre": "Ana", "password": "secreto1"}


def test_registro_crea_jugador_por_defecto_y_devuelve_tokens(cliente) -> None:
    respuesta = cliente.post("/auth/registro", json=JUGADOR)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["rol"] == "jugador"
    assert cuerpo["usuario"]["email"] == JUGADOR["email"]
    assert cuerpo["tokens"]["access_token"]
    assert cuerpo["tokens"]["refresh_token"]


def test_registro_con_email_repetido_falla(cliente) -> None:
    cliente.post("/auth/registro", json=JUGADOR)
    respuesta = cliente.post("/auth/registro", json=JUGADOR)
    assert respuesta.status_code == 400


def test_registro_con_rol_invalido_falla(cliente) -> None:
    respuesta = cliente.post("/auth/registro", json={**JUGADOR, "rol": "admin"})
    assert respuesta.status_code == 422


def test_login_con_rol_esperado_jugador_entra(cliente) -> None:
    cliente.post("/auth/registro", json=JUGADOR)
    respuesta = cliente.post(
        "/auth/login",
        json={"email": JUGADOR["email"], "password": JUGADOR["password"], "rol_esperado": "jugador"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["rol"] == "jugador"


def test_login_de_facilitador_con_rol_esperado_jugador_da_403(cliente) -> None:
    facilitador = {"email": "prof@test.com", "nombre": "Profe", "password": "secreto1", "rol": "facilitador"}
    cliente.post("/auth/registro", json=facilitador)
    respuesta = cliente.post(
        "/auth/login",
        json={"email": facilitador["email"], "password": facilitador["password"], "rol_esperado": "jugador"},
    )
    assert respuesta.status_code == 403
    assert "jugador" in respuesta.json()["detail"]


def test_login_con_password_incorrecta_da_401(cliente) -> None:
    cliente.post("/auth/registro", json=JUGADOR)
    respuesta = cliente.post("/auth/login", json={"email": JUGADOR["email"], "password": "otra"})
    assert respuesta.status_code == 401


def test_me_devuelve_el_usuario_del_token(cliente) -> None:
    token = cliente.post("/auth/registro", json=JUGADOR).json()["tokens"]["access_token"]
    respuesta = cliente.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == JUGADOR["email"]
    assert respuesta.json()["rol"] == "jugador"


def test_me_sin_token_da_401(cliente) -> None:
    assert cliente.get("/auth/me").status_code == 401


def test_guardar_nivel_estimado_actualiza_el_usuario(cliente) -> None:
    token = cliente.post("/auth/registro", json=JUGADOR).json()["tokens"]["access_token"]

    respuesta = cliente.patch(
        "/auth/nivel-estimado",
        json={"nivel": 11, "rango": "Intermedio"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nivel_estimado"] == 11
    assert respuesta.json()["rango_estimado"] == "Intermedio"

    # y se refleja al volver a pedir el usuario
    respuesta_me = cliente.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert respuesta_me.json()["nivel_estimado"] == 11
    assert respuesta_me.json()["rango_estimado"] == "Intermedio"


def test_guardar_nivel_estimado_pisa_el_resultado_anterior(cliente) -> None:
    token = cliente.post("/auth/registro", json=JUGADOR).json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    cliente.patch("/auth/nivel-estimado", json={"nivel": 5, "rango": "Principiante"}, headers=headers)

    respuesta = cliente.patch("/auth/nivel-estimado", json={"nivel": 18, "rango": "Avanzado"}, headers=headers)

    assert respuesta.json()["nivel_estimado"] == 18
    assert respuesta.json()["rango_estimado"] == "Avanzado"


def test_guardar_nivel_estimado_sin_token_da_401(cliente) -> None:
    respuesta = cliente.patch("/auth/nivel-estimado", json={"nivel": 5, "rango": "Principiante"})
    assert respuesta.status_code == 401


def test_guardar_nivel_estimado_con_rango_invalido_da_422(cliente) -> None:
    token = cliente.post("/auth/registro", json=JUGADOR).json()["tokens"]["access_token"]
    respuesta = cliente.patch(
        "/auth/nivel-estimado",
        json={"nivel": 5, "rango": "Experto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 422


def test_crear_tablas_agrega_columna_rol_a_base_vieja() -> None:
    # Una base creada antes de que existiera `usuario.rol` tiene que seguir sirviendo.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conexion:
        conexion.execute(text(
            "CREATE TABLE usuario (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, nombre VARCHAR NOT NULL, "
            "password_hash VARCHAR NOT NULL, creado_en DATETIME, activo BOOLEAN NOT NULL)"
        ))
        conexion.execute(text(
            "INSERT INTO usuario (email, nombre, password_hash, activo) VALUES ('viejo@test.com', 'Viejo', 'x', 1)"
        ))
    crear_tablas(engine)
    with engine.connect() as conexion:
        fila = conexion.execute(
            text("SELECT rol, nivel_estimado, rango_estimado FROM usuario WHERE email = 'viejo@test.com'")
        ).one()
    assert fila.rol == "jugador"
    assert fila.nivel_estimado is None
    assert fila.rango_estimado is None


def test_google_login_crea_jugador_por_defecto(cliente) -> None:
    res = cliente.post("/auth/google", json={"credential": "demo_nuevo.jugador@gmail.com", "rol_seleccionado": "jugador"})
    assert res.status_code == 200
    datos = res.json()
    assert datos["usuario"]["email"] == "nuevo.jugador@gmail.com"
    assert datos["usuario"]["rol"] == "jugador"
    assert datos["usuario"]["google_id"] is not None
    assert datos["tokens"]["access_token"]


def test_google_login_vincula_cuenta_existente_y_preserva_rol(cliente) -> None:
    # 1. Se registra previamente con correo y contraseña
    cliente.post("/auth/registro", json={"email": "vinculado@test.com", "nombre": "Vinculado", "password": "pass1234"})
    
    # 2. Inicia sesión con Google usando el mismo correo
    res = cliente.post("/auth/google", json={"credential": "demo_vinculado@test.com"})
    assert res.status_code == 200
    datos = res.json()
    assert datos["usuario"]["email"] == "vinculado@test.com"
    assert datos["usuario"]["rol"] == "jugador"
    assert datos["usuario"]["google_id"] is not None


def test_google_login_intento_facilitador_sin_clave_falla(cliente) -> None:
    res = cliente.post(
        "/auth/google",
        json={"credential": "demo_intruso@gmail.com", "rol_seleccionado": "facilitador", "clave_facilitador": "clave_erronea"},
    )
    assert res.status_code == 400
    assert "incorrecto" in res.json()["detail"].lower()


def test_google_login_facilitador_con_clave_valida_entra(cliente) -> None:
    res = cliente.post(
        "/auth/google",
        json={"credential": "demo_docente.nuevo@gmail.com", "rol_seleccionado": "facilitador", "clave_facilitador": "admin123"},
    )
    assert res.status_code == 200
    datos = res.json()
    assert datos["usuario"]["rol"] == "facilitador"

