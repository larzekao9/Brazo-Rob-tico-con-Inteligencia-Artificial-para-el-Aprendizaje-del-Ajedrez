"""Panel de control del brazo (`/brazo/control`): conexión, telemetría, parámetros, configuraciones y mover una pieza. Solo facilitador."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.brazo import control_brazo
from backend.servicios.brazo.control_brazo import ErrorControl

router = APIRouter(prefix="/brazo/control", tags=["brazo-control"], dependencies=[Depends(get_current_facilitador)])


def _llamar(funcion, *args, **kwargs):
    try:
        return funcion(*args, **kwargs)
    except ErrorControl as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje) from error


class ConectarRequest(BaseModel):
    host: str = Field("192.168.5.1", max_length=100)
    puerto: int = Field(29999, ge=1, le=65535)
    emulador: bool = False


class ParametrosRequest(BaseModel):
    valores: dict
    guardar: bool = False


class PinzaRequest(BaseModel):
    accion: str
    ancho_mm: float | None = None


class ConfiguracionRequest(BaseModel):
    nombre: str
    descripcion: str = ""


class MoverPiezaRequest(BaseModel):
    origen: str = Field(max_length=2)
    destino: str = Field(max_length=2)
    tipo_pieza: str = Field("p", max_length=1)


@router.get("/estado")
def estado() -> dict:
    return control_brazo.estado()


@router.post("/conectar")
def conectar(cuerpo: ConectarRequest) -> dict:
    return _llamar(control_brazo.conectar, cuerpo.host, cuerpo.puerto, cuerpo.emulador)


@router.post("/desconectar")
def desconectar() -> dict:
    return _llamar(control_brazo.desconectar)


@router.post("/habilitar")
def habilitar() -> dict:
    return _llamar(control_brazo.habilitar)


@router.post("/deshabilitar")
def deshabilitar() -> dict:
    return _llamar(control_brazo.deshabilitar)


@router.post("/limpiar-error")
def limpiar_error() -> dict:
    return _llamar(control_brazo.limpiar_error)


@router.post("/parar")
def parar() -> dict:
    return _llamar(control_brazo.parar)


@router.get("/parametros")
def parametros() -> dict:
    return _llamar(control_brazo.parametros)


@router.put("/parametros")
def actualizar_parametros(cuerpo: ParametrosRequest) -> dict:
    return _llamar(control_brazo.actualizar_parametros, cuerpo.valores, cuerpo.guardar)


@router.post("/pinza/inicializar")
def inicializar_pinza() -> dict:
    return _llamar(control_brazo.inicializar_pinza)


@router.post("/pinza")
def mover_pinza(cuerpo: PinzaRequest) -> dict:
    return _llamar(control_brazo.mover_pinza, cuerpo.accion, cuerpo.ancho_mm)


@router.get("/configuraciones")
def listar_configuraciones() -> list[dict]:
    return _llamar(control_brazo.listar_configuraciones)


@router.post("/configuraciones")
def guardar_configuracion(cuerpo: ConfiguracionRequest) -> list[dict]:
    return _llamar(control_brazo.guardar_configuracion, cuerpo.nombre, cuerpo.descripcion)


@router.post("/configuraciones/{nombre}/aplicar")
def aplicar_configuracion(nombre: str) -> dict:
    return _llamar(control_brazo.aplicar_configuracion, nombre)


@router.delete("/configuraciones/{nombre}")
def borrar_configuracion(nombre: str) -> list[dict]:
    return _llamar(control_brazo.borrar_configuracion, nombre)


@router.post("/mover-pieza/ensayo")
def ensayo(cuerpo: MoverPiezaRequest) -> list[dict]:
    return _llamar(control_brazo.plan_de_movimiento, cuerpo.origen, cuerpo.destino, cuerpo.tipo_pieza)


@router.post("/mover-pieza")
def mover_pieza(cuerpo: MoverPiezaRequest) -> dict:
    return _llamar(control_brazo.mover_pieza, cuerpo.origen, cuerpo.destino, cuerpo.tipo_pieza)
