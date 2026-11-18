"""Contratos Pydantic v2 espelhando todos os 26 Data Schemas da GymFlow API no Apidog."""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ============================================================================
# 1. Enums de Domínio e Segurança
# ============================================================================


class UserRole(str, Enum):
    """Papel de acesso do usuário no sistema GymFlow."""

    PERSONAL = "PERSONAL"
    STUDENT = "STUDENT"


class FitnessGoal(str, Enum):
    """Objetivo físico principal do aluno."""

    HYPERTROPHY = "HYPERTROPHY"
    WEIGHT_LOSS = "WEIGHT_LOSS"
    CONDITIONING = "CONDITIONING"
    REHABILITATION = "REHABILITATION"
    GENERAL_FITNESS = "GENERAL_FITNESS"


class MuscleGroup(str, Enum):
    """Grupo muscular alvo do exercício."""

    CHEST = "CHEST"
    BACK = "BACK"
    LEGS = "LEGS"
    SHOULDERS = "SHOULDERS"
    BICEPS = "BICEPS"
    TRICEPS = "TRICEPS"
    CORE = "CORE"
    CARDIO = "CARDIO"


class WorkoutStatus(str, Enum):
    """Status do ciclo de vida do plano de treino."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


# ============================================================================
# 2. Schemas de Erro (RFC 9457) e Paginação
# ============================================================================


class InvalidParam(BaseModel):
    """Item individual com erro de validação semântica."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Caminho ou nome do campo que falhou na validação.")
    reason: str = Field(..., description="Explicação técnica da restrição violada.")


class ApiError(BaseModel):
    """Formato padronizado de resposta de erro segundo a RFC 9457 (Problem Details)."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., description="URI absoluta identificando o tipo de erro.")
    title: str = Field(..., description="Resumo legível para humanos da categoria do erro.")
    status: int = Field(..., description="Código de status HTTP correspondente.")
    detail: str = Field(..., description="Mensagem detalhada e contextualizada da ocorrência do erro.")
    instance: str = Field(..., description="URI do endpoint onde ocorreu a falha.")
    invalidParams: Optional[list[InvalidParam]] = Field(
        default=None,
        description="Lista de parâmetros ou campos inválidos (preenchido em erros 400 ou 422).",
    )


class PaginationMeta(BaseModel):
    """Envelope de metadados para listagens paginadas."""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(..., ge=1, description="Número da página atual (inicia em 1).")
    limit: int = Field(..., ge=1, le=100, description="Quantidade máxima de registros por página.")
    totalItems: int = Field(..., ge=0, description="Total absoluto de itens encontrados.")
    totalPages: int = Field(..., ge=0, description="Total de páginas disponíveis.")
    hasNext: bool = Field(..., description="Booleano indicando se há uma página posterior.")


# ============================================================================
# 3. Schemas de Autenticação (RegisterUserDTO, LoginRequestDTO, UserResponse, AuthTokenResponse)
# ============================================================================


class RegisterUserDTO(BaseModel):
    """Payload para registro inicial de Personal Trainer ou Aluno."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=3, max_length=100, description="Nome completo do usuário.")
    email: str = Field(..., description="E-mail de acesso do usuário.")
    password: str = Field(..., min_length=6, max_length=64, description="Senha de acesso.")
    role: UserRole = Field(..., description="Papel do usuário (PERSONAL ou STUDENT).")
    cref: Optional[str] = Field(
        default=None,
        description="Registro no CREF (obrigatório quando role=PERSONAL).",
    )
    phone: Optional[str] = Field(default=None, description="Telefone de contato opcional.")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Formato de e-mail inválido.")
        return cleaned

    @model_validator(mode="after")
    def validate_cref_for_personal(self) -> "RegisterUserDTO":
        if self.role == UserRole.PERSONAL and (not self.cref or not self.cref.strip()):
            raise ValueError("O campo 'cref' é obrigatório para usuários com papel PERSONAL.")
        return self


class LoginRequestDTO(BaseModel):
    """Credenciais de autenticação para emissão de token JWT."""

    model_config = ConfigDict(populate_by_name=True)

    email: str = Field(..., description="E-mail do usuário.")
    password: str = Field(..., min_length=6, description="Senha do usuário.")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Formato de e-mail inválido.")
        return cleaned


class UserResponse(BaseModel):
    """Dados públicos do usuário autenticado."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(..., description="UUID do usuário.")
    name: str = Field(..., description="Nome completo do usuário.")
    email: str = Field(..., description="E-mail do usuário.")
    role: UserRole = Field(..., description="Papel de acesso (PERSONAL ou STUDENT).")
    cref: Optional[str] = Field(default=None, description="Registro CREF (se PERSONAL).")
    phone: Optional[str] = Field(default=None, description="Telefone de contato.")
    createdAt: datetime = Field(..., description="Data e hora de criação do registro.")


class AuthTokenResponse(BaseModel):
    """Envelope de resposta contendo o token JWT Bearer e dados do usuário."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    accessToken: str = Field(..., description="Token JWT assinado com HS256.")
    tokenType: str = Field(default="bearer", description="Tipo do token.")
    expiresIn: int = Field(default=3600, description="Tempo de expiração em segundos.")
    user: UserResponse = Field(..., description="Perfil do usuário autenticado.")


# ============================================================================
# 4. Schemas de Alunos (Students)
# ============================================================================


class StudentProfileDTO(BaseModel):
    """Dados biométricos e objetivos físicos do aluno."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    birthDate: Optional[date] = Field(
        default=None, description="Data de nascimento no formato ISO 8601 (AAAA-MM-DD)."
    )
    weightKg: Optional[float] = Field(
        default=None, ge=20, le=300, description="Peso corporal atual em quilogramas (kg)."
    )
    heightCm: Optional[float] = Field(
        default=None, ge=100, le=250, description="Estatura do aluno em centímetros (cm)."
    )
    goal: FitnessGoal = Field(
        default=FitnessGoal.HYPERTROPHY, description="Objetivo físico principal do aluno."
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Observações clínicas ou biomecânicas."
    )


class CreateStudentDTO(BaseModel):
    """Payload de entrada para cadastro de um novo aluno na carteira do Personal."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=3, max_length=100, description="Nome completo do aluno.")
    email: str = Field(..., description="E-mail de acesso do aluno.")
    password: str = Field(
        default="Aluno@2026", min_length=6, max_length=64, description="Senha inicial do aluno."
    )
    phone: Optional[str] = Field(default=None, description="Telefone de contato.")
    profile: Optional[StudentProfileDTO] = Field(
        default=None, description="Perfil biométrico e objetivo físico do aluno."
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Formato de e-mail inválido.")
        return cleaned


class UpdateStudentDTO(BaseModel):
    """Payload para atualização parcial de cadastro e perfil físico do aluno."""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    phone: Optional[str] = Field(default=None)
    profile: Optional[StudentProfileDTO] = Field(default=None)


class StudentResponse(BaseModel):
    """Representação completa de um aluno cadastrado."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(..., description="Identificador único global do aluno.")
    personalId: Optional[str] = Field(
        default=None, description="Identificador do Personal Trainer responsável."
    )
    name: str = Field(..., description="Nome completo do aluno.")
    email: str = Field(..., description="E-mail de acesso do aluno.")
    role: UserRole = Field(..., description="Papel do usuário.")
    phone: Optional[str] = Field(default=None, description="Telefone de contato.")
    profile: Optional[StudentProfileDTO] = Field(default=None, description="Perfil biométrico.")
    createdAt: datetime = Field(..., description="Data e hora de criação do registro.")
    updatedAt: datetime = Field(..., description="Data e hora da última modificação.")


class PaginatedStudentsResponse(BaseModel):
    """Resposta paginada contendo a listagem de alunos."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[StudentResponse]
    meta: PaginationMeta


class StudentAnalyticsResponse(BaseModel):
    """[Conteúdo Extra P2] Indicadores biométricos (IMC) e métricas de engajamento/RPE do aluno."""

    model_config = ConfigDict(populate_by_name=True)

    studentId: str
    studentName: str
    goal: Optional[str] = None
    weightKg: Optional[float] = None
    heightCm: Optional[float] = None
    bmi: Optional[float] = Field(default=None, description="Índice de Massa Corporal (IMC)")
    bmiClassification: Optional[str] = Field(
        default=None, description="Classificação OMS do IMC"
    )
    activeWorkoutPlans: int = Field(..., description="Total de fichas de treino ativas")
    totalExecutions: int = Field(..., description="Total de check-ins de treino realizados")
    totalDurationMinutes: int = Field(..., description="Soma de minutos treinados")
    averageRpeScore: float = Field(..., description="Média da escala RPE Borg (1 a 10)")


# ============================================================================
# 5. Schemas de Planos de Treino, Rotinas e Exercícios (Workouts)
# ============================================================================


class WorkoutExerciseDTO(BaseModel):
    """Dados de prescrição técnica de um exercício dentro de uma rotina."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=3, max_length=100, description="Nome do exercício.")
    muscleGroup: MuscleGroup = Field(..., description="Grupo muscular alvo.")
    sets: int = Field(..., ge=1, le=20, description="Quantidade de séries.")
    reps: str = Field(..., min_length=1, max_length=20, description="Faixa de repetições.")
    restSeconds: int = Field(..., ge=0, le=600, description="Tempo de descanso em segundos.")
    weightKg: Optional[float] = Field(
        default=None, ge=0, le=500, description="Carga sugerida em kg."
    )
    notes: Optional[str] = Field(
        default=None, max_length=300, description="Observações de execução."
    )
    order: int = Field(default=1, ge=1, description="Ordem do exercício na rotina.")


class WorkoutExerciseResponse(BaseModel):
    """Representação completa de um exercício prescrito."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    routineId: str
    name: str
    muscleGroup: MuscleGroup
    sets: int
    reps: str
    restSeconds: int
    weightKg: Optional[float] = None
    notes: Optional[str] = None
    order: int


class WorkoutRoutineDTO(BaseModel):
    """Divisão de treino (ex: Treino A - Superiores) com seus respectivos exercícios."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=80, description="Nome da divisão de treino.")
    dayOfWeek: Optional[str] = Field(default=None, description="Dia da semana sugerido.")
    order: int = Field(default=1, ge=1, description="Ordem da rotina no plano.")
    exercises: list[WorkoutExerciseDTO] = Field(
        default_factory=list, description="Exercícios prescritos na rotina."
    )


class WorkoutRoutineResponse(BaseModel):
    """Representação de uma divisão de rotina persistida com seus exercícios."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    workoutPlanId: str
    name: str
    dayOfWeek: Optional[str] = None
    order: int
    exercises: list[WorkoutExerciseResponse] = Field(default_factory=list)


class CreateWorkoutPlanDTO(BaseModel):
    """Payload para criação de um plano de treino periodizado vinculado a um aluno."""

    model_config = ConfigDict(populate_by_name=True)

    studentId: str = Field(..., description="UUID do aluno destinatário da ficha.")
    title: str = Field(..., min_length=3, max_length=120, description="Título do plano de treino.")
    description: Optional[str] = Field(default=None, max_length=500)
    status: WorkoutStatus = Field(default=WorkoutStatus.ACTIVE)
    startDate: date = Field(..., description="Data de início da vigência.")
    endDate: Optional[date] = Field(default=None, description="Data prevista de término.")
    routines: list[WorkoutRoutineDTO] = Field(default_factory=list)

    @field_validator("studentId")
    @classmethod
    def validate_student_uuid(cls, value: str) -> str:
        try:
            UUID(str(value))
            return str(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("O campo studentId deve ser um UUID válido.") from exc


class UpdateWorkoutPlanDTO(BaseModel):
    """Payload para atualização parcial dos metadados do plano de treino."""

    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(default=None, min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    status: Optional[WorkoutStatus] = Field(default=None)
    startDate: Optional[date] = Field(default=None)
    endDate: Optional[date] = Field(default=None)


class WorkoutPlanResponse(BaseModel):
    """Representação completa de um plano de treino com rotinas e exercícios aninhados."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    personalId: str
    studentId: str
    title: str
    description: Optional[str] = None
    status: WorkoutStatus
    startDate: date
    endDate: Optional[date] = None
    routines: list[WorkoutRoutineResponse] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime


class PaginatedWorkoutsResponse(BaseModel):
    """Envelope paginado de planos de treino."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[WorkoutPlanResponse]
    meta: PaginationMeta


# ============================================================================
# 6. Schemas de Execuções e Feedback RPE (Executions)
# ============================================================================


class CreateExecutionDTO(BaseModel):
    """Payload de check-in de sessão de treino finalizada pelo aluno."""

    model_config = ConfigDict(populate_by_name=True)

    durationMinutes: int = Field(
        ..., ge=5, le=300, description="Duração total do treino em minutos."
    )
    rpeScore: int = Field(
        ..., ge=1, le=10, description="Percepção Subjetiva de Esforço (Escala RPE Borg 1 a 10)."
    )
    feedback: Optional[str] = Field(
        default=None, max_length=500, description="Feedback qualitativo do aluno."
    )


class ExecutionResponse(BaseModel):
    """Registro persistido de execução de treino."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    studentId: str
    routineId: str
    durationMinutes: int
    rpeScore: int
    feedback: Optional[str] = None
    completedAt: datetime
