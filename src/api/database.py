"""Engine SQLite, SessionLocal, get_db e seed idempotente da GymFlow API."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Generator
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Base,
    ExecutionModel,
    StudentProfileModel,
    UserModel,
    WorkoutExerciseModel,
    WorkoutPlanModel,
    WorkoutRoutineModel,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./gymflow.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SEED_PERSONAL_ID = "11111111-1111-1111-1111-111111111111"
SEED_STUDENT_ID = "22222222-2222-2222-2222-222222222222"
SEED_WORKOUT_ID = "33333333-3333-3333-3333-333333333333"
SEED_ROUTINE_ID = "44444444-4444-4444-4444-444444444444"
SEED_EXERCISE_ID = "55555555-5555-5555-5555-555555555555"
SEED_EXECUTION_ID = "66666666-6666-6666-6666-666666666666"


def _default_hash_password(password: str) -> str:
    try:
        from .security import hash_password

        return hash_password(password)
    except ImportError:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"pbkdf2_sha256${salt}${dk.hex()}"


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão SQLAlchemy isolada por requisição HTTP."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db_and_seed(db: Session, target_engine: Engine | None = None) -> None:
    """Cria as tabelas da GymFlow API e insere de forma idempotente os dados de exemplo do Apidog."""
    bind_engine = target_engine or db.get_bind()
    Base.metadata.create_all(bind=bind_engine)

    now = datetime(2026, 2, 10, 9, 0, 0, tzinfo=timezone.utc)

    # 1. Personal Trainer (role="PERSONAL")
    personal = db.scalar(select(UserModel).where(UserModel.id == SEED_PERSONAL_ID))
    if not personal:
        db.add(
            UserModel(
                id=SEED_PERSONAL_ID,
                name="Carlos Personal",
                email="carlos@gymflow.dev",
                password_hash=_default_hash_password("Personal@2026"),
                role="PERSONAL",
                cref="123456-G/SP",
                phone="+5511999990001",
                created_at=now,
                updated_at=now,
            )
        )

    # 2. Aluno (role="STUDENT") + StudentProfileModel
    student = db.scalar(select(UserModel).where(UserModel.id == SEED_STUDENT_ID))
    if not student:
        student_user = UserModel(
            id=SEED_STUDENT_ID,
            personal_id=SEED_PERSONAL_ID,
            name="Rodrigo Aluno",
            email="rodrigo@gymflow.dev",
            password_hash=_default_hash_password("Aluno@2026"),
            role="STUDENT",
            phone="+5511999990002",
            created_at=now,
            updated_at=now,
        )
        db.add(student_user)
        db.flush()

    student_profile = db.scalar(
        select(StudentProfileModel).where(StudentProfileModel.student_id == SEED_STUDENT_ID)
    )
    if not student_profile:
        db.add(
            StudentProfileModel(
                student_id=SEED_STUDENT_ID,
                birth_date=date(1998, 5, 15),
                weight_kg=78.5,
                height_cm=178.0,
                goal="HYPERTROPHY",
                notes="Foco em hipertrofia e fortalecimento do manguito rotador.",
            )
        )

    db.flush()

    # 3. Plano de Treino + Rotina A + Exercício + Execução
    workout = db.scalar(select(WorkoutPlanModel).where(WorkoutPlanModel.id == SEED_WORKOUT_ID))
    if not workout:
        plan = WorkoutPlanModel(
            id=SEED_WORKOUT_ID,
            personal_id=SEED_PERSONAL_ID,
            student_id=SEED_STUDENT_ID,
            title="Mesociclo 01 — Hipertrofia Base ABC",
            description="Progressão linear de carga a cada 2 semanas mantendo RPE entre 7 e 8.",
            status="ACTIVE",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 5, 1),
            created_at=now,
            updated_at=now,
        )
        db.add(plan)
        db.flush()

        routine = WorkoutRoutineModel(
            id=SEED_ROUTINE_ID,
            workout_plan_id=SEED_WORKOUT_ID,
            name="Treino A — Peito, Ombros e Tríceps",
            day_of_week="MONDAY",
            order=1,
        )
        db.add(routine)
        db.flush()

        exercise = WorkoutExerciseModel(
            id=SEED_EXERCISE_ID,
            routine_id=SEED_ROUTINE_ID,
            name="Supino Reto com Barra",
            muscle_group="CHEST",
            sets=4,
            reps="8-12",
            rest_seconds=90,
            weight_kg=60.0,
            notes="Cadência 3010, escápulas retraídas.",
            order=1,
        )
        db.add(exercise)

        execution = ExecutionModel(
            id=SEED_EXECUTION_ID,
            student_id=SEED_STUDENT_ID,
            routine_id=SEED_ROUTINE_ID,
            duration_minutes=55,
            rpe_score=8,
            feedback="Ótimo rendimento no supino, consegui progredir 2kg de cada lado.",
            completed_at=now,
        )
        db.add(execution)

    db.commit()
