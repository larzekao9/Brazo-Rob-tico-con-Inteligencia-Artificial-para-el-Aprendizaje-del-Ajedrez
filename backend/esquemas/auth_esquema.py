"""Esquemas Pydantic para autenticación (registro, login, tokens)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Rol = Literal["jugador", "facilitador"]


class RegistroRequest(BaseModel):
    """Cuerpo para POST /auth/registro. La app móvil siempre registra `jugador`."""

    email: EmailStr
    nombre: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=100)
    rol: Rol = "jugador"
    clave_facilitador: str | None = None


class GoogleAuthRequest(BaseModel):
    """Cuerpo para POST /auth/google."""

    credential: str
    rol_seleccionado: Rol | None = "jugador"
    clave_facilitador: str | None = None


class LoginRequest(BaseModel):
    """Cuerpo para POST /auth/login.

    `rol_esperado` es opcional: si el cliente lo manda (la app móvil manda
    `jugador`), el login falla con 403 cuando la cuenta tiene otro rol.
    """

    email: EmailStr
    password: str
    rol_esperado: Rol | None = None


class TokenResponse(BaseModel):
    """Respuesta con access token y refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class RefreshRequest(BaseModel):
    """Cuerpo para POST /auth/refresh."""

    refresh_token: str


class UsuarioResponse(BaseModel):
    """Datos públicos del usuario autenticado."""

    id: int
    email: str
    nombre: str
    rol: str
    creado_en: str
    google_id: str | None = None
    avatar_url: str | None = None
    nivel_estimado: int | None = None
    rango_estimado: str | None = None

    class Config:
        from_attributes = True


class NivelEstimadoRequest(BaseModel):
    """Cuerpo para PATCH /auth/nivel-estimado — resultado de "Mide tu nivel" (HU5/HU10)."""

    nivel: int = Field(ge=0, le=20)
    rango: Literal["Principiante", "Intermedio", "Avanzado"]


class AuthResponse(BaseModel):
    """Respuesta completa de login/registro."""

    usuario: UsuarioResponse
    tokens: TokenResponse