"""Servicio de autenticación: hashing de contraseñas, JWT, gestión de usuarios."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import UsuarioORM

# Configuración de hashing (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración JWT
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cambia-esto-en-produccion-usar-variable-entorno")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Genera hash bcrypt de la contraseña."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Genera JWT refresh token (larga duración)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica y valida JWT. Lanza JWTError si es inválido o expirado."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_user_by_email(db: Session, email: str) -> Optional[UsuarioORM]:
    """Busca usuario por email."""
    return db.execute(select(UsuarioORM).where(UsuarioORM.email == email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[UsuarioORM]:
    """Busca usuario por ID."""
    return db.get(UsuarioORM, user_id)


def create_user(db: Session, email: str, nombre: str, password: str, rol: str = "jugador") -> UsuarioORM:
    """Crea un nuevo usuario con contraseña hasheada y rol (`jugador` por defecto)."""
    user = UsuarioORM(
        email=email,
        nombre=nombre,
        password_hash=hash_password(password),
        rol=rol,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def actualizar_nivel_estimado(db: Session, user: UsuarioORM, nivel: int, rango: str) -> UsuarioORM:
    """Guarda el resultado de la última "Mide tu nivel" completada (HU5/HU10).

    Pisa el valor anterior a propósito — no se guarda historial de
    evaluaciones, solo el nivel/rango vigente del jugador.
    """
    user.nivel_estimado = nivel
    user.rango_estimado = rango
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[UsuarioORM]:
    """Verifica credenciales y retorna usuario si son válidas."""
    user = get_user_by_email(db, email)
    if not user or not user.activo:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens(user: UsuarioORM) -> tuple[str, str]:
    """Crea access + refresh tokens para un usuario."""
    payload = {"sub": str(user.id), "email": user.email, "rol": user.rol}
    access = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return access, refresh


def decode_and_validate_access_token(token: str) -> Optional[int]:
    """Decodifica access token y retorna user_id si es válido."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return int(payload.get("sub", 0))
    except (JWTError, ValueError):
        return None


def decode_and_validate_refresh_token(token: str) -> Optional[int]:
    """Decodifica refresh token y retorna user_id si es válido."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return None
        return int(payload.get("sub", 0))
    except (JWTError, ValueError):
        return None