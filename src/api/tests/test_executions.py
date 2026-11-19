"""Testes passo a passo de Check-in e Histórico de Execuções com Escala RPE Borg (`/api/v1/routines/{id}/executions`).

===============================================================================
ROTEIRO PASSO A PASSO DOS TESTES DE EXECUÇÕES DE TREINO (CHECK-IN RPE BORG)
===============================================================================
Este módulo valida o registro de sessões de treino concluídas pelos alunos
utilizando a Escala de Percepção Subjetiva de Esforço RPE Borg (`1` a `10`),
a listagem cronológica do histórico e o isolamento horizontal RBAC:

1. `test_create_and_list_workout_executions`:
   - Passo 1: `STUDENT` (Rodrigo) realiza o check-in pós-treino em sua rotina (`POST /api/v1/routines/{routineId}/executions`) informando `durationMinutes=60`, `rpeScore=9` e `feedback`.
   - Passo 2: Valida o retorno `201` e a vinculação correta com `studentId` e `routineId`.
   - Passo 3: `STUDENT` consulta seu histórico de execuções (`GET /api/v1/students/{studentId}/executions`) e confirma que o novo check-in aparece na listagem.

2. `test_execution_horizontal_rbac_isolation`:
   - Passo 1: `PERSONAL` cadastra uma segunda aluna (`Camila Outra Aluna`) e realiza login com o token dela.
   - Passo 2: Camila tenta registrar check-in na rotina pertencente ao plano de Rodrigo (`SEED_ROUTINE_ID`) -> bloqueada com `403`.
   - Passo 3: Camila tenta consultar o histórico de treinos executados por Rodrigo (`SEED_STUDENT_ID`) -> bloqueada com `403`.
===============================================================================
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ..database import SEED_ROUTINE_ID, SEED_STUDENT_ID


def test_create_and_list_workout_executions(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    """Valida passo a passo o registro de check-in RPE pelo aluno e a consulta do histórico de execuções.

    Passo a Passo:
    - Passo 1: Enviar `POST /api/v1/routines/{SEED_ROUTINE_ID}/executions` com token do aluno titular,
      duração de 60 minutos, nota RPE Borg 9 e feedback textual.
    - Passo 2: Confirmar retorno `201` e verificar `studentId`, `routineId` e `rpeScore`.
    - Passo 3: Enviar `GET /api/v1/students/{SEED_STUDENT_ID}/executions` e confirmar retorno `200`
      contendo o histórico atualizado com a nova sessão.
    """
    # --- PASSO 1: Aluno registra check-in pós-treino na rotina prescrita para ele ---
    create_res = client.post(
        f"/api/v1/routines/{SEED_ROUTINE_ID}/executions",
        json={
            "durationMinutes": 60,
            "rpeScore": 9,
            "feedback": "Treino intenso, mantive a técnica até a última série.",
        },
        headers=student_headers,
    )

    # --- PASSO 2: Validar resposta 201 Created e dados persistidos ---
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["studentId"] == SEED_STUDENT_ID
    assert created["routineId"] == SEED_ROUTINE_ID
    assert created["rpeScore"] == 9

    # --- PASSO 3: Consultar histórico de execuções do aluno e confirmar presença do novo registro ---
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
    """Valida passo a passo que um aluno não pode fazer check-in nem ler histórico de outro aluno.

    Passo a Passo:
    - Passo 1: `PERSONAL` cadastra uma segunda aluna (`Camila Outra Aluna`) e realiza login com ela.
    - Passo 2: Camila envia `POST /api/v1/routines/{SEED_ROUTINE_ID}/executions` tentando registrar
      execução em uma rotina vinculada ao aluno Rodrigo -> deve retornar `403` (RFC 9457).
    - Passo 3: Camila envia `GET /api/v1/students/{SEED_STUDENT_ID}/executions` tentando ler o
      histórico de execuções de Rodrigo -> deve retornar `403` (RFC 9457).
    """
    # --- PASSO 1: Personal cadastra outra aluna (Camila) e obtém o token JWT dela ---
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

    # --- PASSO 2: Camila tenta registrar check-in na rotina do Rodrigo (SEED_ROUTINE_ID) -> 403 Forbidden ---
    checkin_forbidden = client.post(
        f"/api/v1/routines/{SEED_ROUTINE_ID}/executions",
        json={"durationMinutes": 45, "rpeScore": 7},
        headers=camila_headers,
    )
    assert checkin_forbidden.status_code == 403

    # --- PASSO 3: Camila tenta listar histórico de execuções do Rodrigo (SEED_STUDENT_ID) -> 403 Forbidden ---
    hist_forbidden = client.get(
        f"/api/v1/students/{SEED_STUDENT_ID}/executions",
        headers=camila_headers,
    )
    assert hist_forbidden.status_code == 403
