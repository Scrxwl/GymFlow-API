"""Exceções de domínio e handlers globais no padrão RFC 9457 (Problem Details) para a GymFlow API."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ApiError, InvalidParam

ERROR_TYPE_MAP: dict[int, tuple[str, str]] = {
    400: ("https://api.gymflow.dev/errors/bad-request", "Requisição Inválida"),
    401: ("https://api.gymflow.dev/errors/unauthorized", "Não Autenticado"),
    403: ("https://api.gymflow.dev/errors/forbidden", "Acesso Proibido"),
    404: ("https://api.gymflow.dev/errors/not-found", "Recurso Não Encontrado"),
    409: ("https://api.gymflow.dev/errors/conflict", "Conflito de Estado"),
    422: ("https://api.gymflow.dev/errors/validation-error", "Erro de Validação Semântica"),
}


class ApiErrorException(Exception):
    """Exceção semântica da GymFlow API formatada segundo a RFC 9457."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        title: Optional[str] = None,
        error_type: Optional[str] = None,
        instance: Optional[str] = None,
        invalid_params: Optional[list[InvalidParam]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(detail)
        default_type, default_title = ERROR_TYPE_MAP.get(
            status_code,
            ("https://api.gymflow.dev/errors/internal-error", "Erro Interno do Servidor"),
        )
        self.status_code = status_code
        self.detail = detail
        self.title = title or default_title
        self.error_type = error_type or default_type
        self.instance = instance
        self.invalid_params = invalid_params
        self.headers = headers


def create_problem_response(
    request: Request,
    status_code: int,
    detail: str,
    title: Optional[str] = None,
    error_type: Optional[str] = None,
    invalid_params: Optional[list[InvalidParam]] = None,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    """Constrói um JSONResponse compatível com o componente ApiError (RFC 9457)."""
    default_type, default_title = ERROR_TYPE_MAP.get(
        status_code,
        ("https://api.gymflow.dev/errors/internal-error", "Erro Interno do Servidor"),
    )
    resolved_params = invalid_params
    if status_code in (400, 422) and not resolved_params:
        resolved_params = [InvalidParam(name="request", reason=detail)]

    problem = ApiError(
        type=error_type or default_type,
        title=title or default_title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
        invalidParams=resolved_params,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(by_alias=True, exclude_none=True),
        headers=headers,
    )


def validate_uuid_param(value: str, param_name: str = "id") -> str:
    """Valida se um parâmetro de rota é um UUID válido; caso contrário, lança 400 RFC 9457."""
    try:
        UUID(str(value))
        return str(value)
    except (ValueError, TypeError) as exc:
        raise ApiErrorException(
            status_code=400,
            detail=f"O parâmetro '{param_name}' com valor '{value}' não é um UUID válido.",
            invalid_params=[
                InvalidParam(
                    name=param_name,
                    reason="Deve ser um identificador UUID v4 válido.",
                )
            ],
        ) from exc


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os exception handlers globais no padrão RFC 9457."""

    @app.exception_handler(ApiErrorException)
    async def handle_api_error_exception(
        request: Request, exc: ApiErrorException
    ) -> JSONResponse:
        return create_problem_response(
            request=request,
            status_code=exc.status_code,
            detail=exc.detail,
            title=exc.title,
            error_type=exc.error_type,
            invalid_params=exc.invalid_params,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        invalid_params: list[InvalidParam] = []
        is_bad_request = False

        for err in exc.errors():
            loc = err.get("loc", ())
            err_type = err.get("type", "")
            msg = err.get("msg", "Valor inválido.")

            if loc and loc[0] in ("query", "path", "header"):
                is_bad_request = True
            if err_type == "json_invalid":
                is_bad_request = True

            field_parts = [
                str(part) for part in loc if part not in ("body", "query", "path", "header")
            ]
            field_name = (
                ".".join(field_parts) if field_parts else (str(loc[-1]) if loc else "body")
            )
            invalid_params.append(InvalidParam(name=field_name, reason=msg))

        if is_bad_request:
            return create_problem_response(
                request=request,
                status_code=400,
                detail="Um ou mais parâmetros de consulta/rota são inválidos.",
                invalid_params=invalid_params,
            )

        return create_problem_response(
            request=request,
            status_code=422,
            detail="Um ou mais campos da requisição falharam na validação.",
            invalid_params=invalid_params,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return create_problem_response(
            request=request,
            status_code=exc.status_code,
            detail=str(exc.detail) if exc.detail else "Erro ao processar a requisição HTTP.",
            headers=dict(exc.headers) if exc.headers else None,
        )
