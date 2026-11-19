"""Testes passo a passo de CRUD, perfil biométrico 1:1 (`selectinload`) e RBAC de Alunos (`/api/v1/students`).

===============================================================================
ROTEIRO PASSO A PASSO DOS TESTES DE GESTÃO DE ALUNOS (STUDENTS & ANALYTICS)
===============================================================================
Este módulo valida as operações da carteira de alunos do Personal Trainer, o
relacionamento 1:1 entre `UserModel` e `StudentProfileModel` com carregamento
otimizado via `selectinload`, o cálculo de indicadores biométricos (IMC / RPE)
e o controle de acesso RBAC vertical e horizontal:

1. `test_list_students_paginated_for_personal_and_403_for_student`:
   - Passo 1: Verifica que um `STUDENT` é bloqueado com `403 Acesso Proibido` (RFC 9457) ao tentar listar a carteira de alunos.
   - Passo 2: Verifica que o `PERSONAL` lista seus alunos com paginação (`page=1&limit=10`), filtro por objetivo (`goal=HYPERTROPHY`) e perfil biométrico aninhado (`selectinload`).

2. `test_full_student_crud_by_personal_and_rbac_delete_protection`:
   - Passo 1: `PERSONAL` cadastra uma nova aluna com perfil biométrico completo (`POST /api/v1/students` -> `201`).
   - Passo 2: `PERSONAL` consulta os detalhes da aluna por UUID (`GET /api/v1/students/{studentId}` -> `200`).
   - Passo 3: `PERSONAL` atualiza o peso e o objetivo físico da aluna (`PATCH /api/v1/students/{studentId}` -> `200`).
   - Passo 4: `STUDENT` tenta remover a aluna e recebe bloqueio RBAC (`DELETE /api/v1/students/{studentId}` -> `403`).
   - Passo 5: `PERSONAL` remove a aluna (`DELETE /api/v1/students/{studentId}` -> `204`) e confirma que uma nova busca retorna `404`.

3. `test_student_analytics_bmi_and_rpe_metrics_and_dashboard`:
   - Passo 1: Consulta `GET /api/v1/students/{studentId}/analytics` e valida o cálculo automático do IMC (`bmi=24.78`), classificação OMS (`Peso normal (Eutrófico)`) e média de esforço RPE (`8.0`).
   - Passo 2: Verifica que o painel web interativo (`GET /`) responde com `200`.

4. `test_student_and_personal_horizontal_rbac_isolation`:
   - Passo 1: `PERSONAL` 1 cadastra um segundo aluno na sua carteira.
   - Passo 2: Aluno 1 tenta acessar o cadastro e os indicadores (`/analytics`) do Aluno 2 -> bloqueado com `403` (prevenção de IDOR).
   - Passo 3: Cadastra e autentica um segundo Personal Trainer (`PERSONAL` 2).
   - Passo 4: `PERSONAL` 2 tenta consultar, atualizar ou remover um aluno da carteira do `PERSONAL` 1 -> bloqueado com `403`.
===============================================================================
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_PERSONAL_ID, SEED_STUDENT_ID


def test_list_students_paginated_for_personal_and_403_for_student(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo a listagem paginada de alunos e o bloqueio RBAC 403 para papel STUDENT.

    Passo a Passo:
    - Passo 1: Enviar `GET /api/v1/students` usando token JWT de `STUDENT` (`student_headers`).
      O middleware RBAC (`require_roles(UserRole.PERSONAL)`) deve barrar com `403` (RFC 9457).
    - Passo 2: Enviar `GET /api/v1/students?page=1&limit=10&goal=HYPERTROPHY` usando token de `PERSONAL`.
      Deve retornar `200` com envelope paginado (`data` + `meta`) e o perfil biométrico 1:1 carregado via `selectinload`.
    """
    # --- PASSO 1: STUDENT tentando listar carteira de alunos -> deve receber 403 Forbidden (RFC 9457) ---
    forbidden = client.get("/api/v1/students", headers=student_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # --- PASSO 2: PERSONAL listando sua carteira com paginação e filtro por objetivo -> 200 OK ---
    ok = client.get(
        "/api/v1/students?page=1&limit=10&goal=HYPERTROPHY",
        headers=personal_headers,
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["meta"]["totalItems"] >= 1
    student = body["data"][0]
    assert student["id"] == SEED_STUDENT_ID
    assert student["personalId"] == SEED_PERSONAL_ID
    assert student["profile"]["goal"] == "HYPERTROPHY"
    assert student["profile"]["weightKg"] == 78.5


def test_full_student_crud_by_personal_and_rbac_delete_protection(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo o ciclo completo de criação, leitura, atualização e exclusão (CRUD) de um aluno.

    Passo a Passo:
    - Passo 1 (Criação): `PERSONAL` envia `POST /api/v1/students` com dados cadastrais e objeto `profile` (1:1).
      Valida status `201`, vínculo automático com o Personal e cabeçalho `Location`.
    - Passo 2 (Leitura por ID): `PERSONAL` envia `GET /api/v1/students/{studentId}` e confirma retorno `200`.
    - Passo 3 (Atualização Parcial): `PERSONAL` envia `PATCH /api/v1/students/{studentId}` alterando `weightKg` e `goal`.
      Confirma retorno `200` com os novos valores persistidos no SQLite.
    - Passo 4 (Proteção RBAC na Exclusão): `STUDENT` tenta executar `DELETE /api/v1/students/{studentId}` e recebe `403`.
    - Passo 5 (Exclusão pelo Personal): `PERSONAL` executa `DELETE /api/v1/students/{studentId}` (`204`) e uma
      consulta subsequente retorna `404 Recurso Não Encontrado` (RFC 9457).
    """
    # --- PASSO 1: POST /api/v1/students (Personal cadastra nova aluna com perfil biométrico 1:1) ---
    create_res = client.post(
        "/api/v1/students",
        json={
            "name": "Mariana Aluna",
            "email": "mariana@gymflow.dev",
            "password": "Mariana@2026",
            "phone": "+5511988881111",
            "profile": {
                "birthDate": "2001-08-20",
                "weightKg": 62.0,
                "heightCm": 166.0,
                "goal": "WEIGHT_LOSS",
                "notes": "Sem restrições articulares.",
            },
        },
        headers=personal_headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    student_id = created["id"]
    assert created["profile"]["goal"] == "WEIGHT_LOSS"
    assert create_res.headers.get("Location") == f"/api/v1/students/{student_id}"

    # --- PASSO 2: GET /api/v1/students/{studentId} (Consultar detalhes da aluna recém-criada) ---
    get_res = client.get(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "mariana@gymflow.dev"

    # --- PASSO 3: PATCH /api/v1/students/{studentId} (Atualizar peso corporal e objetivo físico) ---
    patch_res = client.patch(
        f"/api/v1/students/{student_id}",
        json={"profile": {"weightKg": 60.5, "goal": "CONDITIONING"}},
        headers=personal_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["profile"]["weightKg"] == 60.5
    assert patch_res.json()["profile"]["goal"] == "CONDITIONING"

    # --- PASSO 4: DELETE por STUDENT -> deve ser bloqueado com 403 Forbidden (RBAC) ---
    del_forbidden = client.delete(
        f"/api/v1/students/{student_id}",
        headers=student_headers,
    )
    assert del_forbidden.status_code == 403
    assert del_forbidden.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # --- PASSO 5: DELETE por PERSONAL -> deve remover com 204 e retornar 404 após exclusão ---
    del_ok = client.delete(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert del_ok.status_code == 204

    after_del = client.get(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert after_del.status_code == 404


def test_student_analytics_bmi_and_rpe_metrics_and_dashboard(
    client: TestClient,
    personal_headers: dict[str, str],
) -> None:
    """Valida passo a passo o endpoint de indicadores biométricos (IMC) e estatísticas RPE (`/analytics`).

    Passo a Passo:
    - Passo 1: Enviar `GET /api/v1/students/{SEED_STUDENT_ID}/analytics` autenticado como `PERSONAL`.
    - Passo 2: Confirmar o cálculo do IMC (`78.5 / (1.78 * 1.78) = 24.78`), a classificação OMS
      (`Peso normal (Eutrófico)`), o total de fichas ativas, total de execuções e média RPE (`8.0`).
    - Passo 3: Consultar `GET /` para garantir que o painel interativo HTML está disponível (`200`).
    """
    # --- PASSO 1: Consultar os indicadores biométricos e de engajamento do aluno seed ---
    res = client.get(
        f"/api/v1/students/{SEED_STUDENT_ID}/analytics",
        headers=personal_headers,
    )

    # --- PASSO 2: Validar IMC, classificação OMS e métricas consolidadas de treino/RPE ---
    assert res.status_code == 200
    body = res.json()
    assert body["studentId"] == SEED_STUDENT_ID
    assert body["bmi"] == 24.78
    assert body["bmiClassification"] == "Peso normal (Eutrófico)"
    assert body["activeWorkoutPlans"] >= 1
    assert body["totalExecutions"] >= 1
    assert body["averageRpeScore"] == 8.0

    # --- PASSO 3: Verificar renderização do painel visual interativo em GET / ---
    dash_res = client.get("/")
    assert dash_res.status_code == 200
    assert "GymFlow API" in dash_res.text


def test_student_and_personal_horizontal_rbac_isolation(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo o isolamento horizontal (proteção contra IDOR) entre alunos e entre personais.

    Passo a Passo:
    - Passo 1: `PERSONAL` 1 (Carlos) cadastra um segundo aluno (`Lucas Outro Aluno`).
    - Passo 2: `STUDENT` 1 (Rodrigo) tenta acessar o perfil e o `/analytics` de Lucas -> ambos retornam `403`.
    - Passo 3: Um segundo Personal Trainer (`Bruno Outro Personal`) é registrado e autenticado via JWT.
    - Passo 4: `PERSONAL` 2 (Bruno) tenta consultar (`GET`), editar (`PATCH`) e remover (`DELETE`)
      um aluno pertencente à carteira do `PERSONAL` 1 (Carlos) -> todas as tentativas retornam `403`.
    """
    # --- PASSO 1: Personal 1 cadastra um segundo aluno na sua carteira ---
    create_res = client.post(
        "/api/v1/students",
        json={
            "name": "Lucas Outro Aluno",
            "email": "lucas.outro@gymflow.dev",
            "password": "Lucas@2026",
            "profile": {"goal": "HYPERTROPHY"},
        },
        headers=personal_headers,
    )
    assert create_res.status_code == 201
    other_student_id = create_res.json()["id"]

    # --- PASSO 2: Rodrigo (SEED_STUDENT_ID) tenta consultar perfil e analytics de Lucas -> 403 Forbidden ---
    res_get = client.get(f"/api/v1/students/{other_student_id}", headers=student_headers)
    assert res_get.status_code == 403
    assert res_get.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    res_ana = client.get(
        f"/api/v1/students/{other_student_id}/analytics",
        headers=student_headers,
    )
    assert res_ana.status_code == 403

    # --- PASSO 3: Registrar e autenticar um segundo Personal Trainer (Bruno) ---
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bruno Outro Personal",
            "email": "bruno.personal@gymflow.dev",
            "password": "Personal@2026",
            "role": "PERSONAL",
            "cref": "999888-G/SP",
        },
    )
    login_other = client.post(
        "/api/v1/auth/login",
        json={"email": "bruno.personal@gymflow.dev", "password": "Personal@2026"},
    )
    other_personal_headers = {
        "Authorization": f"Bearer {login_other.json()['accessToken']}"
    }

    # --- PASSO 4: Segundo Personal tenta consultar, editar ou excluir aluno do Personal 1 -> 403 Forbidden ---
    assert (
        client.get(
            f"/api/v1/students/{SEED_STUDENT_ID}", headers=other_personal_headers
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/students/{SEED_STUDENT_ID}",
            json={"name": "Tentativa Indevida"},
            headers=other_personal_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/students/{SEED_STUDENT_ID}", headers=other_personal_headers
        ).status_code
        == 403
    )
