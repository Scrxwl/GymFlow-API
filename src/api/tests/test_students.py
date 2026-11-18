"""Testes de CRUD, perfil biométrico 1:1 e RBAC da entidade Students (/api/v1/students)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_PERSONAL_ID, SEED_STUDENT_ID


def test_list_students_paginated_for_personal_and_403_for_student(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    # STUDENT tentando listar carteira de alunos -> 403 Forbidden
    forbidden = client.get("/api/v1/students", headers=student_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # PERSONAL listando sua carteira -> 200 OK
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
    # 1. POST /api/v1/students (Criar aluno com perfil biométrico)
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

    # 2. GET /api/v1/students/{studentId}
    get_res = client.get(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "mariana@gymflow.dev"

    # 3. PATCH /api/v1/students/{studentId}
    patch_res = client.patch(
        f"/api/v1/students/{student_id}",
        json={"profile": {"weightKg": 60.5, "goal": "CONDITIONING"}},
        headers=personal_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["profile"]["weightKg"] == 60.5
    assert patch_res.json()["profile"]["goal"] == "CONDITIONING"

    # 4. DELETE por STUDENT -> 403 Forbidden (RBAC)
    del_forbidden = client.delete(
        f"/api/v1/students/{student_id}",
        headers=student_headers,
    )
    assert del_forbidden.status_code == 403
    assert del_forbidden.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # 5. DELETE por PERSONAL -> 204 No Content
    del_ok = client.delete(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert del_ok.status_code == 204

    after_del = client.get(f"/api/v1/students/{student_id}", headers=personal_headers)
    assert after_del.status_code == 404


def test_student_analytics_bmi_and_rpe_metrics_and_dashboard(
    client: TestClient,
    personal_headers: dict[str, str],
) -> None:
    """[Conteúdo Extra] Deve calcular IMC (BMI), classificação biométrica e média RPE do aluno."""
    res = client.get(
        f"/api/v1/students/{SEED_STUDENT_ID}/analytics",
        headers=personal_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["studentId"] == SEED_STUDENT_ID
    assert body["bmi"] == 24.78
    assert body["bmiClassification"] == "Peso normal (Eutrófico)"
    assert body["activeWorkoutPlans"] >= 1
    assert body["totalExecutions"] >= 1
    assert body["averageRpeScore"] == 8.0

    dash_res = client.get("/")
    assert dash_res.status_code == 200
    assert "GymFlow API" in dash_res.text
