"""Medallas propias: un facilitador crea, edita, borra y entrega medallas.

El principal crea medallas **generales** (las ven todos los jugadores); cualquier facilitador crea medallas **para sus
cursos** (las ven los jugadores de sus cursos). El facilitador solo elige la regla de una lista (o `manual`): nunca escribe
código. Quien creó la medalla (o el principal) puede cambiarla, subirle la imagen y borrarla.
"""
from __future__ import annotations

import secrets

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import CursoORM, InscripcionORM, MedallaGanadaORM, MedallaPersonalizadaORM, UsuarioORM
from backend.servicios.curso.servicio_cursos import es_principal
from backend.servicios.medallas import servicio_medallas
from backend.servicios.medallas.catalogo import CATALOGO, NIVELES, PIEZAS, PLANTILLAS, REGLA_MANUAL, REGLAS

MAX_MEDALLAS_POR_FACILITADOR = 30
LARGO_NOMBRE = (2, 30)
LARGO_DESCRIPCION = (5, 80)


class ErrorMedalla(ValueError):
    """Un pedido sobre medallas que no se puede cumplir (el mensaje es apto para mostrárselo al facilitador)."""


def reglas_disponibles() -> dict:
    """Lo que necesita la pantalla de creación: reglas elegibles, niveles, piezas e ideas listas para usar."""
    return {
        "reglas": [{"codigo": codigo, **datos} for codigo, datos in REGLAS.items()]
        + [{"codigo": REGLA_MANUAL, "nombre": "Manual: la entrego yo", "tipo": "manual"}],
        "niveles": list(NIVELES),
        "piezas": list(PIEZAS),
        "plantillas": [dict(p) for p in PLANTILLAS],
        "largo_nombre": list(LARGO_NOMBRE),
        "largo_descripcion": list(LARGO_DESCRIPCION),
    }


def _texto(valor: str, rango: tuple[int, int], que: str) -> str:
    valor = " ".join((valor or "").split())
    if not rango[0] <= len(valor) <= rango[1]:
        raise ErrorMedalla(f"{que} tiene que tener entre {rango[0]} y {rango[1]} caracteres")
    return valor


def _regla_y_meta(regla: str, meta: int) -> tuple[str, int]:
    if regla == REGLA_MANUAL:
        return regla, 1
    if regla not in REGLAS:
        raise ErrorMedalla("Regla inválida: elegí una de la lista")
    datos = REGLAS[regla]
    if datos["tipo"] == "si_no":
        return regla, 1
    if not isinstance(meta, int) or isinstance(meta, bool) or not datos["minimo"] <= meta <= datos["maximo"]:
        raise ErrorMedalla(f"La cantidad para «{datos['nombre']}» tiene que estar entre {datos['minimo']} y {datos['maximo']}")
    return regla, meta


def _codigo_nuevo(db: Session) -> str:
    while True:
        codigo = f"propia_{secrets.token_hex(4)}"
        if db.scalar(select(MedallaPersonalizadaORM.id).where(MedallaPersonalizadaORM.codigo == codigo)) is None:
            return codigo


def obtener(db: Session, codigo: str) -> MedallaPersonalizadaORM:
    """La medalla propia con ese código.

    Raises:
        ErrorMedalla: si no existe (las 13 de fábrica no se editan ni se borran: solo se les cambia la imagen).
    """
    fila = db.scalar(select(MedallaPersonalizadaORM).where(MedallaPersonalizadaORM.codigo == codigo))
    if fila is None:
        raise ErrorMedalla("Medalla no encontrada")
    return fila


def puede_gestionar(usuario: UsuarioORM, fila: MedallaPersonalizadaORM) -> bool:
    """El creador de la medalla o un facilitador principal."""
    return usuario.id == fila.creada_por or es_principal(usuario)


def puede_cambiar_imagen(db: Session, usuario: UsuarioORM, codigo: str) -> bool:
    """Las de fábrica, solo el principal; las propias, su creador o el principal. Con un código que no existe, el principal pasa
    (y el servicio responde que la medalla no existe); los demás facilitadores no."""
    if codigo in {m.codigo for m in CATALOGO}:
        return es_principal(usuario)
    fila = db.scalar(select(MedallaPersonalizadaORM).where(MedallaPersonalizadaORM.codigo == codigo))
    return puede_gestionar(usuario, fila) if fila is not None else es_principal(usuario)


def crear(
    db: Session, creador: UsuarioORM, nombre: str, descripcion: str, nivel: str, pieza: str, regla: str, meta: int, general: bool
) -> MedallaPersonalizadaORM:
    """Crea una medalla propia.

    Raises:
        ErrorMedalla: si algún dato no es válido, el facilitador llegó al máximo de medallas o intenta crear una general sin
            ser principal.
    """
    if general and not es_principal(creador):
        raise ErrorMedalla("Solo un facilitador principal puede crear medallas generales")
    if nivel not in NIVELES or pieza not in PIEZAS:
        raise ErrorMedalla("Nivel o pieza inválidos")
    regla, meta = _regla_y_meta(regla, meta)
    cantidad = db.scalar(select(func.count()).select_from(MedallaPersonalizadaORM).where(MedallaPersonalizadaORM.creada_por == creador.id))
    if cantidad >= MAX_MEDALLAS_POR_FACILITADOR:
        raise ErrorMedalla(f"Llegaste al máximo de {MAX_MEDALLAS_POR_FACILITADOR} medallas propias")
    fila = MedallaPersonalizadaORM(
        codigo=_codigo_nuevo(db), nombre=_texto(nombre, LARGO_NOMBRE, "El nombre"),
        descripcion=_texto(descripcion, LARGO_DESCRIPCION, "La descripción"), nivel=nivel, pieza=pieza, regla=regla, meta=meta,
        general=general, creada_por=creador.id,
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def editar(
    db: Session, fila: MedallaPersonalizadaORM, nombre: str | None, descripcion: str | None, nivel: str | None,
    pieza: str | None, regla: str | None, meta: int | None,
) -> MedallaPersonalizadaORM:
    """Cambia lo que venga. Las medallas que alguien ya ganó se conservan aunque cambie la regla.

    Raises:
        ErrorMedalla: si algún dato no es válido.
    """
    if nombre is not None:
        fila.nombre = _texto(nombre, LARGO_NOMBRE, "El nombre")
    if descripcion is not None:
        fila.descripcion = _texto(descripcion, LARGO_DESCRIPCION, "La descripción")
    if nivel is not None:
        if nivel not in NIVELES:
            raise ErrorMedalla("Nivel inválido")
        fila.nivel = nivel
    if pieza is not None:
        if pieza not in PIEZAS:
            raise ErrorMedalla("Pieza inválida")
        fila.pieza = pieza
    if regla is not None or meta is not None:
        fila.regla, fila.meta = _regla_y_meta(regla if regla is not None else fila.regla, meta if meta is not None else fila.meta)
    db.commit()
    db.refresh(fila)
    return fila


def eliminar(db: Session, fila: MedallaPersonalizadaORM) -> int:
    """Borra la medalla, su imagen y las veces que se ganó. Devuelve cuántos jugadores la tenían."""
    ganadas = db.execute(delete(MedallaGanadaORM).where(MedallaGanadaORM.codigo == fila.codigo)).rowcount
    servicio_medallas.borrar_imagen(fila.codigo)
    db.delete(fila)
    db.commit()
    return ganadas


def listar(db: Session, usuario: UsuarioORM) -> list[dict]:
    """Las medallas propias que puede gestionar `usuario` (el principal, todas), con cuántos jugadores las ganaron."""
    consulta = select(MedallaPersonalizadaORM).order_by(MedallaPersonalizadaORM.id)
    if not es_principal(usuario):
        consulta = consulta.where(MedallaPersonalizadaORM.creada_por == usuario.id)
    filas = db.scalars(consulta).all()
    ganadas = dict(
        db.execute(
            select(MedallaGanadaORM.codigo, func.count()).where(MedallaGanadaORM.codigo.in_([f.codigo for f in filas])).group_by(MedallaGanadaORM.codigo)
        ).all()
    ) if filas else {}
    creadores = {u.id: u.nombre for u in db.scalars(select(UsuarioORM).where(UsuarioORM.id.in_({f.creada_por for f in filas}))).all()} if filas else {}
    return [
        {
            "codigo": f.codigo, "nombre": f.nombre, "descripcion": f.descripcion, "nivel": f.nivel, "pieza": f.pieza,
            "regla": f.regla, "regla_nombre": "Manual" if f.regla == REGLA_MANUAL else REGLAS[f.regla]["nombre"], "meta": f.meta,
            "general": f.general, "creada_por": f.creada_por, "creador_nombre": creadores.get(f.creada_por, ""),
            "es_mia": f.creada_por == usuario.id, "ganada_por": int(ganadas.get(f.codigo, 0)),
            "imagen_url": servicio_medallas.url_imagen(f.codigo),
        }
        for f in filas
    ]


def otorgar_manual(
    db: Session, usuario: UsuarioORM, fila: MedallaPersonalizadaORM, usuario_ids: list[int], curso_id: int | None
) -> dict:
    """Entrega una medalla manual a jugadores concretos o a todos los de un curso.

    Un facilitador solo puede entregarla a jugadores de sus cursos (el principal, a cualquier jugador). Los que ya la tenían
    no se repiten.

    Raises:
        ErrorMedalla: si la medalla no es manual, no se indicó a quién, el curso no es suyo o algún jugador no es válido.
    """
    if fila.regla != REGLA_MANUAL:
        raise ErrorMedalla("Solo las medallas manuales se entregan a mano: las demás se ganan jugando")
    ids = set(usuario_ids)
    if curso_id is not None:
        curso = db.get(CursoORM, curso_id)
        if curso is None or (curso.facilitador_id != usuario.id and not es_principal(usuario)):
            raise ErrorMedalla("Curso no encontrado")
        ids |= set(db.scalars(select(InscripcionORM.usuario_id).where(InscripcionORM.curso_id == curso_id)).all())
    if not ids:
        raise ErrorMedalla("Elegí a quién se la das: un curso o jugadores")
    jugadores = {u.id for u in db.scalars(select(UsuarioORM).where(UsuarioORM.id.in_(ids), UsuarioORM.rol == "jugador", UsuarioORM.activo.is_(True))).all()}
    if jugadores != ids and curso_id is None:
        raise ErrorMedalla("Alguno de los jugadores elegidos no existe o está inactivo")
    if not es_principal(usuario):
        propios = set(
            db.scalars(
                select(InscripcionORM.usuario_id).join(CursoORM, CursoORM.id == InscripcionORM.curso_id).where(CursoORM.facilitador_id == usuario.id)
            ).all()
        )
        if not jugadores <= propios:
            raise ErrorMedalla("Solo podés entregarla a jugadores de tus cursos")
    ya = set(db.scalars(select(MedallaGanadaORM.usuario_id).where(MedallaGanadaORM.codigo == fila.codigo, MedallaGanadaORM.usuario_id.in_(jugadores))).all())
    nuevos = jugadores - ya
    for jugador_id in nuevos:
        db.add(MedallaGanadaORM(usuario_id=jugador_id, codigo=fila.codigo, ganada_en=servicio_medallas._ahora()))
    db.commit()
    return {"otorgadas": len(nuevos), "ya_la_tenian": len(ya)}


def retirar_usuario_de_medallas(db: Session, usuario_id: int) -> None:
    """Limpieza al eliminar una cuenta (sin hacer commit): se borran sus medallas ganadas y, si es facilitador, sus medallas
    propias con sus imágenes y las veces que se ganaron."""
    db.execute(delete(MedallaGanadaORM).where(MedallaGanadaORM.usuario_id == usuario_id))
    for fila in db.scalars(select(MedallaPersonalizadaORM).where(MedallaPersonalizadaORM.creada_por == usuario_id)).all():
        db.execute(delete(MedallaGanadaORM).where(MedallaGanadaORM.codigo == fila.codigo))
        servicio_medallas.borrar_imagen(fila.codigo)
        db.delete(fila)
