"""Testes de registro, login JWT e perfil (/api/v1/auth) da GymFlow API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_personal_and_login_jwt(client: TestClient) -> None:
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
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["role"] == "PERSONAL"
    assert user_data["cref"] == "654321-G/SP"

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "fernanda@gymflow.dev", "password": "Personal@2026"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "accessToken" in token_data
    assert token_data["tokenType"] == "bearer"
    assert token_data["user"]["email"] == "fernanda@gymflow.dev"


def test_login_invalid_credentials_returns_401_rfc9457(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "carlos@gymflow.dev", "password": "WrongPassword999"},
    )
    assert res.status_code == 401
    err = res.json()
    assert err["type"] == "https://api.gymflow.dev/errors/unauthorized"
    assert err["status"] == 401


def test_get_me_authenticated_and_unauthenticated(
    client: TestClient,
    personal_headers: dict[str, str],
) -> None:
    unauth = client.get("/api/v1/auth/me")
    assert unauth.status_code == 401

    ok = client.get("/api/v1/auth/me", headers=personal_headers)
    assert ok.status_code == 200
    assert ok.json()["email"] == "carlos@gymflow.dev"
    assert ok.json()["role"] == "PERSONAL"
