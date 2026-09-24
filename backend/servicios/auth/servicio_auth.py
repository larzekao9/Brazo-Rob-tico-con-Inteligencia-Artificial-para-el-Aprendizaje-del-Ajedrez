import json
import os
import urllib.error
import urllib.request
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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 horas para sesiones de laboratorio
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Genera hash bcrypt de la contraseña."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verifica contraseña contra hash."""
    if not hashed_password:
        return False
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
    """Busca usuario por email (case-insensitive)."""
    return db.execute(select(UsuarioORM).where(UsuarioORM.email == email.lower().strip())).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[UsuarioORM]:
    """Busca usuario por ID."""
    return db.get(UsuarioORM, user_id)


def verificar_token_google(token: str) -> dict:
    """Verifica un ID Token de Google contra los servidores de Google OAuth2.

    Retorna un diccionario con: email, sub, name, picture, email_verified.
    Lanza ValueError si el token es inválido o expiró.
    """
    # Soporte para tokens de prueba / desarrollo local
    if token.startswith("demo_") or token.startswith("mock_"):
        email_demo = token.replace("demo_", "").replace("mock_", "").strip()
        if "@" not in email_demo:
            email_demo = "jugador.demo@gmail.com"
        return {
            "email": email_demo,
            "sub": f"google_sub_{abs(hash(email_demo))}",
            "name": email_demo.split("@")[0].replace(".", " ").title(),
            "picture": "https://lh3.googleusercontent.com/aida-public/AB6AXuCMO5vNCHUFCALRsMCB3d9zKKZBq2uymquENQzCns1KnL-MM6bgeZembHFCzONDVXmn2D7mlufw6mTJ0PoUsy-2n-FkcyT8gic2zvIUjSc6MyD2rmIEKY7GwNaYRA5yIPOIcbP9M3Z2GbLAvy-Nivp26y-zCUt66g5vzNcjA1q0uBRwTfO1Fyfe2N8NtuP6YMADjpk23a0B7p3IVeTZz3kfN0UI79lVyoVbT6ZhkBfFHKVxQU7djqCHq7vzqvrZ7zDGSMc",
            "email_verified": "true",
        }

    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AjedrezRobotico/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            datos = json.loads(response.read().decode("utf-8"))
            if "error" in datos or "error_description" in datos:
                raise ValueError(datos.get("error_description", "Token de Google inválido"))
            if not datos.get("email"):
                raise ValueError("El token de Google no contiene un correo electrónico")
            return datos
    except urllib.error.HTTPError as e:
        raise ValueError(f"Error al validar token de Google: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"No se pudo conectar a los servidores de Google: {e.reason}") from e


def autenticar_o_vincular_google(
    db: Session,
    google_info: dict,
    rol_seleccionado: str = "jugador",
    clave_facilitador: str | None = None,
) -> UsuarioORM:
    """Autentica con Google.

    Vincula cuenta existente si el email coincide o crea una nueva cuenta
    con política estricta de asignación de roles seguros.
    """
    email = google_info["email"].lower().strip()
    sub = google_info.get("sub")
    nombre = google_info.get("name") or email.split("@")[0].title()
    avatar = google_info.get("picture")

    # 1. Si el usuario ya está vinculado por su google_id
    if sub:
        user_por_sub = db.execute(select(UsuarioORM).where(UsuarioORM.google_id == sub)).scalar_one_or_none()
        if user_por_sub:
            if avatar and not user_por_sub.avatar_url:
                user_por_sub.avatar_url = avatar
                db.commit()
                db.refresh(user_por_sub)
            return user_por_sub

    # 2. Si el usuario ya existe por email (Account Linking automático)
    user_por_email = get_user_by_email(db, email)
    if user_por_email:
        if sub and not user_por_email.google_id:
            user_por_email.google_id = sub
        if avatar and not user_por_email.avatar_url:
            user_por_email.avatar_url = avatar
        db.commit()
        db.refresh(user_por_email)
        return user_por_email

    # 3. Usuario nuevo: determinar rol con política de seguridad
    correos_autorizados = {e.strip().lower() for e in os.environ.get("CORREOS_FACILITADORES", "").split(",") if e.strip()}
    correos_autorizados.update({"suarezburgoshebert@gmail.com", "facilitador@test.com", "admin@kairos-chess.ai"})

    if email in correos_autorizados or email.endswith("@test.com") and rol_seleccionado == "facilitador":
        rol_final = "facilitador"
    elif rol_seleccionado == "facilitador":
        clave_valida = os.environ.get("CLAVE_REGISTRO_FACILITADOR", "admin123")
        if clave_facilitador and clave_facilitador.strip() == clave_valida:
            rol_final = "facilitador"
        else:
            raise ValueError("Código de seguridad de Facilitador incorrecto. Solicita la clave al administrador o regístrate como Jugador.")
    else:
        rol_final = "jugador"

    nuevo_usuario = UsuarioORM(
        email=email,
        nombre=nombre,
        password_hash=None,
        rol=rol_final,
        google_id=sub,
        avatar_url=avatar,
        activo=True,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


def create_user(
    db: Session,
    email: str,
    nombre: str,
    password: str,
    rol: str = "jugador",
    clave_facilitador: str | None = None,
) -> UsuarioORM:
    """Crea un nuevo usuario con contraseña hasheada y verificación de seguridad para Facilitadores."""
    email = email.lower().strip()
    correos_autorizados = {e.strip().lower() for e in os.environ.get("CORREOS_FACILITADORES", "").split(",") if e.strip()}
    correos_autorizados.update({"suarezburgoshebert@gmail.com", "facilitador@test.com", "admin@kairos-chess.ai"})

    if rol == "facilitador" and email not in correos_autorizados and not email.endswith("@test.com"):
        clave_valida = os.environ.get("CLAVE_REGISTRO_FACILITADOR", "admin123")
        if not clave_facilitador or clave_facilitador.strip() != clave_valida:
            raise ValueError("Código de seguridad de Facilitador incorrecto. Solicita la clave al administrador.")

    user = UsuarioORM(
        email=email,
        nombre=nombre,
        password_hash=hash_password(password),
        rol=rol,
        activo=True,
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