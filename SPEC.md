# SPEC.md — Especificação de Negócio, ORM e Autenticação (GymFlow API)

## 1. Visão Geral e Equipe
A **GymFlow API — Gestão de Treinos e Acompanhamento Físico** é uma API RESTful projetada sob a metodologia **Design-First no Apidog** e **Spec-Driven Development (SDD)** com **SQLAlchemy 2.0 ORM** e **Autenticação Stateless JWT + RBAC (`PERSONAL` e `STUDENT`)**, seguindo o padrão de erros **RFC 9457 (Problem Details)**.

### Equipe (Fatec Ribeirão Preto)
- **João Gabriel Cardoso** — RA: `2840482421028`
- **Rodrigo de Azevedo Junior** — RA: `2840482421044`
- **Thales de Oliveira Silva** — RA: `2840482413031`

---

## 2. Entidades e Contratos Pydantic v2 (Schema-First)
Extraídos diretamente dos 26 `Data Schemas` do Apidog (`https://3f9huyoq5b.apidog.io/readme-2508436m0`):
1. **Enums:**
   - `UserRole`: `"PERSONAL"`, `"STUDENT"`
   - `FitnessGoal`: `"HYPERTROPHY"`, `"WEIGHT_LOSS"`, `"CONDITIONING"`, `"REHABILITATION"`, `"GENERAL_FITNESS"`
   - `MuscleGroup`: `"CHEST"`, `"BACK"`, `"LEGS"`, `"SHOULDERS"`, `"BICEPS"`, `"TRICEPS"`, `"CORE"`, `"CARDIO"`
   - `WorkoutStatus`: `"ACTIVE"`, `"INACTIVE"`, `"ARCHIVED"`
2. **Autenticação (`/api/v1/auth`):**
   - `RegisterUserDTO`, `LoginRequestDTO`, `UserResponse`, `AuthTokenResponse`.
3. **Alunos (`Students` — `/api/v1/students`):**
   - `StudentProfileDTO`, `CreateStudentDTO`, `UpdateStudentDTO`, `StudentResponse`, `PaginatedStudentsResponse`.
4. **Planos de Treino, Rotinas e Exercícios (`Workouts` — `/api/v1/workouts`):**
   - `WorkoutExerciseDTO`, `WorkoutExerciseResponse`, `WorkoutRoutineDTO`, `WorkoutRoutineResponse`, `CreateWorkoutPlanDTO`, `UpdateWorkoutPlanDTO`, `WorkoutPlanResponse`, `PaginatedWorkoutsResponse`.
5. **Execuções / Check-in RPE (`Executions`):**
   - `CreateExecutionDTO` (`durationMinutes`: 5 a 300, `rpeScore`: 1 a 10 Escala Borg, `feedback` opcional), `ExecutionResponse`.
6. **Erros e Paginação:**
   - `InvalidParam`, `ApiError` (RFC 9457 com URIs `https://api.gymflow.dev/errors/...`) e `PaginationMeta`.

---

## 3. Mapeamento Objeto-Relacional — SQLAlchemy 2.0 ORM
- `UserModel` (`users`) com auto-relacionamento opcional `personal_id -> users.id` e relacionamento `1:1` com `StudentProfileModel` (`student_profiles`).
- `WorkoutPlanModel` (`workout_plans`) com relacionamento `1:N` para `WorkoutRoutineModel` (`workout_routines`), que por sua vez possui relacionamento `1:N` para `WorkoutExerciseModel` (`workout_exercises`) e `ExecutionModel` (`executions`).
- Prevenção de queries **N+1** com `selectinload` no carregamento de alunos com perfil biométrico e de fichas de treino com suas rotinas e exercícios aninhados.

---

## 4. Matriz de Controle de Acesso (RBAC: `PERSONAL` vs. `STUDENT`)
- **`POST /api/v1/auth/register` e `POST /api/v1/auth/login`**: Públicos.
- **`GET /api/v1/auth/me`**: Autenticado (`PERSONAL` ou `STUDENT`).
- **`GET /api/v1/students`, `POST /api/v1/students`, `PATCH /api/v1/students/{studentId}`, `DELETE /api/v1/students/{studentId}`**: Exclusivos para `PERSONAL` (retornam `401` sem token e `403 Forbidden` RFC 9457 para `STUDENT`).
- **`GET /api/v1/students/{studentId}`**: Acessível pelo `PERSONAL` responsável ou pelo próprio `STUDENT`.
- **`POST /api/v1/workouts`, `PATCH /api/v1/workouts/{workoutId}`, `DELETE /api/v1/workouts/{workoutId}`, `POST /api/v1/workouts/{workoutId}/routines`, `POST /api/v1/routines/{routineId}/exercises`, `DELETE /api/v1/exercises/{exerciseId}`**: Exclusivos para `PERSONAL` (`403 Forbidden` para `STUDENT`).
- **`GET /api/v1/workouts` e `GET /api/v1/workouts/{workoutId}`**: Autenticados (`PERSONAL` ou `STUDENT`).
- **`POST /api/v1/routines/{routineId}/executions` e `GET /api/v1/students/{studentId}/executions`**: Autenticados (`STUDENT` ou `PERSONAL`).
