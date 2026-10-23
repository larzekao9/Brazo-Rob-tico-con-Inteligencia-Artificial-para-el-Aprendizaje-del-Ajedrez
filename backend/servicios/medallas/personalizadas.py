"""Lectura de las medallas propias (creadas por facilitadores) como objetos `Medalla`, igual que las de fábrica.

Solo lee la base; la creación, edición y entrega manual están en `servicio_creacion`.
"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import MedallaGanadaORM, MedallaPersonalizadaORM
from backend.servicios.curso import servicio_cursos
from backend.servicios.medallas.catalogo import Medalla, medidor_de_regla


def a_medalla(fila: MedallaPersonalizadaORM) -> Medalla:
    """La fila de la base como una `Medalla` del catálogo (con su función de medición según la regla)."""
    return Medalla(
        codigo=fila.codigo, nombre=fila.nombre, descripcion=fila.descripcion, nivel=fila.nivel, pieza=fila.pieza,
        meta=fila.meta, medir=medidor_de_regla(fila.regla),
    )


def todas(db: Session) -> list[Medalla]:
    """Todas las medallas propias que existen."""
    return [a_medalla(f) for f in db.scalars(select(MedallaPersonalizadaORM).order_by(MedallaPersonalizadaORM.id)).all()]


def visibles_para(db: Session, usuario_id: int) -> list[Medalla]:
    """Las medallas propias que ve `usuario_id`: las generales, las de los cursos de su facilitador y las que ya ganó."""
    ganadas = select(MedallaGanadaORM.codigo).where(MedallaGanadaORM.usuario_id == usuario_id)
    condicion = or_(MedallaPersonalizadaORM.general.is_(True), MedallaPersonalizadaORM.codigo.in_(ganadas))
    facilitador = servicio_cursos.facilitador_de(db, usuario_id)
    if facilitador is not None:
        condicion = or_(condicion, MedallaPersonalizadaORM.creada_por == facilitador.id)
    filas = db.scalars(select(MedallaPersonalizadaORM).where(condicion).order_by(MedallaPersonalizadaORM.id)).all()
    return [a_medalla(f) for f in filas]
