# STYLEGUIDE.md — Constituição Técnica (GymFlow API: ORM & Auth Edition)

## 1. Stack Tecnológica
- **Linguagem:** Python 3.12+ com tipagem estática.
- **Framework Web:** FastAPI + Pydantic v2 (`ConfigDict(populate_by_name=True, from_attributes=True)`).
- **Persistência:** SQLAlchemy 2.0 (`DeclarativeBase`, `Mapped`, `mapped_column`, `relationship`, `selectinload`) sobre SQLite (`sqlite:///./gymflow.db`).
- **Segurança:** Autenticação Stateless via JWT (`PyJWT`, `HS256`) e RBAC (`PERSONAL` e `STUDENT`).
- **Erros:** Conformidade estrita com a **RFC 9457 (Problem Details)** (`https://api.gymflow.dev/errors/...`).
- **Testes:** `pytest` + `TestClient` com banco SQLite em memória isolado por teste.
