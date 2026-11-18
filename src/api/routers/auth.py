"""Endpoints de autenticação da GymFlow API (/api/v1/auth/register, /api/v1/auth/login e /api/v1/auth/me)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..exceptions import ApiErrorException
from ..models import UserModel
from ..schemas import AuthTokenResponse, LoginRequestDTO, RegisterUserDTO, UserResponse
from ..security import (
    JWT_EXPIRATION_SECONDS,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário no sistema (Personal Trainer ou Aluno)",
)
def register_user(
    payload: RegisterUserDTO,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    existing = db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == payload.email.lower())
    )
    if existing:
        raise ApiErrorException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário registrado com o e-mail '{payload.email}'.",
            instance=str(request.url.path),
        )

    now = datetime.now(timezone.utc)
    new_user = UserModel(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        cref=payload.cref,
        phone=payload.phone,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    response.headers["Location"] = f"/api/v1/auth/me"
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticar usuário e emitir token JWT",
)
def login_user(
    payload: LoginRequestDTO,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    user = db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == payload.email.lower())
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise ApiErrorException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas: e-mail ou senha incorretos.",
            instance=str(request.url.path),
        )

    token = create_access_token(user=user, expires_delta_seconds=JWT_EXPIRATION_SECONDS)
    return AuthTokenResponse(
        accessToken=token,
        tokenType="bearer",
        expiresIn=JWT_EXPIRATION_SECONDS,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar dados do usuário autenticado",
)
def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
