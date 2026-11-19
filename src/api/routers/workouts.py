"""Endpoints de Planos de Treino, Rotinas e Exercícios (/api/v1/workouts, /routines, /exercises) com selectinload."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..exceptions import ApiErrorException, validate_uuid_param
from ..models import (
    UserModel,
    WorkoutExerciseModel,
    WorkoutPlanModel,
    WorkoutRoutineModel,
)
from ..schemas import (
    CreateWorkoutPlanDTO,
    PaginatedWorkoutsResponse,
    PaginationMeta,
    UpdateWorkoutPlanDTO,
    UserRole,
    WorkoutExerciseDTO,
    WorkoutExerciseResponse,
    WorkoutPlanResponse,
    WorkoutRoutineDTO,
    WorkoutRoutineResponse,
    WorkoutStatus,
)
from ..security import get_current_user, require_roles

router = APIRouter(prefix="/api/v1", tags=["Workouts"])


def _workout_eager_query():
    """Retorna select(WorkoutPlanModel) com selectinload em cascata para routines e exercises (evita N+1)."""
    return select(WorkoutPlanModel).options(
        selectinload(WorkoutPlanModel.routines).selectinload(WorkoutRoutineModel.exercises)
    )


@router.get(
    "/workouts",
    response_model=PaginatedWorkoutsResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar fichas de treino com filtros e paginação (selectinload 1:N)",
)
def list_workouts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    studentId: Optional[str] = Query(default=None),
    status_filter: Optional[WorkoutStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> PaginatedWorkoutsResponse:
    stmt = _workout_eager_query()

    if current_user.role == UserRole.STUDENT.value:
        stmt = stmt.where(WorkoutPlanModel.student_id == current_user.id)
    else:
        stmt = stmt.where(WorkoutPlanModel.personal_id == current_user.id)
        if studentId is not None:
            valid_student_id = validate_uuid_param(studentId, param_name="studentId")
            stmt = stmt.where(WorkoutPlanModel.student_id == valid_student_id)

    if status_filter is not None:
        stmt = stmt.where(WorkoutPlanModel.status == status_filter.value)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_items = db.scalar(count_stmt) or 0
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    has_next = page < total_pages

    offset = (page - 1) * limit
    plans = db.scalars(
        stmt.order_by(WorkoutPlanModel.created_at.desc()).offset(offset).limit(limit)
    ).all()

    return PaginatedWorkoutsResponse(
        data=[WorkoutPlanResponse.model_validate(plan) for plan in plans],
        meta=PaginationMeta(
            page=page,
            limit=limit,
            totalItems=total_items,
            totalPages=total_pages,
            hasNext=has_next,
        ),
    )


@router.post(
    "/workouts",
    response_model=WorkoutPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo plano de treino completo com rotinas e exercícios (Restrito a PERSONAL)",
)
def create_workout_plan(
    payload: CreateWorkoutPlanDTO,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> WorkoutPlanResponse:
    student = db.scalar(
        select(UserModel).where(
            UserModel.id == payload.studentId,
            UserModel.role == UserRole.STUDENT.value,
        )
    )
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{payload.studentId}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if student.personal_id is not None and student.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode prescrever fichas de treino para alunos da sua própria carteira.",
            instance=str(request.url.path),
        )

    now = datetime.now(timezone.utc)
    new_plan = WorkoutPlanModel(
        personal_id=current_user.id,
        student_id=payload.studentId,
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        start_date=payload.startDate,
        end_date=payload.endDate,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_plan)
        db.flush()

        for routine_dto in payload.routines:
            new_routine = WorkoutRoutineModel(
                workout_plan_id=new_plan.id,
                name=routine_dto.name,
                day_of_week=routine_dto.dayOfWeek,
                order=routine_dto.order,
            )
            db.add(new_routine)
            db.flush()

            for ex_dto in routine_dto.exercises:
                db.add(
                    WorkoutExerciseModel(
                        routine_id=new_routine.id,
                        name=ex_dto.name,
                        muscle_group=ex_dto.muscleGroup.value,
                        sets=ex_dto.sets,
                        reps=ex_dto.reps,
                        rest_seconds=ex_dto.restSeconds,
                        weight_kg=ex_dto.weightKg,
                        notes=ex_dto.notes,
                        order=ex_dto.order,
                    )
                )

        db.commit()
    except Exception:
        db.rollback()
        raise

    loaded = db.scalar(_workout_eager_query().where(WorkoutPlanModel.id == new_plan.id))
    response.headers["Location"] = f"/api/v1/workouts/{new_plan.id}"
    return WorkoutPlanResponse.model_validate(loaded)


@router.get(
    "/workouts/{workoutId}",
    response_model=WorkoutPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter plano de treino completo por ID com selectinload",
)
def get_workout_by_id(
    workoutId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> WorkoutPlanResponse:
    valid_id = validate_uuid_param(workoutId, param_name="workoutId")
    plan = db.scalar(_workout_eager_query().where(WorkoutPlanModel.id == valid_id))
    if not plan:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plano de treino com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if current_user.role == UserRole.STUDENT.value and plan.student_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Um aluno só pode consultar os seus próprios planos de treino.",
            instance=str(request.url.path),
        )

    if current_user.role == UserRole.PERSONAL.value and plan.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este plano de treino pertence à carteira de outro Personal Trainer.",
            instance=str(request.url.path),
        )

    return WorkoutPlanResponse.model_validate(plan)


@router.patch(
    "/workouts/{workoutId}",
    response_model=WorkoutPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar metadados do plano de treino (Restrito a PERSONAL)",
)
def update_workout_plan(
    workoutId: str,
    payload: UpdateWorkoutPlanDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> WorkoutPlanResponse:
    valid_id = validate_uuid_param(workoutId, param_name="workoutId")
    plan = db.scalar(_workout_eager_query().where(WorkoutPlanModel.id == valid_id))
    if not plan:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plano de treino com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if plan.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode gerenciar planos de treino prescritos na sua própria carteira.",
            instance=str(request.url.path),
        )

    if payload.title is not None:
        plan.title = payload.title
    if payload.description is not None:
        plan.description = payload.description
    if payload.status is not None:
        plan.status = payload.status.value
    if payload.startDate is not None:
        plan.start_date = payload.startDate
    if payload.endDate is not None:
        plan.end_date = payload.endDate

    plan.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        raise

    return WorkoutPlanResponse.model_validate(plan)


@router.delete(
    "/workouts/{workoutId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover plano de treino em cascata (Exclusivo PERSONAL)",
)
def delete_workout_plan(
    workoutId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> Response:
    valid_id = validate_uuid_param(workoutId, param_name="workoutId")
    plan = db.scalar(select(WorkoutPlanModel).where(WorkoutPlanModel.id == valid_id))
    if not plan:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plano de treino com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if plan.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode remover planos de treino prescritos na sua própria carteira.",
            instance=str(request.url.path),
        )

    try:
        db.delete(plan)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workouts/{workoutId}/routines",
    response_model=WorkoutRoutineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar divisão de rotina ao plano de treino (Restrito a PERSONAL)",
)
def add_routine_to_workout(
    workoutId: str,
    payload: WorkoutRoutineDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> WorkoutRoutineResponse:
    valid_id = validate_uuid_param(workoutId, param_name="workoutId")
    plan = db.scalar(select(WorkoutPlanModel).where(WorkoutPlanModel.id == valid_id))
    if not plan:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plano de treino com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if plan.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode adicionar rotinas a planos de treino da sua própria carteira.",
            instance=str(request.url.path),
        )

    new_routine = WorkoutRoutineModel(
        workout_plan_id=plan.id,
        name=payload.name,
        day_of_week=payload.dayOfWeek,
        order=payload.order,
    )
    try:
        db.add(new_routine)
        db.flush()
        for ex_dto in payload.exercises:
            db.add(
                WorkoutExerciseModel(
                    routine_id=new_routine.id,
                    name=ex_dto.name,
                    muscle_group=ex_dto.muscleGroup.value,
                    sets=ex_dto.sets,
                    reps=ex_dto.reps,
                    rest_seconds=ex_dto.restSeconds,
                    weight_kg=ex_dto.weightKg,
                    notes=ex_dto.notes,
                    order=ex_dto.order,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    loaded = db.scalar(
        select(WorkoutRoutineModel)
        .options(selectinload(WorkoutRoutineModel.exercises))
        .where(WorkoutRoutineModel.id == new_routine.id)
    )
    return WorkoutRoutineResponse.model_validate(loaded)


@router.post(
    "/routines/{routineId}/exercises",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar exercício a uma rotina de treino (Restrito a PERSONAL)",
)
def add_exercise_to_routine(
    routineId: str,
    payload: WorkoutExerciseDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> WorkoutExerciseResponse:
    valid_id = validate_uuid_param(routineId, param_name="routineId")
    routine = db.scalar(
        select(WorkoutRoutineModel).where(WorkoutRoutineModel.id == valid_id)
    )
    if not routine:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rotina de treino com id '{valid_id}' não foi encontrada.",
            instance=str(request.url.path),
        )

    plan = db.scalar(
        select(WorkoutPlanModel).where(WorkoutPlanModel.id == routine.workout_plan_id)
    )
    if plan and plan.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode adicionar exercícios a rotinas da sua própria carteira.",
            instance=str(request.url.path),
        )

    new_ex = WorkoutExerciseModel(
        routine_id=routine.id,
        name=payload.name,
        muscle_group=payload.muscleGroup.value,
        sets=payload.sets,
        reps=payload.reps,
        rest_seconds=payload.restSeconds,
        weight_kg=payload.weightKg,
        notes=payload.notes,
        order=payload.order,
    )
    try:
        db.add(new_ex)
        db.commit()
        db.refresh(new_ex)
    except Exception:
        db.rollback()
        raise

    return WorkoutExerciseResponse.model_validate(new_ex)


@router.delete(
    "/exercises/{exerciseId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover exercício de uma rotina (Restrito a PERSONAL)",
)
def delete_exercise(
    exerciseId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> Response:
    valid_id = validate_uuid_param(exerciseId, param_name="exerciseId")
    exercise = db.scalar(
        select(WorkoutExerciseModel).where(WorkoutExerciseModel.id == valid_id)
    )
    if not exercise:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercício com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    routine = db.scalar(
        select(WorkoutRoutineModel).where(WorkoutRoutineModel.id == exercise.routine_id)
    )
    if routine:
        plan = db.scalar(
            select(WorkoutPlanModel).where(WorkoutPlanModel.id == routine.workout_plan_id)
        )
        if plan and plan.personal_id != current_user.id:
            raise ApiErrorException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode remover exercícios de rotinas da sua própria carteira.",
                instance=str(request.url.path),
            )

    try:
        db.delete(exercise)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)
