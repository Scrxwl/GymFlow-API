"""Testes passo a passo de conformidade estrita com a RFC 9457 (Problem Details) (`400`, `401`, `403`, `404`, `422`).

===============================================================================
ROTEIRO PASSO A PASSO DOS TESTES DE PADRONIZAÇÃO DE ERROS (RFC 9457)
===============================================================================
Todas as falhas HTTP da GymFlow API devem obedecer ao contrato canônico `ApiError`
definido pela RFC 9457 (`type`, `title`, `status`, `detail`, `instance` e, em erros
de sintaxe/validação, a lista `invalidParams`):

- Passo 1 (`400 Requisição Inválida`): Envio de um parâmetro de rota que não é um UUID válido
  (`/api/v1/students/nao-e-uuid`) -> `type: "https://api.gymflow.dev/errors/bad-request"`.
- Passo 2 (`401 Não Autenticado`): Acesso a rota protegida sem envio de token JWT
  (`GET /api/v1/students`) -> `type: "https://api.gymflow.dev/errors/unauthorized"`.
- Passo 3 (`403 Acesso Proibido`): Papel `STUDENT` tentando executar operação exclusiva de `PERSONAL`
  (`DELETE /api/v1/students/{studentId}`) -> `type: "https://api.gymflow.dev/errors/forbidden"`.
- Passo 4 (`404 Recurso Não Encontrado`): Busca por UUID válido porém inexistente no banco SQLite
  (`GET /api/v1/workouts/00000000-0000-0000-0000-000000000000`) -> `type: "https://api.gymflow.dev/errors/not-found"`.
- Passo 5 (`422 Erro de Validação Semântica`): Envio de payload violando regras de domínio do Pydantic v2
  (nome curto, e-mail inválido, senha curta e `weightKg` negativo) -> `type: "https://api.gymflow.dev/errors/validation-error"`
  com lista `invalidParams` detalhando cada campo recusado.
===============================================================================
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_STUDENT_ID

NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


def test_rfc9457_400_401_403_404_422_responses(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo os 5 códigos de erro HTTP padronizados pela RFC 9457 (400, 401, 403, 404 e 422).

    Passo a Passo:
    - Passo 1: Provocar erro `400` passando um identificador malformado (`nao-e-uuid`) na rota.
    - Passo 2: Provocar erro `401` chamando uma rota protegida sem cabeçalho `Authorization`.
    - Passo 3: Provocar erro `403` chamando uma rota exclusiva de `PERSONAL` com token de `STUDENT`.
    - Passo 4: Provocar erro `404` buscando um recurso com UUID válido que não existe no banco.
    - Passo 5: Provocar erro `422` enviando campos com violação de limites semânticos (`weightKg: -5`, etc.).
    """
    # --- PASSO 1: 400 Bad Request (UUID inválido no parâmetro de rota) ---
    res_400 = client.get("/api/v1/students/nao-e-uuid", headers=personal_headers)
    assert res_400.status_code == 400
    assert res_400.json()["type"] == "https://api.gymflow.dev/errors/bad-request"
    assert len(res_400.json()["invalidParams"]) >= 1

    # --- PASSO 2: 401 Unauthorized (Requisição sem token JWT no cabeçalho Authorization) ---
    res_401 = client.get("/api/v1/students")
    assert res_401.status_code == 401
    assert res_401.json()["type"] == "https://api.gymflow.dev/errors/unauthorized"

    # --- PASSO 3: 403 Forbidden (STUDENT tentando remover um aluno da carteira do Personal) ---
    res_403 = client.delete(
        f"/api/v1/students/{SEED_STUDENT_ID}",
        headers=student_headers,
    )
    assert res_403.status_code == 403
    assert res_403.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # --- PASSO 4: 404 Not Found (Consulta de plano de treino com UUID inexistente no banco) ---
    res_404 = client.get(
        f"/api/v1/workouts/{NONEXISTENT_UUID}",
        headers=personal_headers,
    )
    assert res_404.status_code == 404
    assert res_404.json()["type"] == "https://api.gymflow.dev/errors/not-found"

    # --- PASSO 5: 422 Unprocessable Entity (Violação de limites semânticos: nome, e-mail, senha e weightKg < 20) ---
    res_422 = client.post(
        "/api/v1/students",
        json={
            "name": "Al",
            "email": "email-invalido",
            "password": "123",
            "profile": {"weightKg": -5, "goal": "HYPERTROPHY"},
        },
        headers=personal_headers,
    )
    assert res_422.status_code == 422
    err_422 = res_422.json()
    assert err_422["type"] == "https://api.gymflow.dev/errors/validation-error"
    assert isinstance(err_422["invalidParams"], list)
    assert len(err_422["invalidParams"]) >= 1
