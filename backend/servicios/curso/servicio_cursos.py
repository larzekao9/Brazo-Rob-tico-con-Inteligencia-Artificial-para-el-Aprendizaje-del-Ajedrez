"""Cursos: el vínculo entre un facilitador y sus estudiantes.

Un facilitador crea cursos y cada uno tiene un **código** que se le da a la clase. El jugador lo escribe y queda
inscrito; desde ahí ve los videos y recibe el tono de enseñanza de ese facilitador. Un jugador está en un solo
curso a la vez (entrar a otro lo mueve).

El código del curso sirve para muchos y se puede volver a ver, a diferencia de los de facilitador
(`servicio_invitaciones`, de un solo uso): un curso de 30 alumnos no puede gastar un código por persona. Por eso
se guarda en claro; lo único que da es entrar a la clase como jugador. Para frenar a quien pruebe códigos, la
ruta usa el mismo límite de intentos por IP que los códigos de facilitador.
"""
from __future__ import annotations

import secrets

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import CursoORM, InscripcionORM, UsuarioORM
from backend.servicios.auth.servicio_auth import es_correo_de_principal
from backend.servicios.auth.servicio_invitaciones import ALFABETO, normalizar_codigo
from backend.servicios.facilitador.servicio_videos import listar_videos_piezas

LONGITUD_CODIGO_CURSO = 6
MAX_CURSOS_POR_FACILITADOR = 20
PRESETS_VALIDOS = ("infantil", "estandar", "adultos")

MENSAJE_CODIGO_INVALIDO = "Código de curso inválido o el curso no está aceptando ingresos."


class ErrorCurso(ValueError):
    """Un pedido sobre cursos que no se puede cumplir (el mensaje es apto para mostrarle al usuario)."""


def formatear_codigo(codigo: str) -> str:
    """`K7QM4T` -> `K7Q-M4T`, como se muestra en pantalla."""
    mitad = len(codigo) // 2
    return f"{codigo[:mitad]}-{codigo[mitad:]}"


def _codigo_nuevo(db: Session) -> str:
    while True:
        codigo = "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD_CODIGO_CURSO))
        if db.scalar(select(CursoORM.id).where(CursoORM.codigo == codigo)) is None:
            return codigo


def _nombre_valido(nombre: str) -> str:
    nombre = (nombre or "").strip()
    if not 2 <= len(nombre) <= 80:
        raise ErrorCurso("El nombre del curso tiene que tener entre 2 y 80 caracteres")
    return nombre


def es_principal(usuario: UsuarioORM) -> bool:
    """`True` si `usuario` es un facilitador principal activo (su correo está en `CORREOS_FACILITADORES`).

    El principal ve y administra los cursos de todos los facilitadores y puede asignar un curso a otro facilitador;
    los demás facilitadores solo tocan los suyos.
    """
    return usuario.rol == "facilitador" and bool(usuario.activo) and es_correo_de_principal(usuario.email)


def facilitador_asignable(db: Session, facilitador_id: int) -> UsuarioORM:
    """El facilitador al que se le puede asignar un curso.

    Raises:
        ErrorCurso: si no existe, no es facilitador o su cuenta está inactiva.
    """
    facilitador = db.get(UsuarioORM, facilitador_id)
    if facilitador is None or facilitador.rol != "facilitador" or not facilitador.activo:
        raise ErrorCurso("Ese facilitador no existe o está inactivo")
    return facilitador


def _exigir_cupo(db: Session, facilitador_id: int) -> None:
    cantidad = db.scalar(select(func.count()).select_from(CursoORM).where(CursoORM.facilitador_id == facilitador_id))
    if cantidad >= MAX_CURSOS_POR_FACILITADOR:
        raise ErrorCurso(f"Ese facilitador llegó al máximo de {MAX_CURSOS_POR_FACILITADOR} cursos")


# --- facilitador ----------------------------------------------------------------------------------------------
def crear_curso(db: Session, facilitador_id: int, nombre: str) -> CursoORM:
    """Crea un curso del facilitador con un código nuevo.

    Raises:
        ErrorCurso: si el nombre no es válido o ya tiene el máximo de cursos.
    """
    nombre = _nombre_valido(nombre)
    _exigir_cupo(db, facilitador_id)
    curso = CursoORM(nombre=nombre, facilitador_id=facilitador_id, codigo=_codigo_nuevo(db))
    db.add(curso)
    db.commit()
    db.refresh(curso)
    return curso


def obtener_curso_de_facilitador(db: Session, curso_id: int, facilitador_id: int, es_principal: bool = False) -> CursoORM:
    """El curso, solo si es de ese facilitador (o de cualquiera, si quien pide es principal).

    Raises:
        ErrorCurso: si no existe o es de otro facilitador (no se distingue, para no revelar cursos ajenos).
    """
    curso = db.get(CursoORM, curso_id)
    if curso is None or (curso.facilitador_id != facilitador_id and not es_principal):
        raise ErrorCurso("Curso no encontrado")
    return curso


def listar_cursos(db: Session, facilitador_id: int | None = None) -> list[dict]:
    """Los cursos del facilitador con la cantidad de estudiantes de cada uno; con `facilitador_id=None`, los de todos."""
    consulta = select(CursoORM).order_by(CursoORM.id)
    if facilitador_id is not None:
        consulta = consulta.where(CursoORM.facilitador_id == facilitador_id)
    cursos = db.scalars(consulta).all()
    if not cursos:
        return []
    cantidades = dict(
        db.execute(
            select(InscripcionORM.curso_id, func.count())
            .where(InscripcionORM.curso_id.in_([c.id for c in cursos]))
            .group_by(InscripcionORM.curso_id)
        ).all()
    )
    return [{"curso": c, "estudiantes": cantidades.get(c.id, 0)} for c in cursos]


def actualizar_curso(
    db: Session, curso: CursoORM, nombre: str | None = None, acepta_ingresos: bool | None = None
) -> CursoORM:
    """Cambia el nombre y/o abre y cierra los ingresos (cerrado: el código no deja entrar a nadie más)."""
    if nombre is not None:
        curso.nombre = _nombre_valido(nombre)
    if acepta_ingresos is not None:
        curso.acepta_ingresos = acepta_ingresos
    db.commit()
    db.refresh(curso)
    return curso


def reasignar_curso(db: Session, curso: CursoORM, facilitador_id: int) -> CursoORM:
    """Pasa el curso a otro facilitador. Sus estudiantes siguen inscritos y desde ahí reciben los videos y el tono
    del nuevo facilitador.

    Raises:
        ErrorCurso: si el destino no es un facilitador activo o ya tiene el máximo de cursos.
    """
    if facilitador_id == curso.facilitador_id:
        return curso
    facilitador_asignable(db, facilitador_id)
    _exigir_cupo(db, facilitador_id)
    curso.facilitador_id = facilitador_id
    db.commit()
    db.refresh(curso)
    return curso


def regenerar_codigo(db: Session, curso: CursoORM) -> CursoORM:
    """Cambia el código del curso: el anterior deja de servir (los que ya están inscritos siguen)."""
    curso.codigo = _codigo_nuevo(db)
    db.commit()
    db.refresh(curso)
    return curso


def eliminar_curso(db: Session, curso: CursoORM) -> int:
    """Borra el curso; sus estudiantes quedan sin curso (no se borra a nadie). Devuelve cuántos se desinscribieron."""
    desinscritos = db.execute(delete(InscripcionORM).where(InscripcionORM.curso_id == curso.id)).rowcount
    db.delete(curso)
    db.commit()
    return desinscritos


def estudiantes_del_curso(db: Session, curso: CursoORM) -> list[dict]:
    """Los jugadores inscritos, con lo que el facilitador necesita para seguirlos."""
    filas = db.execute(
        select(UsuarioORM, InscripcionORM.unido_en)
        .join(InscripcionORM, InscripcionORM.usuario_id == UsuarioORM.id)
        .where(InscripcionORM.curso_id == curso.id)
        .order_by(UsuarioORM.nombre)
    ).all()
    return [{"usuario": usuario, "unido_en": unido_en} for usuario, unido_en in filas]


def quitar_estudiante(db: Session, curso: CursoORM, usuario_id: int) -> bool:
    """Saca a un estudiante del curso. `False` si no estaba inscrito en él."""
    resultado = db.execute(
        delete(InscripcionORM).where(InscripcionORM.curso_id == curso.id, InscripcionORM.usuario_id == usuario_id)
    )
    db.commit()
    return resultado.rowcount == 1


# --- jugador --------------------------------------------------------------------------------------------------
def unirse_con_codigo(db: Session, usuario: UsuarioORM, codigo: str) -> CursoORM:
    """Inscribe al jugador en el curso del código; si ya estaba en otro, lo mueve.

    Raises:
        ErrorCurso: si no es jugador, o el código no existe o el curso cerró los ingresos (el mensaje no
            distingue cuál, a propósito).
    """
    if usuario.rol != "jugador":
        raise ErrorCurso("Solo los jugadores se inscriben en un curso")
    normalizado = normalizar_codigo(codigo or "")
    curso = db.scalar(select(CursoORM).where(CursoORM.codigo == normalizado)) if normalizado else None
    if curso is None or not curso.acepta_ingresos:
        raise ErrorCurso(MENSAJE_CODIGO_INVALIDO)
    inscripcion = db.scalar(select(InscripcionORM).where(InscripcionORM.usuario_id == usuario.id))
    if inscripcion is None:
        db.add(InscripcionORM(curso_id=curso.id, usuario_id=usuario.id))
    else:
        inscripcion.curso_id = curso.id
    db.commit()
    return curso


def salir_del_curso(db: Session, usuario_id: int) -> bool:
    """El jugador deja su curso. `False` si no estaba en ninguno."""
    resultado = db.execute(delete(InscripcionORM).where(InscripcionORM.usuario_id == usuario_id))
    db.commit()
    return resultado.rowcount == 1


def curso_de(db: Session, usuario_id: int) -> CursoORM | None:
    """El curso en el que está inscrito el jugador, o `None`."""
    return db.scalar(
        select(CursoORM)
        .join(InscripcionORM, InscripcionORM.curso_id == CursoORM.id)
        .where(InscripcionORM.usuario_id == usuario_id)
    )


def facilitador_de_curso(db: Session, curso: CursoORM) -> UsuarioORM:
    """El facilitador dueño del curso."""
    return db.get(UsuarioORM, curso.facilitador_id)


def facilitador_de(db: Session, usuario_id: int) -> UsuarioORM | None:
    """El facilitador del curso del jugador, o `None` si no está en ninguno."""
    curso = curso_de(db, usuario_id)
    return facilitador_de_curso(db, curso) if curso else None


def facilitadores_principales(db: Session) -> list[UsuarioORM]:
    """Los facilitadores principales activos, del más antiguo al más nuevo (por id)."""
    facilitadores = db.scalars(
        select(UsuarioORM).where(UsuarioORM.rol == "facilitador", UsuarioORM.activo.is_(True)).order_by(UsuarioORM.id)
    ).all()
    return [f for f in facilitadores if es_principal(f)]


def videos_visibles(db: Session, usuario_id: int) -> dict[str, str]:
    """Videos por pieza que le corresponde ver a `usuario_id`: `tipo_pieza -> url`.

    Los **generales** son los del facilitador principal (si hay varios principales, vale el del más antiguo que haya
    subido esa pieza). Si el usuario está en un curso, el video que su facilitador subió para una pieza **reemplaza**
    al general de esa pieza; las demás siguen siendo las generales. Así quien juega por su cuenta, sin curso, también
    ve los videos. Cada URL lleva `?v=` (ver `listar_videos_piezas`).
    """
    videos: dict[str, str] = {}
    facilitador = facilitador_de(db, usuario_id)
    if facilitador is not None:
        videos.update(listar_videos_piezas(facilitador.id, con_version=True))
    for principal in facilitadores_principales(db):
        for pieza, url in listar_videos_piezas(principal.id, con_version=True).items():
            videos.setdefault(pieza, url)
    return videos


def preset_efectivo(db: Session, usuario: UsuarioORM) -> str | None:
    """El tono de enseñanza que le corresponde a `usuario`.

    Un jugador inscrito en un curso recibe el de su facilitador (si lo eligió); si no, el suyo propio. Es lo que
    hace que la preferencia del facilitador llegue de verdad a sus estudiantes.
    """
    if usuario.rol == "jugador":
        facilitador = facilitador_de(db, usuario.id)
        if facilitador is not None and facilitador.preset_ensenanza in PRESETS_VALIDOS:
            return facilitador.preset_ensenanza
    return usuario.preset_ensenanza


def retirar_usuario_de_cursos(db: Session, usuario_id: int) -> None:
    """Limpieza al eliminar una cuenta (sin hacer commit): si es jugador, sale de su curso; si es facilitador, se
    borran sus cursos y se desinscribe a sus estudiantes."""
    db.execute(delete(InscripcionORM).where(InscripcionORM.usuario_id == usuario_id))
    ids_cursos = db.scalars(select(CursoORM.id).where(CursoORM.facilitador_id == usuario_id)).all()
    if ids_cursos:
        db.execute(delete(InscripcionORM).where(InscripcionORM.curso_id.in_(ids_cursos)))
        db.execute(delete(CursoORM).where(CursoORM.id.in_(ids_cursos)))
