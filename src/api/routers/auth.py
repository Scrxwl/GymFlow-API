"""Endpoints de autenticação da GymFlow API (/api/v1/auth/register, /api/v1/auth/login e /api/v1/auth/me)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..exceptions import ApiErrorException
from ..models import UserModel
from ..schemas import (
    ApiError,
    AuthTokenResponse,
    LoginRequestDTO,
    RegisterUserDTO,
    UserResponse,
)
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
    summary="Passo 1 (Opcional): Registrar novo usuário (Personal Trainer ou Aluno)",
    response_description="Usuário cadastrado com sucesso no banco SQLite via SQLAlchemy 2.0.",
    description=(
        "Cadastra um novo usuário no sistema com papel **`PERSONAL`** ou **`STUDENT`**.\n\n"
        "### Passo a Passo para Testar:\n"
        "1. Revise o JSON de exemplo abaixo (para `PERSONAL`, o campo `cref` é obrigatório; para `STUDENT`, o `cref` pode ser omitido ou `null`).\n"
        "2. Clique em **Executar Requisição**.\n"
        "3. Em caso de sucesso, a API retorna **`201`** com os dados do usuário e o cabeçalho `Location: /api/v1/auth/me`.\n"
        "4. Em seguida, utilize o e-mail e a senha cadastrados no endpoint **`POST /api/v1/auth/login`** para gerar seu token JWT."
    ),
    responses={
        409: {
            "model": ApiError,
            "description": "Conflito: Já existe um usuário cadastrado com o e-mail informado (RFC 9457).",
            "content": {
                "application/problem+json": {
                    "example": {
                        "type": "https://api.gymflow.dev/errors/conflict",
                        "title": "Conflito de Estado",
                        "status": 409,
                        "detail": "Já existe um usuário registrado com o e-mail 'carlos@gymflow.dev'.",
                        "instance": "/api/v1/auth/register",
                    }
                }
            },
        },
        422: {
            "model": ApiError,
            "description": "Erro de Validação Semântica: Campos inválidos ou PERSONAL sem CREF (RFC 9457).",
            "content": {
                "application/problem+json": {
                    "example": {
                        "type": "https://api.gymflow.dev/errors/validation-error",
                        "title": "Erro de Validação Semântica",
                        "status": 422,
                        "detail": "Um ou mais campos da requisição falharam na validação.",
                        "instance": "/api/v1/auth/register",
                        "invalidParams": [
                            {
                                "name": "cref",
                                "reason": "Value error, O campo 'cref' é obrigatório para usuários com papel PERSONAL.",
                            }
                        ],
                    }
                }
            },
        },
    },
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

    response.headers["Location"] = "/api/v1/auth/me"
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Passo 2: Autenticar credenciais e emitir token JWT (HS256)",
    response_description="Autenticação concluída com sucesso e token JWT emitido.",
    description=(
        "Valida o e-mail e a senha do usuário e emite um **Token JWT (`HS256`)** com validade de 1 hora (`3600` segundos).\n\n"
        "### Contas Pré-Cadastradas (Banco Inicial):\n"
        "- **Personal Trainer (`PERSONAL`):** E-mail `carlos@gymflow.dev` | Senha `Personal@2026`\n"
        "- **Aluno (`STUDENT`):** E-mail `rodrigo@gymflow.dev` | Senha `Aluno@2026` *(ou `rodrigoyoshi@gymflow.com` / `aluno123`)*\n\n"
        "### Passo a Passo para Usar o Token no `GET /api/v1/auth/me`:\n"
        "1. Clique em **Executar Requisição** abaixo (as credenciais do Personal Carlos já estão preenchidas como exemplo).\n"
        "2. No corpo da resposta `200`, copie o valor do campo **`accessToken`** (sem as aspas).\n"
        "3. Clique no botão **Autorizar JWT** (ícone de cadeado no topo da página ou ao lado de `GET /api/v1/auth/me`), cole o token e confirme.\n"
        "4. *Dica de UX:* Você também pode clicar nos botões **Autenticar em 1 Clique** na barra superior desta documentação para injetar o token automaticamente!"
    ),
    responses={
        401: {
            "model": ApiError,
            "description": "Não Autenticado: E-mail não encontrado ou senha incorreta (RFC 9457).",
            "content": {
                "application/problem+json": {
                    "example": {
                        "type": "https://api.gymflow.dev/errors/unauthorized",
                        "title": "Não Autenticado",
                        "status": 401,
                        "detail": "Credenciais inválidas: e-mail ou senha incorretos.",
                        "instance": "/api/v1/auth/login",
                    }
                }
            },
        },
        422: {
            "model": ApiError,
            "description": "Erro de Validação Semântica: Formato de e-mail inválido ou senha com menos de 6 caracteres (RFC 9457).",
        },
    },
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
    summary="Passo 3: Consultar perfil do usuário autenticado via Token JWT",
    response_description="Dados cadastrais e papel RBAC (PERSONAL ou STUDENT) do usuário autenticado.",
    description=(
        "Retorna os dados completos do usuário autenticado a partir do **Token JWT (`HS256`)** enviado no cabeçalho `Authorization: Bearer <token>`.\n\n"
        "---\n"
        "### Guia Passo a Passo para Testar esta Rota (`GET /api/v1/auth/me`)\n\n"
        "#### Opção Rápida (1 Clique — Recomendado)\n"
        "1. Na **Barra de Assistente de Testes** no topo desta página, clique em **\"1. Autenticar como PERSONAL (Carlos)\"** ou **\"2. Autenticar como STUDENT (Rodrigo)\"**.\n"
        "2. O token JWT será gerado e aplicado automaticamente no cadeado desta rota.\n"
        "3. Clique diretamente no botão **Executar Requisição** abaixo para visualizar a resposta **`200`** com o perfil completo!\n\n"
        "#### Opção Manual (Passo a Passo Tradicional)\n"
        "1. **Passo 1 — Gerar o Token:** Abra a rota `POST /api/v1/auth/login` acima e clique em **Executar Requisição** com `carlos@gymflow.dev` e `Personal@2026`.\n"
        "2. **Passo 2 — Autorizar no Cadeado:** Copie o texto do campo `accessToken` da resposta, clique no ícone de **cadeado (Autorizar JWT)** no canto direito desta rota, cole o token no campo `Value` e clique em **Autorizar**.\n"
        "3. **Passo 3 — Consultar `/api/v1/auth/me`:** Clique no botão **Executar Requisição** abaixo. A API validará a assinatura `HS256`, buscará o usuário no SQLite via SQLAlchemy 2.0 e retornará **`200`**.\n"
        "4. **Passo 4 — Simular Erro `401` (RFC 9457):** Para testar a proteção da rota sem token, clique em **\"3. Remover Token (Testar 401)\"** na barra superior (ou desautorize no cadeado) e clique em **Executar Requisição** novamente."
    ),
    responses={
        200: {
            "model": UserResponse,
            "description": "Perfil do usuário autenticado retornado com sucesso.",
            "content": {
                "application/json": {
                    "examples": {
                        "perfil_personal": {
                            "summary": "Exemplo 1: Usuário autenticado como PERSONAL (Carlos)",
                            "value": {
                                "id": "11111111-1111-1111-1111-111111111111",
                                "name": "Carlos Personal",
                                "email": "carlos@gymflow.dev",
                                "role": "PERSONAL",
                                "cref": "123456-G/SP",
                                "phone": "+5511999990001",
                                "createdAt": "2026-02-10T09:00:00Z",
                            },
                        },
                        "perfil_student": {
                            "summary": "Exemplo 2: Usuário autenticado como STUDENT (Rodrigo)",
                            "value": {
                                "id": "22222222-2222-2222-2222-222222222222",
                                "name": "Rodrigo Aluno",
                                "email": "rodrigo@gymflow.dev",
                                "role": "STUDENT",
                                "cref": None,
                                "phone": "+5511999990002",
                                "createdAt": "2026-02-10T09:00:00Z",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "model": ApiError,
            "description": "Não Autenticado: Token JWT ausente, malformado ou expirado (Padrão RFC 9457 Problem Details).",
            "content": {
                "application/problem+json": {
                    "examples": {
                        "token_ausente": {
                            "summary": "Cenário A: Requisição enviada sem cabeçalho Authorization",
                            "value": {
                                "type": "https://api.gymflow.dev/errors/unauthorized",
                                "title": "Não Autenticado",
                                "status": 401,
                                "detail": "Token ausente. Envie o cabeçalho 'Authorization: Bearer <token>'.",
                                "instance": "/api/v1/auth/me",
                            },
                        },
                        "token_invalido": {
                            "summary": "Cenário B: Token JWT adulterado ou com assinatura HS256 inválida",
                            "value": {
                                "type": "https://api.gymflow.dev/errors/unauthorized",
                                "title": "Não Autenticado",
                                "status": 401,
                                "detail": "Token JWT inválido ou malformado.",
                                "instance": "/api/v1/auth/me",
                            },
                        },
                    }
                }
            },
        },
    },
)
def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
