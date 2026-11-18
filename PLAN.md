# PLAN.md — Roteiro Técnico de Implementação (GymFlow API: ORM + Auth)

> **Status:** 100% Concluído e Validado com `pytest -v`.

- [x] **Fase 1:** Estrutura de diretórios (`src/api/`, `src/api/routers/`, `src/api/tests/`) e `requirements.txt`.
- [x] **Fase 2:** Extração dos 26 schemas Pydantic v2 do Apidog em `src/api/schemas.py`.
- [x] **Fase 3:** Modelos ORM SQLAlchemy 2.0 (`UserModel`, `StudentProfileModel`, `WorkoutPlanModel`, `WorkoutRoutineModel`, `WorkoutExerciseModel`, `ExecutionModel`) e `database.py` com seed inicial.
- [x] **Fase 4:** Exceções RFC 9457 (`400`, `401`, `403`, `404`, `409`, `422`) em `src/api/exceptions.py` e JWT/RBAC (`PERSONAL` vs. `STUDENT`) em `src/api/security.py`.
- [x] **Fase 5:** Routers (`auth.py`, `students.py`, `workouts.py`, `executions.py`) com `selectinload` e `main.py`.
- [x] **Fase 6:** Suíte completa de testes `pytest` (`conftest.py`, `test_auth.py`, `test_students.py`, `test_workouts.py`, `test_executions.py`, `test_errors.py`).
