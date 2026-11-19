"""Testes passo a passo de Planos de Treino, Rotinas e Exercícios (`/api/v1/workouts`) com `selectinload` 1:N.

===============================================================================
ROTEIRO PASSO A PASSO DOS TESTES DE FICHAS DE TREINO, ROTINAS E EXERCÍCIOS
===============================================================================
Este módulo valida a árvore relacional 1:N (`WorkoutPlanModel` -> `WorkoutRoutineModel`
-> `WorkoutExerciseModel`) carregada via `selectinload` no SQLAlchemy 2.0 (prevenindo
queries N+1), além das regras de permissão RBAC (`PERSONAL` vs `STUDENT`):

1. `test_list_and_get_workout_with_nested_routines_and_exercises`:
   - Passo 1: `STUDENT` lista suas fichas de treino (`GET /api/v1/workouts`) e recebe as rotinas e exercícios aninhados em uma única operação ORM (`selectinload`).
   - Passo 2: `STUDENT` consulta os detalhes da sua ficha por ID (`GET /api/v1/workouts/{workoutId}`) e confirma o título e estrutura.

2. `test_create_update_delete_workout_and_subresources`:
   - Passo 1: `STUDENT` tenta prescrever uma nova ficha (`POST /api/v1/workouts`) -> bloqueado com `403`.
   - Passo 2: `PERSONAL` cria uma ficha completa com rotina e exercício em cascata (`POST /api/v1/workouts` -> `201`).
   - Passo 3: `PERSONAL` adiciona uma nova divisão de rotina (Treino C) à ficha (`POST /api/v1/workouts/{workoutId}/routines` -> `201`).
   - Passo 4: `PERSONAL` adiciona um novo exercício à rotina criada (`POST /api/v1/routines/{routineId}/exercises` -> `201`).
   - Passo 5: `PERSONAL` remove o exercício (`DELETE /api/v1/exercises/{exerciseId}` -> `204`).
   - Passo 6: `PERSONAL` arquiva a ficha (`PATCH /api/v1/workouts/{workoutId}` com `status="ARCHIVED"` -> `200`).
   - Passo 7: `PERSONAL` exclui a ficha em cascata (`DELETE /api/v1/workouts/{workoutId}` -> `204`).

3. `test_workout_horizontal_rbac_isolation`:
   - Passo 1: Cadastra e autentica uma segunda aluna (`Julia Aluna`).
   - Passo 2: Julia tenta acessar a ficha de treino do aluno Rodrigo (`SEED_WORKOUT_ID`) -> bloqueada com `403`.
   - Passo 3: Cadastra e autentica um segundo Personal Trainer (`Rafael Outro Personal`).
   - Passo 4: Rafael tenta alterar (`PATCH`) ou excluir (`DELETE`) a ficha criada pelo Personal Carlos -> bloqueado com `403`.
===============================================================================
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_STUDENT_ID, SEED_WORKOUT_ID


def test_list_and_get_workout_with_nested_routines_and_exercises(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo a leitura de fichas de treino com rotinas e exercícios aninhados (`selectinload`).

    Passo a Passo:
    - Passo 1: Enviar `GET /api/v1/workouts` autenticado como `STUDENT`.
      Confirmar status `200` e verificar que a ficha contém a lista `routines` e, dentro dela, a lista `exercises`.
    - Passo 2: Enviar `GET /api/v1/workouts/{SEED_WORKOUT_ID}` autenticado como o `STUDENT` destinatário.
      Confirmar status `200` e o título da ficha prescrita.
    """
    # --- PASSO 1: Listar fichas de treino do aluno logado com carregamento eager (selectinload) ---
    list_res = client.get("/api/v1/workouts", headers=student_headers)
    assert list_res.status_code == 200
    workouts = list_res.json()["data"]
    assert len(workouts) >= 1
    assert workouts[0]["id"] == SEED_WORKOUT_ID
    assert len(workouts[0]["routines"]) >= 1
    assert len(workouts[0]["routines"][0]["exercises"]) >= 1

    # --- PASSO 2: Consultar plano de treino específico por UUID ---
    detail_res = client.get(
        f"/api/v1/workouts/{SEED_WORKOUT_ID}",
        headers=student_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Mesociclo 01 — Hipertrofia Base ABC"


def test_create_update_delete_workout_and_subresources(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo a prescrição em cascata e manutenção de fichas, rotinas e exercícios pelo PERSONAL.

    Passo a Passo:
    - Passo 1: `STUDENT` tenta criar um plano de treino (`POST /api/v1/workouts`) -> bloqueado com `403`.
    - Passo 2: `PERSONAL` cria o plano com rotinas e exercícios aninhados (`POST /api/v1/workouts` -> `201`).
    - Passo 3: `PERSONAL` adiciona uma nova divisão de rotina ao plano (`POST /api/v1/workouts/{id}/routines` -> `201`).
    - Passo 4: `PERSONAL` adiciona um exercício à nova rotina (`POST /api/v1/routines/{id}/exercises` -> `201`).
    - Passo 5: `PERSONAL` exclui o exercício criado (`DELETE /api/v1/exercises/{id}` -> `204`).
    - Passo 6: `PERSONAL` atualiza o status do plano para `ARCHIVED` (`PATCH /api/v1/workouts/{id}` -> `200`).
    - Passo 7: `PERSONAL` remove o plano de treino (`DELETE /api/v1/workouts/{id}` -> `204`).
    """
    payload = {
        "studentId": SEED_STUDENT_ID,
        "title": "Mesociclo 02 — Força e Potência",
        "description": "Foco em exercícios multiarticulares compostos.",
        "status": "ACTIVE",
        "startDate": "2026-06-01",
        "endDate": "2026-08-01",
        "routines": [
            {
                "name": "Treino B — Costas e Bíceps",
                "dayOfWeek": "WEDNESDAY",
                "order": 1,
                "exercises": [
                    {
                        "name": "Remada Curvada Pronada",
                        "muscleGroup": "BACK",
                        "sets": 4,
                        "reps": "6-8",
                        "restSeconds": 120,
                        "weightKg": 70.0,
                        "order": 1,
                    }
                ],
            }
        ],
    }

    # --- PASSO 1: STUDENT tenta criar ficha de treino -> deve ser bloqueado com 403 Forbidden ---
    forbidden = client.post("/api/v1/workouts", json=payload, headers=student_headers)
    assert forbidden.status_code == 403

    # --- PASSO 2: PERSONAL cria ficha completa com rotinas e exercícios em cascata -> 201 Created ---
    create_res = client.post("/api/v1/workouts", json=payload, headers=personal_headers)
    assert create_res.status_code == 201
    workout = create_res.json()
    workout_id = workout["id"]
    assert len(workout["routines"]) == 1
    assert len(workout["routines"][0]["exercises"]) == 1

    # --- PASSO 3: PERSONAL adiciona nova divisão de rotina (Treino C) ao plano -> 201 Created ---
    routine_res = client.post(
        f"/api/v1/workouts/{workout_id}/routines",
        json={"name": "Treino C — Pernas Completo", "dayOfWeek": "FRIDAY", "order": 2},
        headers=personal_headers,
    )
    assert routine_res.status_code == 201
    routine_id = routine_res.json()["id"]

    # --- PASSO 4: PERSONAL adiciona novo exercício à rotina recém-criada -> 201 Created ---
    ex_res = client.post(
        f"/api/v1/routines/{routine_id}/exercises",
        json={
            "name": "Agachamento Livre",
            "muscleGroup": "LEGS",
            "sets": 5,
            "reps": "5",
            "restSeconds": 180,
            "weightKg": 100.0,
            "order": 1,
        },
        headers=personal_headers,
    )
    assert ex_res.status_code == 201
    ex_id = ex_res.json()["id"]

    # --- PASSO 5: PERSONAL remove o exercício criado -> 204 No Content ---
    del_ex = client.delete(f"/api/v1/exercises/{ex_id}", headers=personal_headers)
    assert del_ex.status_code == 204

    # --- PASSO 6: PERSONAL atualiza metadados do plano para ARCHIVED -> 200 OK ---
    patch_res = client.patch(
        f"/api/v1/workouts/{workout_id}",
        json={"status": "ARCHIVED"},
        headers=personal_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "ARCHIVED"

    # --- PASSO 7: PERSONAL remove o plano de treino em cascata -> 204 No Content ---
    del_plan = client.delete(f"/api/v1/workouts/{workout_id}", headers=personal_headers)
    assert del_plan.status_code == 204


def test_workout_horizontal_rbac_isolation(
    client: TestClient,
    personal_headers: dict[str, str],
) -> None:
    """Valida passo a passo que um aluno não acessa ficha de outro aluno e outro Personal não altera ficha alheia.

    Passo a Passo:
    - Passo 1: `PERSONAL` 1 cadastra uma nova aluna (`Julia Aluna`) e realiza login com as credenciais dela.
    - Passo 2: Julia tenta consultar a ficha de treino de Rodrigo (`GET /api/v1/workouts/{SEED_WORKOUT_ID}`) -> `403`.
    - Passo 3: Um segundo Personal (`Rafael Outro Personal`) se registra e faz login.
    - Passo 4: Rafael tenta atualizar (`PATCH`) e remover (`DELETE`) a ficha prescrita por Carlos -> ambos retornam `403`.
    """
    # --- PASSO 1: Personal 1 cria outra aluna (Julia) e obtém o token JWT dela ---
    client.post(
        "/api/v1/students",
        json={
            "name": "Julia Aluna",
            "email": "julia@gymflow.dev",
            "password": "Julia@2026",
            "profile": {"goal": "CONDITIONING"},
        },
        headers=personal_headers,
    )
    login_julia = client.post(
        "/api/v1/auth/login",
        json={"email": "julia@gymflow.dev", "password": "Julia@2026"},
    )
    julia_headers = {"Authorization": f"Bearer {login_julia.json()['accessToken']}"}

    # --- PASSO 2: Julia tenta acessar ficha de treino do Rodrigo (SEED_WORKOUT_ID) -> 403 Forbidden ---
    res_julia = client.get(
        f"/api/v1/workouts/{SEED_WORKOUT_ID}",
        headers=julia_headers,
    )
    assert res_julia.status_code == 403

    # --- PASSO 3: Registrar e autenticar um segundo Personal Trainer (Rafael) ---
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Rafael Outro Personal",
            "email": "rafael.personal@gymflow.dev",
            "password": "Personal@2026",
            "role": "PERSONAL",
            "cref": "112233-G/SP",
        },
    )
    login_rafael = client.post(
        "/api/v1/auth/login",
        json={"email": "rafael.personal@gymflow.dev", "password": "Personal@2026"},
    )
    rafael_headers = {"Authorization": f"Bearer {login_rafael.json()['accessToken']}"}

    # --- PASSO 4: Segundo Personal tenta alterar ou excluir ficha do Personal 1 -> 403 Forbidden ---
    assert (
        client.patch(
            f"/api/v1/workouts/{SEED_WORKOUT_ID}",
            json={"title": "Alteração Indevida"},
            headers=rafael_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/workouts/{SEED_WORKOUT_ID}",
            headers=rafael_headers,
        ).status_code
        == 403
    )
