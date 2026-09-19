"""Rutas de autenticación: registro, login, refresh, me, gestión de usuarios (admin)."""
from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database import DATABASE_URL, crear_fabrica_sesiones, crear_tablas, obtener_engine
from backend.esquemas.auth_esquema import (
    LoginRequest,
    NivelEstimadoRequest,
    RegistroRequest,
    RefreshRequest,
    TokenResponse,
    AuthResponse,
    UsuarioResponse,
)
from backend.esquemas.usuario_esquema import HistorialPartidasResponse
from backend.modelos.tablas_orm import PartidaORM, UsuarioORM
from backend.servicios.auth import (
    actualizar_nivel_estimado,
    authenticate_user,
    create_access_token,
    create_user,
    create_tokens,
    decode_and_validate_access_token,
    decode_and_validate_refresh_token,
    get_user_by_email,
    get_user_by_id,
)
from backend.servicios.usuario.servicio_estadisticas import obtener_historial_partidas

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _fabrica_sesiones() -> sessionmaker[Session]:
    """Un solo engine por proceso; crea las tablas (incluida `usuario`) la primera vez."""
    engine = obtener_engine()
    crear_tablas(engine)
    return crear_fabrica_sesiones(engine)


def get_db() -> Iterator[Session]:
    """Dependencia de sesión de base de datos (requiere `DATABASE_URL`)."""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Base de datos no configurada")
    db = _fabrica_sesiones()()
    try:
        yield db
    finally:
        db.close()


def _a_respuesta(user) -> UsuarioResponse:
    return UsuarioResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        rol=user.rol,
        creado_en=user.creado_en.isoformat(),
        nivel_estimado=user.nivel_estimado,
        rango_estimado=user.rango_estimado,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> int:
    """Extrae y valida el access token, retorna user_id."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    user_id = decode_and_validate_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    user = get_user_by_id(db, user_id)
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return user_id


def get_current_facilitador(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> int:
    """Verifica que el usuario autenticado tenga rol facilitador."""
    user = get_user_by_id(db, user_id)
    if not user or user.rol != "facilitador":
        raise HTTPException(status_code=403, detail="Acceso solo para facilitadores")
    return user_id


@router.post(
    "/registro",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
def registro(data: RegistroRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Registra un nuevo usuario y devuelve tokens de acceso."""
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email ya registrado")

    user = create_user(db, data.email, data.nombre, data.password, rol=data.rol)
    access, refresh = create_tokens(user)

    return AuthResponse(
        usuario=_a_respuesta(user),
        tokens=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=30 * 60,
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Iniciar sesión",
)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Autentica usuario y devuelve tokens de acceso.

    Si el cliente manda `rol_esperado` (la app móvil manda `jugador`) y la
    cuenta tiene otro rol, responde 403 sin emitir tokens.
    """
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if data.rol_esperado is not None and user.rol != data.rol_esperado:
        raise HTTPException(
            status_code=403,
            detail=f"Esta cuenta tiene rol '{user.rol}'; este acceso es solo para rol '{data.rol_esperado}'",
        )

    access, refresh = create_tokens(user)

    return AuthResponse(
        usuario=_a_respuesta(user),
        tokens=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=30 * 60,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar access token",
)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Renueva access token usando refresh token."""
    user_id = decode_and_validate_refresh_token(data.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    user = get_user_by_id(db, user_id)
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    access = create_access_token({"sub": str(user.id), "email": user.email, "rol": user.rol})
    return TokenResponse(access_token=access, refresh_token=data.refresh_token, expires_in=30 * 60)


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Datos del usuario autenticado",
)
def me(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)) -> UsuarioResponse:
    """Retorna datos del usuario actual (requiere access token válido)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_respuesta(user)


@router.patch(
    "/nivel-estimado",
    response_model=UsuarioResponse,
    summary="Guardar el resultado de 'Mide tu nivel'",
)
def guardar_nivel_estimado(
    data: NivelEstimadoRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsuarioResponse:
    """Guarda el nivel/rango calculado al terminar el diagnóstico (HU5/HU10).

    Pisa el resultado anterior — no se guarda historial de evaluaciones.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = actualizar_nivel_estimado(db, user, data.nivel, data.rango)
    return _a_respuesta(user)


@router.get(
    "/usuarios",
    response_model=list[UsuarioResponse],
    summary="Listar todos los usuarios (solo facilitadores)",
)
def listar_usuarios(
    _: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> list[UsuarioResponse]:
    """Lista todos los usuarios registrados. Requiere rol facilitador."""
    usuarios = db.scalars(select(UsuarioORM).order_by(UsuarioORM.creado_en.desc())).all()
    return [_a_respuesta(u) for u in usuarios]


@router.get(
    "/usuarios/{usuario_id}/historial-partidas",
    response_model=HistorialPartidasResponse,
    summary="Historial de partidas de un usuario (solo facilitadores)",
)
def historial_partidas_usuario(
    usuario_id: int,
    limit: int = 10,
    offset: int = 0,
    _: int = Depends(get_current_facilitador),
    db: Session = Depends(get_db),
) -> HistorialPartidasResponse:
    """Historial paginado de partidas de un usuario específico. Requiere rol facilitador."""
    if not get_user_by_id(db, usuario_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return HistorialPartidasResponse(**obtener_historial_partidas(db, usuario_id, limit, offset))