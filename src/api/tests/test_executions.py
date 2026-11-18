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
