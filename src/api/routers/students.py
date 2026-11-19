"""Endpoints de gestão de alunos (/api/v1/students) com eager loading selectinload e controle RBAC."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..exceptions import ApiErrorException, validate_uuid_param
from ..models import ExecutionModel, StudentProfileModel, UserModel, WorkoutPlanModel
from ..schemas import (
    CreateStudentDTO,
    FitnessGoal,
    PaginatedStudentsResponse,
    PaginationMeta,
    StudentAnalyticsResponse,
    StudentResponse,
    UpdateStudentDTO,
    UserRole,
)
from ..security import get_current_user, hash_password, require_roles

router = APIRouter(prefix="/api/v1/students", tags=["Students"])


@router.get(
    "",
    response_model=PaginatedStudentsResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar alunos com paginação e filtros (Restrito a PERSONAL)",
)
def list_students(
    page: int = Query(default=1, ge=1, description="Número da página desejada."),
    limit: int = Query(default=10, ge=1, le=100, description="Número máximo de registros por página."),
    search: Optional[str] = Query(default=None, description="Filtro parcial por nome ou e-mail."),
    goal: Optional[FitnessGoal] = Query(default=None, description="Filtro por objetivo físico."),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> PaginatedStudentsResponse:
    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.role == UserRole.STUDENT.value)
        .where(
            or_(
                UserModel.personal_id == current_user.id,
                UserModel.personal_id.is_(None),
            )
        )
    )

    if search is not None and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(UserModel.name).contains(term),
                func.lower(UserModel.email).contains(term),
            )
        )

    if goal is not None:
        stmt = stmt.join(StudentProfileModel, StudentProfileModel.student_id == UserModel.id).where(
            StudentProfileModel.goal == goal.value
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_items = db.scalar(count_stmt) or 0
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    has_next = page < total_pages

    offset = (page - 1) * limit
    records = db.scalars(
        stmt.order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
    ).all()

    return PaginatedStudentsResponse(
        data=[StudentResponse.model_validate(s) for s in records],
        meta=PaginationMeta(
            page=page,
            limit=limit,
            totalItems=total_items,
            totalPages=total_pages,
            hasNext=has_next,
        ),
    )


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo aluno na carteira do Personal (Restrito a PERSONAL)",
)
def create_student(
    payload: CreateStudentDTO,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> StudentResponse:
    existing = db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == payload.email.lower())
    )
    if existing:
        raise ApiErrorException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário com o e-mail '{payload.email}'.",
            instance=str(request.url.path),
        )

    now = datetime.now(timezone.utc)
    new_student = UserModel(
        personal_id=current_user.id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT.value,
        phone=payload.phone,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_student)
        db.flush()

        if payload.profile is not None:
            prof = StudentProfileModel(
                student_id=new_student.id,
                birth_date=payload.profile.birthDate,
                weight_kg=payload.profile.weightKg,
                height_cm=payload.profile.heightCm,
                goal=payload.profile.goal.value,
                notes=payload.profile.notes,
            )
            db.add(prof)

        db.commit()
    except Exception:
        db.rollback()
        raise

    loaded = db.scalar(
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == new_student.id)
    )
    response.headers["Location"] = f"/api/v1/students/{new_student.id}"
    return StudentResponse.model_validate(loaded)


@router.get(
    "/{studentId}",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter detalhes de um aluno por ID",
)
def get_student_by_id(
    studentId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    valid_id = validate_uuid_param(studentId, param_name="studentId")
    student = db.scalar(
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == valid_id, UserModel.role == UserRole.STUDENT.value)
    )
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if current_user.role == UserRole.STUDENT.value and current_user.id != student.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Um aluno só pode consultar o seu próprio perfil.",
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

    return StudentResponse.model_validate(student)


@router.patch(
    "/{studentId}",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar cadastro e perfil físico do aluno (Restrito a PERSONAL)",
)
def update_student(
    studentId: str,
    payload: UpdateStudentDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> StudentResponse:
    valid_id = validate_uuid_param(studentId, param_name="studentId")
    student = db.scalar(
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == valid_id, UserModel.role == UserRole.STUDENT.value)
    )
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if student.personal_id is not None and student.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este aluno pertence à carteira de outro Personal Trainer.",
            instance=str(request.url.path),
        )

    if payload.name is not None:
        student.name = payload.name
    if payload.phone is not None:
        student.phone = payload.phone

    if payload.profile is not None:
        if student.profile is None:
            student.profile = StudentProfileModel(
                student_id=student.id,
                birth_date=payload.profile.birthDate,
                weight_kg=payload.profile.weightKg,
                height_cm=payload.profile.heightCm,
                goal=payload.profile.goal.value,
                notes=payload.profile.notes,
            )
        else:
            if payload.profile.birthDate is not None:
                student.profile.birth_date = payload.profile.birthDate
            if payload.profile.weightKg is not None:
                student.profile.weight_kg = payload.profile.weightKg
            if payload.profile.heightCm is not None:
                student.profile.height_cm = payload.profile.heightCm
            if payload.profile.goal is not None:
                student.profile.goal = payload.profile.goal.value
            if payload.profile.notes is not None:
                student.profile.notes = payload.profile.notes

    student.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(student)
    except Exception:
        db.rollback()
        raise

    return StudentResponse.model_validate(student)


@router.delete(
    "/{studentId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover aluno da carteira do Personal (Exclusivo PERSONAL)",
)
def delete_student(
    studentId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.PERSONAL)),
) -> Response:
    valid_id = validate_uuid_param(studentId, param_name="studentId")
    student = db.scalar(
        select(UserModel).where(
            UserModel.id == valid_id, UserModel.role == UserRole.STUDENT.value
        )
    )
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if student.personal_id is not None and student.personal_id != current_user.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este aluno pertence à carteira de outro Personal Trainer.",
            instance=str(request.url.path),
        )

    try:
        db.delete(student)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{studentId}/analytics",
    response_model=StudentAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="[Conteúdo Extra] Obter indicadores biométricos (IMC) e estatísticas RPE do aluno",
)
def get_student_analytics(
    studentId: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentAnalyticsResponse:
    """Calcula IMC (BMI), classificação biométrica e métricas consolidadas de treino e esforço RPE."""
    valid_id = validate_uuid_param(studentId, param_name="studentId")
    student = db.scalar(
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == valid_id, UserModel.role == UserRole.STUDENT.value)
    )
    if not student:
        raise ApiErrorException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com id '{valid_id}' não foi encontrado.",
            instance=str(request.url.path),
        )

    if current_user.role == UserRole.STUDENT.value and current_user.id != student.id:
        raise ApiErrorException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Um aluno só pode consultar seus próprios indicadores.",
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

    weight = student.profile.weight_kg if student.profile else None
    height = student.profile.height_cm if student.profile else None
    goal = student.profile.goal if student.profile else None

    bmi: Optional[float] = None
    bmi_class: Optional[str] = None
    if weight and height and height > 0:
        height_m = height / 100.0
        bmi = round(weight / (height_m * height_m), 2)
        if bmi < 18.5:
            bmi_class = "Abaixo do peso"
        elif bmi < 25.0:
            bmi_class = "Peso normal (Eutrófico)"
        elif bmi < 30.0:
            bmi_class = "Sobrepeso"
        else:
            bmi_class = "Obesidade"

    active_plans = (
        db.scalar(
            select(func.count()).where(
                WorkoutPlanModel.student_id == valid_id,
                WorkoutPlanModel.status == "ACTIVE",
            )
        )
        or 0
    )

    executions = db.scalars(
        select(ExecutionModel).where(ExecutionModel.student_id == valid_id)
    ).all()
    total_execs = len(executions)
    total_duration = sum(e.duration_minutes for e in executions)
    avg_rpe = (
        round(sum(e.rpe_score for e in executions) / total_execs, 2)
        if total_execs > 0
        else 0.0
    )

    return StudentAnalyticsResponse(
        studentId=student.id,
        studentName=student.name,
        goal=goal,
        weightKg=weight,
        heightCm=height,
        bmi=bmi,
        bmiClassification=bmi_class,
        activeWorkoutPlans=active_plans,
        totalExecutions=total_execs,
        totalDurationMinutes=total_duration,
        averageRpeScore=avg_rpe,
    )
