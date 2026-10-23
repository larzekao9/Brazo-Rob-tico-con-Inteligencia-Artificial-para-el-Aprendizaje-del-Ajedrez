"""Medallas propias: un facilitador crea las suyas, las edita, las borra y las entrega.

Las generales (que ven todos los jugadores) solo las crea un facilitador principal; las demás las ven los jugadores de los
cursos de quien las creó. La imagen se sube por `POST /facilitador/medallas/{codigo}/imagen`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.esquemas.medallas_esquema import (
    CrearMedallaRequest,
    EditarMedallaRequest,
    MedallaPropiaResponse,
    OpcionesMedallaResponse,
    OtorgarMedallaRequest,
    OtorgarMedallaResponse,
)
from backend.rutas.ruta_auth import get_current_facilitador, get_db
from backend.servicios.auth import get_user_by_id
from backend.servicios.medallas import servicio_creacion as creacion
from backend.servicios.medallas.servicio_creacion import ErrorMedalla

router = APIRouter(prefix="/medallas", tags=["medallas"])


def _gestionable(db: Session, usuario_id: int, codigo: str):
    """La medalla propia y el usuario, si puede gestionarla. 404 si no existe, 403 si es de otro facilitador."""
    usuario = get_user_by_id(db, usuario_id)
    try:
        fila = creacion.obtener(db, codigo)
    except ErrorMedalla as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if not creacion.puede_gestionar(usuario, fila):
        raise HTTPException(status_code=403, detail="Esta medalla es de otro facilitador")
    return usuario, fila


def _respuesta(db: Session, usuario_id: int, codigo: str) -> MedallaPropiaResponse:
    usuario = get_user_by_id(db, usuario_id)
    return MedallaPropiaResponse(**next(m for m in creacion.listar(db, usuario) if m["codigo"] == codigo))


@router.get("/opciones", response_model=OpcionesMedallaResponse, summary="Reglas, niveles, piezas e ideas para crear medallas")
def opciones(_: int = Depends(get_current_facilitador)) -> OpcionesMedallaResponse:
    """Lo que necesita el formulario de creación: las reglas que se pueden elegir (con su rango), los niveles, las piezas,
    ideas de medalla listas para usar y los largos permitidos del nombre y la descripción."""
    return OpcionesMedallaResponse(**creacion.reglas_disponibles())


@router.get("/mias", response_model=list[MedallaPropiaResponse], summary="Las medallas propias que puedo gestionar")
def mias(usuario_id: int = Depends(get_current_facilitador), db: Session = Depends(get_db)) -> list[MedallaPropiaResponse]:
    """Las medallas creadas por el facilitador, con cuántos jugadores las ganaron. El principal ve las de todos."""
    return [MedallaPropiaResponse(**m) for m in creacion.listar(db, get_user_by_id(db, usuario_id))]


@router.post("", response_model=MedallaPropiaResponse, status_code=status.HTTP_201_CREATED, summary="Crear una medalla propia")
def crear(data: CrearMedallaRequest, usuario_id: int = Depends(get_current_facilitador), db: Session = Depends(get_db)) -> MedallaPropiaResponse:
    """Crea la medalla (sin imagen: se le sube después). 400 con el motivo si algún dato no sirve; 403 si pide una general
    sin ser principal."""
    usuario = get_user_by_id(db, usuario_id)
    if data.general and not creacion.es_principal(usuario):
        raise HTTPException(status_code=403, detail="Solo un facilitador principal puede crear medallas generales")
    try:
        fila = creacion.crear(db, usuario, data.nombre, data.descripcion, data.nivel, data.pieza, data.regla, data.meta, data.general)
    except ErrorMedalla as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _respuesta(db, usuario_id, fila.codigo)


@router.patch("/{codigo}", response_model=MedallaPropiaResponse, summary="Editar una medalla propia")
def editar(
    codigo: str, data: EditarMedallaRequest, usuario_id: int = Depends(get_current_facilitador), db: Session = Depends(get_db)
) -> MedallaPropiaResponse:
    """Cambia lo que venga. Los jugadores que ya la ganaron la conservan aunque cambie la regla."""
    _, fila = _gestionable(db, usuario_id, codigo)
    try:
        creacion.editar(db, fila, data.nombre, data.descripcion, data.nivel, data.pieza, data.regla, data.meta)
    except ErrorMedalla as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _respuesta(db, usuario_id, codigo)


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT, summary="Borrar una medalla propia")
def borrar(codigo: str, usuario_id: int = Depends(get_current_facilitador), db: Session = Depends(get_db)) -> Response:
    """Borra la medalla, su imagen y las veces que se ganó (los jugadores la pierden)."""
    _, fila = _gestionable(db, usuario_id, codigo)
    creacion.eliminar(db, fila)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{codigo}/otorgar", response_model=OtorgarMedallaResponse, summary="Entregar una medalla manual")
def otorgar(
    codigo: str, data: OtorgarMedallaRequest, usuario_id: int = Depends(get_current_facilitador), db: Session = Depends(get_db)
) -> OtorgarMedallaResponse:
    """Entrega una medalla manual a jugadores concretos y/o a todo un curso. Solo a jugadores de los cursos del facilitador
    (el principal, a cualquiera). Los que ya la tenían no se repiten; a los demás les aparece el aviso de medalla nueva."""
    usuario, fila = _gestionable(db, usuario_id, codigo)
    try:
        return OtorgarMedallaResponse(**creacion.otorgar_manual(db, usuario, fila, data.usuario_ids, data.curso_id))
    except ErrorMedalla as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
