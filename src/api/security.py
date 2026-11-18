"""Autenticação Stateless JWT (HS256) e Autorização RBAC (PERSONAL vs. STUDENT) da GymFlow API."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .exceptions import ApiErrorException
from .models import UserModel
from .schemas import UserRole

JWT_SECRET_KEY = os.getenv(
    "GYMFLOW_JWT_SECRET_KEY",
    "gymflow-fatec-rp-2026-super-secret-hs256-signing-key",
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 3600

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, stored_hex = password_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return hmac.compare_digest(dk.hex(), stored_hex)
    except (ValueError, AttributeError):
        return False


def create_access_token(
    user: UserModel,
    expires_delta_seconds: int = JWT_EXPIRATION_SECONDS,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=expires_delta_seconds)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "email": str(user.email),
        "role": str(user.role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "email", "role", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiErrorException(
            status_code=401,
            detail="Token JWT expirado. Realize login novamente.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise ApiErrorException(
            status_code=401,
            detail="Token JWT inválido ou malformado.",
        ) from exc


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise ApiErrorException(
            status_code=401,
            detail="Token ausente. Envie o cabeçalho 'Authorization: Bearer <token>'.",
            instance=str(request.url.path),
        )

    parts = auth_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or credentials is None:
        raise ApiErrorException(
            status_code=401,
            detail="Formato de cabeçalho Authorization inválido. Use 'Bearer <token>'.",
            instance=str(request.url.path),
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    user = db.scalar(select(UserModel).where(UserModel.id == str(user_id)))
    if not user:
        raise ApiErrorException(
            status_code=401,
            detail="Usuário associado ao token não foi encontrado.",
            instance=str(request.url.path),
        )

    return user


def require_roles(*allowed_roles: UserRole | str) -> Callable[..., UserModel]:
    normalized = {
        r.value if isinstance(r, UserRole) else str(r).upper() for r in allowed_roles
    }

    def _role_checker(
        request: Request,
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = str(current_user.role).upper()
        if user_role not in normalized:
            roles_str = ", ".join(sorted(normalized))
            raise ApiErrorException(
                status_code=403,
                detail=(
                    f"Acesso proibido para o papel '{user_role}'. "
                    f"Esta operação é restrita a: {roles_str}."
                ),
                instance=str(request.url.path),
            )
        return current_user

    return _role_checker
