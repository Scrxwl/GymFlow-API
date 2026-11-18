"""Testes de CRUD de Planos de Treino, Rotinas e Exercícios (/api/v1/workouts) com selectinload 1:N."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_ROUTINE_ID, SEED_STUDENT_ID, SEED_WORKOUT_ID


def test_list_and_get_workout_with_nested_routines_and_exercises(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    list_res = client.get("/api/v1/workouts", headers=student_headers)
    assert list_res.status_code == 200
    workouts = list_res.json()["data"]
    assert len(workouts) >= 1
    assert workouts[0]["id"] == SEED_WORKOUT_ID
    assert len(workouts[0]["routines"]) >= 1
    assert len(workouts[0]["routines"][0]["exercises"]) >= 1

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

    # STUDENT não pode criar ficha de treino -> 403 Forbidden
    forbidden = client.post("/api/v1/workouts", json=payload, headers=student_headers)
    assert forbidden.status_code == 403

    # PERSONAL cria ficha com rotinas e exercícios em cascata -> 201 Created
    create_res = client.post("/api/v1/workouts", json=payload, headers=personal_headers)
    assert create_res.status_code == 201
    workout = create_res.json()
    workout_id = workout["id"]
    assert len(workout["routines"]) == 1
    assert len(workout["routines"][0]["exercises"]) == 1

    # Adiciona nova rotina ao plano
    routine_res = client.post(
        f"/api/v1/workouts/{workout_id}/routines",
        json={"name": "Treino C — Pernas Completo", "dayOfWeek": "FRIDAY", "order": 2},
        headers=personal_headers,
    )
    assert routine_res.status_code == 201
    routine_id = routine_res.json()["id"]

    # Adiciona exercício à nova rotina
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

    # Remove o exercício criado -> 204 No Content
    del_ex = client.delete(f"/api/v1/exercises/{ex_id}", headers=personal_headers)
    assert del_ex.status_code == 204

    # Atualiza metadados do plano -> 200 OK
    patch_res = client.patch(
        f"/api/v1/workouts/{workout_id}",
        json={"status": "ARCHIVED"},
        headers=personal_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "ARCHIVED"

    # Remove o plano de treino -> 204 No Content
    del_plan = client.delete(f"/api/v1/workouts/{workout_id}", headers=personal_headers)
    assert del_plan.status_code == 204
