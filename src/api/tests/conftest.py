"""Configuração central de fixtures do pytest para a GymFlow API (`conftest.py`).

===============================================================================
GUIA PASSO A PASSO DA INFRAESTRUTURA DE TESTES AUTOMATIZADOS
===============================================================================
Como executar toda a suíte de testes no terminal:
    $ ./.venv/bin/pytest -v

Como executar apenas os testes de autenticação e da rota GET /api/v1/auth/me:
    $ ./.venv/bin/pytest src/api/tests/test_auth.py -v

O que este arquivo configura automaticamente antes de cada teste:
    - Passo 1 (`db_session`): Cria um banco de dados SQLite 100% em memória
      (`sqlite:///:memory:`) isolado por função de teste e executa o seed inicial
      (`init_db_and_seed`), cadastrando:
        * Personal Trainer (`PERSONAL`): Carlos Personal (`carlos@gymflow.dev` / `Personal@2026`)
        * Aluno (`STUDENT`): Rodrigo Aluno (`rodrigo@gymflow.dev` / `Aluno@2026`) + Perfil Biométrico 1:1
        * Ficha de Treino (`WorkoutPlanModel`) + Rotina A (`WorkoutRoutineModel`) + Exercício + Execução RPE
    - Passo 2 (`client`): Sobrescreve a dependência `get_db` do FastAPI para usar
      a sessão em memória do teste atual e instancia o `TestClient`.
    - Passo 3 (`personal_headers` e `student_headers`): Gera tokens JWT reais
      assinados com `HS256` (`create_access_token`) e monta o cabeçalho HTTP
      `{"Authorization": "Bearer <token>"}` para os papéis `PERSONAL` e `STUDENT`.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..database import SEED_PERSONAL_ID, SEED_STUDENT_ID, get_db, init_db_and_seed
from ..main import app
from ..models import Base, UserModel
from ..security import create_access_token


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Cria e popula um banco SQLite em memória isolado para cada teste.

    Passo a Passo:
    1. Instancia uma engine SQLite em memória com `StaticPool` (mantém a mesma
       conexão durante a execução do teste).
    2. Cria todas as tabelas mapeadas pelo SQLAlchemy 2.0 (`Base.metadata.create_all`).
    3. Executa `init_db_and_seed` para inserir os registros iniciais (Carlos Personal,
       Rodrigo Aluno, perfil biométrico, ficha de treino, rotina, exercício e check-in RPE).
    4. Entrega a sessão ao teste (`yield session`) e, ao final, destrói todas as tabelas
       para garantir isolamento absoluto entre os testes.
    """
    # Passo 1: Criar engine SQLite em memória isolada
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    # Passo 2: Criar todas as tabelas ORM no banco em memória
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        # Passo 3: Popular o banco com os dados iniciais do contrato Apidog
        init_db_and_seed(session, target_engine=test_engine)
        yield session
    finally:
        # Passo 4: Encerrar sessão e limpar todas as tabelas após o término do teste
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Fornece um cliente HTTP (`TestClient`) conectado ao banco em memória do teste.

    Passo a Passo:
    1. Substitui a dependência `get_db` da aplicação FastAPI pela sessão `db_session`.
    2. Inicializa o `TestClient(app)` para permitir chamadas HTTP síncronas (`GET`, `POST`, `PATCH`, `DELETE`).
    3. Limpa os overrides de dependência ao finalizar o teste.
    """
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def personal_headers(db_session: Session) -> dict[str, str]:
    """Gera o cabeçalho HTTP `Authorization: Bearer <token>` para o perfil `PERSONAL`.

    Passo a Passo:
    1. Busca o usuário seed Carlos Personal (`SEED_PERSONAL_ID`) no banco de testes.
    2. Gera um token JWT válido assinado com `HS256` contendo `sub`, `email`, `role="PERSONAL"` e `exp`.
    3. Retorna o dicionário `{"Authorization": "Bearer <token>"}` pronto para uso nas requisições.
    """
    personal = db_session.scalar(
        select(UserModel).where(UserModel.id == SEED_PERSONAL_ID)
    )
    assert personal is not None
    token = create_access_token(personal)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_headers(db_session: Session) -> dict[str, str]:
    """Gera o cabeçalho HTTP `Authorization: Bearer <token>` para o perfil `STUDENT`.

    Passo a Passo:
    1. Busca o usuário seed Rodrigo Aluno (`SEED_STUDENT_ID`) no banco de testes.
    2. Gera um token JWT válido assinado com `HS256` contendo `sub`, `email`, `role="STUDENT"` e `exp`.
    3. Retorna o dicionário `{"Authorization": "Bearer <token>"}` pronto para uso nas requisições.
    """
    student = db_session.scalar(
        select(UserModel).where(UserModel.id == SEED_STUDENT_ID)
    )
    assert student is not None
    token = create_access_token(student)
    return {"Authorization": f"Bearer {token}"}
