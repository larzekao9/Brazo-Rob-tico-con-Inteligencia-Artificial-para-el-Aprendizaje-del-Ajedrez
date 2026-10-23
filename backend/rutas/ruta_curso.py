"""Cursos: el facilitador arma sus grupos y el jugador entra con un código.

Las rutas de `/cursos/mio...`, `/cursos/unirse` y `/cursos/salir` son del jugador; las demás, del facilitador
(un facilitador solo ve y toca sus propios cursos).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.database import fecha_a_iso
from backend.esquemas.curso_esquema import (
    CrearCursoRequest,
    CursoDelJugadorResponse,
    CursoResponse,
    EditarCursoRequest,
    EstudianteDeCursoResponse,
    UnirseCursoRequest,
)
from backend.modelos.tablas_orm import CursoORM
from backend.rutas.ruta_auth import _cliente_de, _exigir_intentos_disponibles, get_current_facilitador, get_current_user, get_db
from backend.servicios.auth import get_user_by_id
from backend.servicios.auth.servicio_invitaciones import registrar_intento_fallido
from backend.servicios.curso import servicio_cursos as cursos
from backend.servicios.curso.servicio_cursos import ErrorCurso

router = APIRouter(prefix="/cursos", tags=["cursos"])


def _respuesta_curso(db: Session, curso: CursoORM, estudiantes: int) -> CursoResponse:
    dueno = cursos.facilitador_de_curso(db, curso)
    return CursoResponse(
        id=curso.id,
        nombre=curso.nombre,
        codigo=cursos.formatear_codigo(curso.codigo),
        acepta_ingresos=curso.acepta_ingresos,
        estudiantes=estudiantes,
        creado_en=fecha_a_iso(curso.creado_en),
        facilitador_id=curso.facilitador_id,
        facilitador_nombre=dueno.nombre if dueno else "",
    )


def _es_principal(db: Session, facilitador_id: int) -> bool:
    return cursos.es_principal(get_user_by_id(db, facilitador_id))


def _del_facilitador(db: Session, curso_id: int, facilitador_id: int) -> CursoORM:
    """El curso si es del facilitador; un facilitador principal puede con el de cualquiera. 404 si no."""
    try:
        return cursos.obtener_curso_de_facilitador(db, curso_id, facilitador_id, _es_principal(db, facilitador_id))
    except ErrorCurso as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _exigir_principal(db: Session, facilitador_id: int, que: str) -> None:
    if not _es_principal(db, facilitador_id):
        raise HTTPException(status_code=403, detail=f"Solo un facilitador principal puede {que}")


def _respuesta_del_jugador(db: Session, curso: CursoORM) -> CursoDelJugadorResponse:
    facilitador = cursos.facilitador_de_curso(db, curso)
    return CursoDelJugadorResponse(
        id=curso.id,
        nombre=curso.nombre,
        facilitador_nombre=facilitador.nombre,
        facilitador_avatar_url=facilitador.avatar_url,
        preset_ensenanza=facilitador.preset_ensenanza,
    )


# --- jugador (las rutas fijas van antes que las de `/{curso_id}`) ----------------------------------------------
@router.post("/unirse", response_model=CursoDelJugadorResponse, summary="Entrar a un curso con su código (jugador)")
def unirse(
    data: UnirseCursoRequest,
    solicitud: Request,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CursoDelJugadorResponse:
    """Inscribe al jugador en el curso del código; si ya estaba en otro, lo cambia. Responde 400 si el código no
    sirve (no existe o el curso cerró los ingresos) y 429 si el cliente ya gastó sus intentos fallidos."""
    cliente = _cliente_de(solicitud)
    _exigir_intentos_disponibles(cliente)
    usuario = get_user_by_id(db, user_id)
    try:
        curso = cursos.unirse_con_codigo(db, usuario, data.codigo)
    except ErrorCurso as error:
        registrar_intento_fallido(cliente)
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _respuesta_del_jugador(db, curso)


@router.get("/mio", response_model=CursoDelJugadorResponse | None, summary="El curso del jugador, o null")
def mi_curso(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)) -> CursoDelJugadorResponse | None:
    """El curso en el que está inscrito el usuario autenticado, o `null` si no está en ninguno."""
    curso = cursos.curso_de(db, user_id)
    return _respuesta_del_jugador(db, curso) if curso else None


@router.get("/mio/videos", response_model=dict[str, str], summary="Videos por pieza que me corresponde ver")
def videos_para_mi(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    """Mapa `tipo_pieza -> url`. Los videos **generales** son los del facilitador principal y los ven todos los
    jugadores, con o sin curso; si el facilitador del curso del jugador subió el suyo para una pieza, ese reemplaza al
    general de esa pieza. Una pieza sin video en ninguno de los dos no aparece."""
    return cursos.videos_visibles(db, user_id)


@router.post("/salir", status_code=status.HTTP_204_NO_CONTENT, summary="Salir del curso (jugador)")
def salir(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    """El jugador deja su curso. 404 si no estaba en ninguno."""
    if not cursos.salir_del_curso(db, user_id):
        raise HTTPException(status_code=404, detail="No estás inscrito en ningún curso")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- facilitador ----------------------------------------------------------------------------------------------
@router.post("", response_model=CursoResponse, status_code=status.HTTP_201_CREATED, summary="Crear un curso (facilitador)")
def crear_curso(
    data: CrearCursoRequest,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> CursoResponse:
    """Crea un curso con su código. Máximo 20 por facilitador. Un facilitador principal puede mandar
    `facilitador_id` para crearlo a nombre de otro facilitador activo (403 si no es principal)."""
    dueno_id = data.facilitador_id if data.facilitador_id is not None else facilitador_id
    if dueno_id != facilitador_id:
        _exigir_principal(db, facilitador_id, "crear cursos para otro facilitador")
    try:
        if dueno_id != facilitador_id:
            cursos.facilitador_asignable(db, dueno_id)
        curso = cursos.crear_curso(db, dueno_id, data.nombre)
    except ErrorCurso as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _respuesta_curso(db, curso, 0)


@router.get("", response_model=list[CursoResponse], summary="Mis cursos (facilitador)")
def listar_mis_cursos(
    todos: bool = False,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> list[CursoResponse]:
    """Los cursos del facilitador con su código y cuántos estudiantes tiene cada uno. Con `?todos=true`, un
    facilitador principal ve los de todos los facilitadores (403 si no es principal)."""
    if todos:
        _exigir_principal(db, facilitador_id, "ver los cursos de todos los facilitadores")
    items = cursos.listar_cursos(db, None if todos else facilitador_id)
    return [_respuesta_curso(db, item["curso"], item["estudiantes"]) for item in items]


@router.patch("/{curso_id}", response_model=CursoResponse, summary="Renombrar, abrir/cerrar ingresos o reasignar un curso")
def editar_curso(
    curso_id: int,
    data: EditarCursoRequest,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> CursoResponse:
    """Edición parcial. `facilitador_id` pasa el curso a otro facilitador activo y solo lo puede hacer un
    facilitador principal (403 si no lo es); los estudiantes inscritos siguen en el curso."""
    curso = _del_facilitador(db, curso_id, facilitador_id)
    if data.facilitador_id is not None and data.facilitador_id != curso.facilitador_id:
        _exigir_principal(db, facilitador_id, "asignar un curso a otro facilitador")
    try:
        if data.facilitador_id is not None:
            curso = cursos.reasignar_curso(db, curso, data.facilitador_id)  # primero lo que puede fallar
        curso = cursos.actualizar_curso(db, curso, data.nombre, data.acepta_ingresos)
    except ErrorCurso as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _respuesta_curso(db, curso, len(cursos.estudiantes_del_curso(db, curso)))


@router.post("/{curso_id}/codigo", response_model=CursoResponse, summary="Generar un código nuevo para el curso")
def regenerar_codigo(
    curso_id: int,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> CursoResponse:
    """El código anterior deja de servir; los estudiantes que ya están inscritos siguen en el curso."""
    curso = cursos.regenerar_codigo(db, _del_facilitador(db, curso_id, facilitador_id))
    return _respuesta_curso(db, curso, len(cursos.estudiantes_del_curso(db, curso)))


@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un curso")
def eliminar_curso(
    curso_id: int,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> Response:
    """Borra el curso. Sus estudiantes no se borran: quedan sin curso."""
    cursos.eliminar_curso(db, _del_facilitador(db, curso_id, facilitador_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{curso_id}/estudiantes", response_model=list[EstudianteDeCursoResponse], summary="Estudiantes de un curso"
)
def estudiantes(
    curso_id: int,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> list[EstudianteDeCursoResponse]:
    curso = _del_facilitador(db, curso_id, facilitador_id)
    return [
        EstudianteDeCursoResponse(
            id=item["usuario"].id,
            nombre=item["usuario"].nombre,
            email=item["usuario"].email,
            avatar_url=item["usuario"].avatar_url,
            nivel_estimado=item["usuario"].nivel_estimado,
            rango_estimado=item["usuario"].rango_estimado,
            activo=item["usuario"].activo,
            unido_en=fecha_a_iso(item["unido_en"]),
        )
        for item in cursos.estudiantes_del_curso(db, curso)
    ]


@router.delete(
    "/{curso_id}/estudiantes/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Sacar a un estudiante del curso"
)
def quitar_estudiante(
    curso_id: int,
    usuario_id: int,
    facilitador_id: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> Response:
    """Lo saca del curso sin borrar su cuenta. 404 si no estaba inscrito en él."""
    curso = _del_facilitador(db, curso_id, facilitador_id)
    if not cursos.quitar_estudiante(db, curso, usuario_id):
        raise HTTPException(status_code=404, detail="Ese estudiante no está en el curso")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
