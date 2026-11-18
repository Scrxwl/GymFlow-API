"""Testes de conformidade estrita com a RFC 9457 (Problem Details) da GymFlow API (400, 401, 403, 404, 422)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_STUDENT_ID

NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


def test_rfc9457_400_401_403_404_422_responses(
    client: TestClient,
    personal_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    # 1. 400 Bad Request (UUID inválido na rota)
    res_400 = client.get("/api/v1/students/nao-e-uuid", headers=personal_headers)
    assert res_400.status_code == 400
    assert res_400.json()["type"] == "https://api.gymflow.dev/errors/bad-request"
    assert len(res_400.json()["invalidParams"]) >= 1

    # 2. 401 Unauthorized (Sem token JWT)
    res_401 = client.get("/api/v1/students")
    assert res_401.status_code == 401
    assert res_401.json()["type"] == "https://api.gymflow.dev/errors/unauthorized"

    # 3. 403 Forbidden (STUDENT tentando remover aluno)
    res_403 = client.delete(
        f"/api/v1/students/{SEED_STUDENT_ID}",
        headers=student_headers,
    )
    assert res_403.status_code == 403
    assert res_403.json()["type"] == "https://api.gymflow.dev/errors/forbidden"

    # 4. 404 Not Found (Recurso inexistente)
    res_404 = client.get(
        f"/api/v1/workouts/{NONEXISTENT_UUID}",
        headers=personal_headers,
    )
    assert res_404.status_code == 404
    assert res_404.json()["type"] == "https://api.gymflow.dev/errors/not-found"

    # 5. 422 Unprocessable Entity (Violação de limites weightKg < 20 e rpeScore > 10)
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
