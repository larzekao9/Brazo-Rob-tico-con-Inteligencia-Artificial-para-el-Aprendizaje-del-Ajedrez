"""Las 4 tablas mínimas de la base de datos (PLAN_IMPLEMENTACION_COMPLETO.md, sección 7).

Son la capa de "Modelos de datos" (representan las tablas), separada a
propósito de `partida.py` — la entidad de dominio (`Partida`, un dataclass
con un `chess.Board` adentro) que ya usan `servicio_partida.py` y las rutas.
Ninguno de los dos reemplaza al otro: `RepositorioPartidasPostgres`
(`backend/repositorios/repositorio_partida.py`) es el único lugar que
traduce entre ambos, tal como pide el patrón Repository (sección 4.3) — el
resto del backend sigue sin saber que SQLAlchemy existe.

Dos diferencias deliberadas respecto al SQL literal de la sección 7,
documentadas acá para no perder el motivo:

1. `partida.id` es TEXT (el uuid hex que ya genera `Partida.id`), no
   INTEGER autoincremental — así el id no cambia entre la versión en
   memoria y la versión en Postgres.
2. `partida` suma las columnas `fen`, `nivel`, `tipo_oponente` y
   `jugadas_uci`, que hoy viven directo en el dataclass `Partida` porque
   todavía no existe ningún flujo de sesión/participante (HU10/HU11 son las
   que lo van a crear). Los campos `participante_id` y `sesion_id` quedan
   nulleables mientras tanto. `jugadas_uci` guarda la lista de jugadas (UCI,
   separadas por espacio) para poder reconstruir el `chess.Board` completo
   al leer — la tabla `jugada` de abajo es para el detalle por jugada que
   necesita RF34/HU4 (quién decidió, tiempo de cálculo, explicación), no
   para esto.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


ROLES_USUARIO = ("jugador", "facilitador")
"""Roles posibles de un usuario. `jugador` es el único que puede usar la app
móvil; `facilitador` está pensado para la Sala de Control web."""


class UsuarioORM(Base):
    """Tabla de usuarios para autenticación (email + password hash + rol)."""
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    rol: Mapped[str] = mapped_column(nullable=False, default="jugador", server_default="jugador")
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Resultado de la última "Mide tu nivel" completada (HU5/HU10) — se pisa
    # en cada diagnóstico nuevo, no se guarda historial (ver PLAN_IMPLEMENTACION_COMPLETO.md).
    nivel_estimado: Mapped[int | None] = mapped_column(nullable=True)
    rango_estimado: Mapped[str | None] = mapped_column(nullable=True)  # 'Principiante' | 'Intermedio' | 'Avanzado'

    partidas: Mapped[list["PartidaORM"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class ParticipanteORM(Base):
    __tablename__ = "participante"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(nullable=False)


class SesionORM(Base):
    __tablename__ = "sesion"

    id: Mapped[int] = mapped_column(primary_key=True)
    facilitador: Mapped[str | None] = mapped_column(nullable=True)
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    dificultad: Mapped[int | None] = mapped_column(nullable=True)  # 0-20, nivel de Stockfish
    tipo_oponente: Mapped[str | None] = mapped_column(nullable=True)  # 'motor' | 'modelo' | 'participante'


class PartidaORM(Base):
    __tablename__ = "partida"

    id: Mapped[str] = mapped_column(primary_key=True)  # uuid hex, ver docstring del módulo
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    participante_id: Mapped[int | None] = mapped_column(ForeignKey("participante.id"), nullable=True)
    sesion_id: Mapped[int | None] = mapped_column(ForeignKey("sesion.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    resultado: Mapped[str | None] = mapped_column(nullable=True)  # None mientras está 'en_curso'
    tipo: Mapped[str] = mapped_column(nullable=False)  # 'fisica' | 'digital'
    fen: Mapped[str] = mapped_column(nullable=False)
    nivel: Mapped[int] = mapped_column(nullable=False)
    tipo_oponente: Mapped[str] = mapped_column(nullable=False, default="motor")
    jugadas_uci: Mapped[str] = mapped_column(nullable=False, default="")

    jugadas: Mapped[list["JugadaORM"]] = relationship(back_populates="partida", cascade="all, delete-orphan")
    usuario: Mapped["UsuarioORM"] = relationship(back_populates="partidas")


class JugadaORM(Base):
    """Todavía sin poblar desde `servicio_partida.py` (RF34, HU4) — la tabla ya
    existe para cuando llegue esa HU, no hace falta crearla de nuevo."""

    __tablename__ = "jugada"

    id: Mapped[int] = mapped_column(primary_key=True)
    partida_id: Mapped[str] = mapped_column(ForeignKey("partida.id"), nullable=False)
    numero: Mapped[int] = mapped_column(nullable=False)
    fen_antes: Mapped[str] = mapped_column(nullable=False)
    movimiento: Mapped[str] = mapped_column(nullable=False)  # notación UCI, ej. "e2e4"
    decidido_por: Mapped[str | None] = mapped_column(nullable=True)  # 'motor' | 'modelo' | 'jugador'
    tiempo_calculo_ms: Mapped[int | None] = mapped_column(nullable=True)
    explicacion: Mapped[str | None] = mapped_column(nullable=True)

    partida: Mapped[PartidaORM] = relationship(back_populates="jugadas")
