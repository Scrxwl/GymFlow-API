"""Endpoints de Execuções e Check-in RPE de Treinos (/api/v1/routines/{id}/executions e /students/{id}/executions)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..exceptions import ApiErrorException, validate_uuid_param
from ..models import ExecutionModel, UserModel, WorkoutPlanModel, WorkoutRoutineModel
from ..schemas import CreateExecutionDTO, ExecutionResponse, UserRole
from ..security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Executions"])


@router.post(
    "/routines/{routineId}/executions",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar execução e feedback de treino (Check-in do Aluno com RPE 1-10)",
)
def create_execution(
    routineId: str,
    payload: CreateExecutionDTO,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ExecutionResponse:
    valid_routine_id = validate_uuid_param(routineId, param_name="routineId")
    routine = db.scalar(
        select(WorkoutRoutineModel).where(WorkoutRoutineModel.id == valid_routine_id)
    )
    if not routine:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rotina de treino com id '{valid_routine_id}' não foi encontrada.",
            instance=str(request.url.path),
        )

    plan = db.scalar(
        select(WorkoutPlanModel).where(WorkoutPlanModel.id == routine.workout_plan_id)
    )
    if (
        current_user.role == UserRole.STUDENT.value
        and plan is not None
        and plan.student_id != current_user.id
    ):
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Um aluno só pode registrar check-in em rotinas vinculadas ao seu próprio plano de treino.",
            instance=str(request.url.path),
        )

    new_exec = ExecutionModel(
        student_id=current_user.id,
        routine_id=routine.id,
        duration_minutes=payload.durationMinutes,
        rpe_score=payload.rpeScore,
        feedback=payload.feedback,
        completed_at=datetime.now(timezone.utc),
    )
    try:
        db.add(new_exec)
        db.commit()
        db.refresh(new_exec)
    except Exception:
        db.rollback()
        raise

    response.headers["Location"] = f"/api/v1/students/{current_user.id}/executions"
    return ExecutionResponse.model_validate(new_exec)


@router.get(
    "/students/{studentId}/executions",
    response_model=list[ExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar histórico de execuções de treino do aluno",
)
def list_student_executions(
    studentId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[ExecutionResponse]:
    valid_student_id = validate_uuid_param(studentId, param_name="studentId")
    student = db.scalar(select(UserModel).where(UserModel.id == valid_student_id))
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{valid_student_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if current_user.role == UserRole.STUDENT.value and current_user.id != student.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Um aluno só pode consultar o seu próprio histórico de execuções.",
            instance=str(request.url.path),
        )

    if (
        current_user.role == UserRole.PERSONAL.value
        and student.personal_id is not None
        and student.personal_id != current_user.id
    ):
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este aluno pertence à carteira de outro Personal Trainer.",
            instance=str(request.url.path),
        )

    executions = db.scalars(
        select(ExecutionModel)
        .where(ExecutionModel.student_id == valid_student_id)
        .order_by(ExecutionModel.completed_at.desc())
    ).all()
    return [ExecutionResponse.model_validate(ex) for ex in executions]
