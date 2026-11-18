"""Testes de check-in e histórico de execuções com Escala RPE Borg (/api/v1/routines/{id}/executions)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_ROUTINE_ID, SEED_STUDENT_ID


def test_create_and_list_workout_executions(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    create_res = client.post(
        f"/api/v1/routines/{SEED_ROUTINE_ID}/executions",
        json={
            "durationMinutes": 60,
            "rpeScore": 9,
            "feedback": "Treino intenso, mantive a técnica até a última série.",
        },
        headers=student_headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["studentId"] == SEED_STUDENT_ID
    assert created["routineId"] == SEED_ROUTINE_ID
    assert created["rpeScore"] == 9

    history_res = client.get(
        f"/api/v1/students/{SEED_STUDENT_ID}/executions",
        headers=student_headers,
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 2
    assert any(item["id"] == created["id"] for item in history)


def test_execution_horizontal_rbac_isolation(
    client: TestClient,
    personal_headers: dict[str, str],
) -> None:
    """Garante que um aluno não possa registrar check-in nem ler histórico de execuções de outro aluno."""
    # Personal cadastra outro aluno e faz login com ele
    client.post(
        "/api/v1/students",
        json={
            "name": "Camila Outra Aluna",
            "email": "camila@gymflow.dev",
            "password": "Camila@2026",
            "profile": {"goal": "WEIGHT_LOSS"},
        },
        headers=personal_headers,
    )
    login_camila = client.post(
        "/api/v1/auth/login",
        json={"email": "camila@gymflow.dev", "password": "Camila@2026"},
    )
    camila_headers = {"Authorization": f"Bearer {login_camila.json()['accessToken']}"}

    # Camila tenta registrar check-in na rotina do Rodrigo (SEED_ROUTINE_ID) -> 403 Forbidden
    checkin_forbidden = client.post(
        f"/api/v1/routines/{SEED_ROUTINE_ID}/executions",
        json={"durationMinutes": 45, "rpeScore": 7},
        headers=camila_headers,
    )
    assert checkin_forbidden.status_code == 403

    # Camila tenta listar histórico de execuções do Rodrigo (SEED_STUDENT_ID) -> 403 Forbidden
    hist_forbidden = client.get(
        f"/api/v1/students/{SEED_STUDENT_ID}/executions",
        headers=camila_headers,
    )
    assert hist_forbidden.status_code == 403
