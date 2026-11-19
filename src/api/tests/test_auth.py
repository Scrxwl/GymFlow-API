"""Testes passo a passo de Registro, Login JWT e Perfil Autenticado (`/api/v1/auth`).

===============================================================================
ROTEIRO PASSO A PASSO DOS TESTES DE AUTENTICAÇÃO E DA ROTA GET /api/v1/auth/me
(`http://localhost:8000/docs#/Authentication/get_me_api_v1_auth_me_get`)
===============================================================================
Este módulo valida integralmente o ciclo de autenticação Stateless via JWT (`HS256`)
e a consulta do usuário autenticado em `GET /api/v1/auth/me`:

1. `test_register_personal_and_login_jwt`:
   - Passo 1: Cadastra uma nova Personal Trainer (`POST /api/v1/auth/register`) informando o `cref`.
   - Passo 2: Valida o retorno `201`, os campos do usuário criado e o cabeçalho `Location: /api/v1/auth/me`.
   - Passo 3: Realiza login (`POST /api/v1/auth/login`) com as credenciais recém-criadas.
   - Passo 4: Valida o retorno `200` contendo o `accessToken` JWT, `tokenType="bearer"` e `expiresIn=3600`.
   - Passo 5: Usa o `accessToken` obtido no login para consultar `GET /api/v1/auth/me` e confirma os dados do perfil.

2. `test_login_invalid_credentials_returns_401_rfc9457`:
   - Passo 1: Tenta autenticar com senha incorreta em `POST /api/v1/auth/login`.
   - Passo 2: Verifica o erro `401` padronizado pela RFC 9457 (`https://api.gymflow.dev/errors/unauthorized`).
   - Passo 3: Tenta autenticar com e-mail não cadastrado e confirma que a API mantém a mesma resposta `401` segura.

3. `test_get_me_authenticated_and_unauthenticated`:
   - Passo 1 (Sem Token): Chama `GET /api/v1/auth/me` sem cabeçalho `Authorization` -> retorna `401` (RFC 9457).
   - Passo 2 (Cabeçalho Malformado): Chama `GET /api/v1/auth/me` sem o prefixo `Bearer` -> retorna `401` (RFC 9457).
   - Passo 3 (Token Adulterado): Chama `GET /api/v1/auth/me` com assinatura JWT inválida -> retorna `401` (RFC 9457).
   - Passo 4 (Autenticado como PERSONAL): Chama `GET /api/v1/auth/me` com token de Personal -> retorna `200` com `role="PERSONAL"` e `cref`.
   - Passo 5 (Autenticado como STUDENT): Chama `GET /api/v1/auth/me` com token de Aluno -> retorna `200` com `role="STUDENT"` e `cref=None`.

4. `test_register_conflict_409_and_missing_cref_422_rfc9457`:
   - Passo 1: Tenta registrar um e-mail já existente (`carlos@gymflow.dev`) -> retorna `409` (RFC 9457).
   - Passo 2: Tenta registrar um `PERSONAL` sem informar o campo obrigatório `cref` -> retorna `422` (RFC 9457) com `invalidParams`.

5. `test_swagger_docs_get_me_ux_and_localized_openapi`:
   - Passo 1: Acessa `GET /docs` (interface de `http://localhost:8000/docs#/Authentication/get_me_api_v1_auth_me_get`) e verifica que o guia passo a passo em português e os botões de autenticação em 1 clique estão presentes.
   - Passo 2: Acessa `GET /openapi.json` e confirma que a operação `get_me_api_v1_auth_me_get` possui o passo a passo detalhado em português e exemplos de resposta `200` e `401`.
===============================================================================
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_personal_and_login_jwt(client: TestClient) -> None:
    """Valida o fluxo completo passo a passo: Cadastro -> Login JWT -> Consulta em GET /api/v1/auth/me.

    Passo a Passo:
    - Passo 1: Enviar `POST /api/v1/auth/register` com dados válidos de uma Personal Trainer (incluindo `cref`).
    - Passo 2: Confirmar status `201`, papel `PERSONAL`, registro `cref` e cabeçalho `Location: /api/v1/auth/me`.
    - Passo 3: Enviar `POST /api/v1/auth/login` com o e-mail e a senha cadastrados no Passo 1.
    - Passo 4: Confirmar status `200` e extrair o `accessToken` JWT retornado no corpo JSON.
    - Passo 5: Enviar `GET /api/v1/auth/me` passando o cabeçalho `Authorization: Bearer <accessToken>`
      e validar que o perfil retornado corresponde exatamente à usuária autenticada.
    """
    # --- PASSO 1: Cadastrar uma nova Personal Trainer em POST /api/v1/auth/register ---
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Fernanda Personal",
            "email": "fernanda@gymflow.dev",
            "password": "Personal@2026",
            "role": "PERSONAL",
            "cref": "654321-G/SP",
            "phone": "+5511977776666",
        },
    )

    # --- PASSO 2: Validar resposta HTTP 201 e cabeçalho Location apontando para /api/v1/auth/me ---
    assert reg_res.status_code == 201
    assert reg_res.headers.get("Location") == "/api/v1/auth/me"
    user_data = reg_res.json()
    assert user_data["name"] == "Fernanda Personal"
    assert user_data["email"] == "fernanda@gymflow.dev"
    assert user_data["role"] == "PERSONAL"
    assert user_data["cref"] == "654321-G/SP"

    # --- PASSO 3: Autenticar as credenciais em POST /api/v1/auth/login para obter o token JWT ---
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "fernanda@gymflow.dev", "password": "Personal@2026"},
    )

    # --- PASSO 4: Validar envelope AuthTokenResponse (HTTP 200) e extrair o accessToken ---
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "accessToken" in token_data
    assert token_data["tokenType"] == "bearer"
    assert token_data["expiresIn"] == 3600
    assert token_data["user"]["email"] == "fernanda@gymflow.dev"
    access_token = token_data["accessToken"]

    # --- PASSO 5: Consultar GET /api/v1/auth/me enviando o token JWT no cabeçalho Authorization ---
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_data["id"]
    assert me_data["email"] == "fernanda@gymflow.dev"
    assert me_data["role"] == "PERSONAL"
    assert me_data["cref"] == "654321-G/SP"


def test_login_invalid_credentials_returns_401_rfc9457(client: TestClient) -> None:
    """Valida passo a passo que falhas de autenticação no login retornam HTTP 401 no padrão RFC 9457.

    Passo a Passo:
    - Passo 1: Enviar `POST /api/v1/auth/login` com e-mail válido (`carlos@gymflow.dev`), mas senha incorreta.
    - Passo 2: Confirmar retorno `401` e verificar os campos obrigatórios da RFC 9457 (`type`, `title`, `status`, `detail`, `instance`).
    - Passo 3: Enviar `POST /api/v1/auth/login` com um e-mail não cadastrado (`inexistente@gymflow.dev`).
    - Passo 4: Confirmar que também retorna `401` com a mesma mensagem genérica (evitando enumeração de usuários).
    """
    # --- PASSO 1: Tentar login com senha incorreta ---
    res_wrong_pass = client.post(
        "/api/v1/auth/login",
        json={"email": "carlos@gymflow.dev", "password": "WrongPassword999"},
    )

    # --- PASSO 2: Validar contrato de erro RFC 9457 (Problem Details) para HTTP 401 ---
    assert res_wrong_pass.status_code == 401
    err = res_wrong_pass.json()
    assert err["type"] == "https://api.gymflow.dev/errors/unauthorized"
    assert err["title"] == "Não Autenticado"
    assert err["status"] == 401
    assert "Credenciais inválidas" in err["detail"]
    assert err["instance"] == "/api/v1/auth/login"

    # --- PASSO 3: Tentar login com e-mail não cadastrado ---
    res_unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "nao.existe@gymflow.dev", "password": "QualquerSenha123"},
    )

    # --- PASSO 4: Confirmar retorno 401 RFC 9457 idêntico e seguro ---
    assert res_unknown_email.status_code == 401
    assert res_unknown_email.json()["type"] == "https://api.gymflow.dev/errors/unauthorized"


def test_get_me_authenticated_and_unauthenticated(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo todos os cenários da rota `GET /api/v1/auth/me` (`get_me_api_v1_auth_me_get`).

    Esta é a rota destacada em `http://localhost:8000/docs#/Authentication/get_me_api_v1_auth_me_get`.

    Passo a Passo:
    - Passo 1 (Requisição sem Token): Chamar `GET /api/v1/auth/me` sem o cabeçalho `Authorization`.
      Deve retornar `401` (RFC 9457) orientando a enviar `Authorization: Bearer <token>`.
    - Passo 2 (Cabeçalho com Formato Inválido): Chamar `GET /api/v1/auth/me` com `Authorization: TokenInvalidoSemPrefixo`.
      Deve retornar `401` (RFC 9457) explicando o formato `Bearer <token>`.
    - Passo 3 (Token JWT Adulterado/Inválido): Chamar `GET /api/v1/auth/me` com um token JWT cuja assinatura `HS256` não confere.
      Deve retornar `401` (RFC 9457) informando que o token é inválido ou malformado.
    - Passo 4 (Sucesso com Token de PERSONAL): Chamar `GET /api/v1/auth/me` com `personal_headers` (Carlos Personal).
      Deve retornar `200` com `email="carlos@gymflow.dev"`, `role="PERSONAL"` e `cref="123456-G/SP"`.
    - Passo 5 (Sucesso com Token de STUDENT): Chamar `GET /api/v1/auth/me` com `student_headers` (Rodrigo Aluno).
      Deve retornar `200` com `email="rodrigo@gymflow.dev"`, `role="STUDENT"` e `cref=None`.
    """
    # --- PASSO 1: Testar GET /api/v1/auth/me SEM enviar token JWT (esperado: 401 RFC 9457) ---
    unauth = client.get("/api/v1/auth/me")
    assert unauth.status_code == 401
    unauth_err = unauth.json()
    assert unauth_err["type"] == "https://api.gymflow.dev/errors/unauthorized"
    assert unauth_err["status"] == 401
    assert unauth_err["instance"] == "/api/v1/auth/me"
    assert "Authorization: Bearer <token>" in unauth_err["detail"]

    # --- PASSO 2: Testar GET /api/v1/auth/me com cabeçalho Authorization sem o esquema 'Bearer' ---
    bad_scheme = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic token_sem_esquema_bearer"},
    )
    assert bad_scheme.status_code == 401
    assert bad_scheme.json()["type"] == "https://api.gymflow.dev/errors/unauthorized"

    # --- PASSO 3: Testar GET /api/v1/auth/me com token JWT adulterado (assinatura HS256 inválida) ---
    tampered = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.assinatura_invalida"},
    )
    assert tampered.status_code == 401
    assert tampered.json()["type"] == "https://api.gymflow.dev/errors/unauthorized"
    assert "inválido ou malformado" in tampered.json()["detail"]

    # --- PASSO 4: Testar GET /api/v1/auth/me autenticado como PERSONAL (Carlos Personal) ---
    ok_personal = client.get("/api/v1/auth/me", headers=personal_headers)
    assert ok_personal.status_code == 200
    personal_body = ok_personal.json()
    assert personal_body["email"] == "carlos@gymflow.dev"
    assert personal_body["role"] == "PERSONAL"
    assert personal_body["cref"] == "123456-G/SP"

    # --- PASSO 5: Testar GET /api/v1/auth/me autenticado como STUDENT (Rodrigo Aluno) ---
    ok_student = client.get("/api/v1/auth/me", headers=student_headers)
    assert ok_student.status_code == 200
    student_body = ok_student.json()
    assert student_body["email"] == "rodrigo@gymflow.dev"
    assert student_body["role"] == "STUDENT"
    assert student_body["cref"] is None


def test_register_conflict_409_and_missing_cref_422_rfc9457(client: TestClient) -> None:
    """Valida passo a passo as regras de negócio de conflito de e-mail (409) e obrigatoriedade de CREF (422).

    Passo a Passo:
    - Passo 1: Tentar cadastrar um usuário com o e-mail `carlos@gymflow.dev` (já existente no seed inicial).
    - Passo 2: Confirmar retorno `409 Conflito de Estado` no padrão RFC 9457 (`https://api.gymflow.dev/errors/conflict`).
    - Passo 3: Tentar cadastrar um usuário com papel `PERSONAL`, porém sem preencher o campo `cref`.
    - Passo 4: Confirmar retorno `422 Erro de Validação Semântica` no padrão RFC 9457 com a lista `invalidParams`.
    """
    # --- PASSO 1: Enviar registro com e-mail já cadastrado no banco ---
    conflict_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Carlos Duplicado",
            "email": "carlos@gymflow.dev",
            "password": "Personal@2026",
            "role": "PERSONAL",
            "cref": "123456-G/SP",
        },
    )

    # --- PASSO 2: Validar erro 409 Conflict (RFC 9457) ---
    assert conflict_res.status_code == 409
    conflict_err = conflict_res.json()
    assert conflict_err["type"] == "https://api.gymflow.dev/errors/conflict"
    assert conflict_err["status"] == 409

    # --- PASSO 3: Enviar registro de PERSONAL sem o campo obrigatório 'cref' ---
    missing_cref_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Personal Sem Cref",
            "email": "sem.cref@gymflow.dev",
            "password": "Personal@2026",
            "role": "PERSONAL",
        },
    )

    # --- PASSO 4: Validar erro 422 Validation Error (RFC 9457) com invalidParams ---
    assert missing_cref_res.status_code == 422
    val_err = missing_cref_res.json()
    assert val_err["type"] == "https://api.gymflow.dev/errors/validation-error"
    assert val_err["status"] == 422
    assert isinstance(val_err["invalidParams"], list)
    assert len(val_err["invalidParams"]) >= 1


def test_swagger_docs_get_me_ux_and_localized_openapi(client: TestClient) -> None:
    """Valida passo a passo a página interativa `/docs` e o esquema `/openapi.json` em português.

    Passo a Passo:
    - Passo 1: Acessar `GET /docs` e verificar que a interface contém o Guia Passo a Passo
      em português para a rota `GET /api/v1/auth/me` (`#/Authentication/get_me_api_v1_auth_me_get`)
      e os botões de autenticação JWT em 1 clique.
    - Passo 2: Acessar `GET /openapi.json` e verificar que a operação `get_me_api_v1_auth_me_get`
      está documentada em português, com o passo a passo no campo `description` e exemplos para `200` e `401`.
    """
    # --- PASSO 1: Consultar a página de documentação interativa GET /docs ---
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "Guia Passo a Passo" in docs_res.text
    assert "get_me_api_v1_auth_me_get" in docs_res.text
    assert "Autenticar como PERSONAL" in docs_res.text

    # --- PASSO 2: Consultar o contrato OpenAPI gerado em GET /openapi.json ---
    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    me_op = schema["paths"]["/api/v1/auth/me"]["get"]
    assert me_op["operationId"] == "get_me_api_v1_auth_me_get"
    assert "Passo a Passo" in me_op["description"]
    assert "200" in me_op["responses"]
    assert "401" in me_op["responses"]
