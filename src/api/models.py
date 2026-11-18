"""Entidades ORM SQLAlchemy 2.0 da GymFlow API (Users, Profiles, Workouts, Routines, Exercises, Executions)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Classe base declarativa do SQLAlchemy 2.0."""


class UserModel(Base):
    """Tabela 'users' representando Personal Trainers e Alunos."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    personal_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="STUDENT")
    cref: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    profile: Mapped[Optional["StudentProfileModel"]] = relationship(
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def personalId(self) -> Optional[str]:
        return self.personal_id

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at


class StudentProfileModel(Base):
    """Tabela 'student_profiles' com dados biométricos e meta física do aluno (1:1 com UserModel)."""

    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    goal: Mapped[str] = mapped_column(String(30), nullable=False, default="HYPERTROPHY")
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    student: Mapped["UserModel"] = relationship(back_populates="profile")

    @property
    def birthDate(self) -> Optional[date]:
        return self.birth_date

    @property
    def weightKg(self) -> Optional[float]:
        return self.weight_kg

    @property
    def heightCm(self) -> Optional[float]:
        return self.height_cm


class WorkoutPlanModel(Base):
    """Tabela 'workout_plans' representando fichas de treino prescritas pelo Personal a um Aluno."""

    __tablename__ = "workout_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    personal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    routines: Mapped[list["WorkoutRoutineModel"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        order_by="WorkoutRoutineModel.order",
    )

    @property
    def personalId(self) -> str:
        return self.personal_id

    @property
    def studentId(self) -> str:
        return self.student_id

    @property
    def startDate(self) -> date:
        return self.start_date

    @property
    def endDate(self) -> Optional[date]:
        return self.end_date

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at


class WorkoutRoutineModel(Base):
    """Tabela 'workout_routines' representando divisões (Treino A, B, C) de um plano de treino (1:N)."""

    __tablename__ = "workout_routines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    workout_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    day_of_week: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    workout_plan: Mapped["WorkoutPlanModel"] = relationship(back_populates="routines")
    exercises: Mapped[list["WorkoutExerciseModel"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="WorkoutExerciseModel.order",
    )
    executions: Mapped[list["ExecutionModel"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
    )

    @property
    def workoutPlanId(self) -> str:
        return self.workout_plan_id

    @property
    def dayOfWeek(self) -> Optional[str]:
        return self.day_of_week


class WorkoutExerciseModel(Base):
    """Tabela 'workout_exercises' contendo os exercícios prescritos dentro de uma rotina (1:N)."""

    __tablename__ = "workout_exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    routine_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    muscle_group: Mapped[str] = mapped_column(String(30), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str] = mapped_column(String(20), nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    routine: Mapped["WorkoutRoutineModel"] = relationship(back_populates="exercises")

    @property
    def routineId(self) -> str:
        return self.routine_id

    @property
    def muscleGroup(self) -> str:
        return self.muscle_group

    @property
    def restSeconds(self) -> int:
        return self.rest_seconds

    @property
    def weightKg(self) -> Optional[float]:
        return self.weight_kg


class ExecutionModel(Base):
    """Tabela 'executions' para check-in de sessões concluídas pelo aluno com nota RPE (1 a 10)."""

    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    routine_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    rpe_score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    routine: Mapped["WorkoutRoutineModel"] = relationship(back_populates="executions")

    @property
    def studentId(self) -> str:
        return self.student_id

    @property
    def routineId(self) -> str:
        return self.routine_id

    @property
    def durationMinutes(self) -> int:
        return self.duration_minutes

    @property
    def rpeScore(self) -> int:
        return self.rpe_score

    @property
    def completedAt(self) -> datetime:
        return self.completed_at
