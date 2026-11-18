---
name: sdd-apidog-workflow
description: >-
  Guides the agent through the 4 phases of Spec-Driven Development (Constitution, Specify, Plan, Tasks & Implement)
  for GymFlow API using STYLEGUIDE.md, SPEC.md, PLAN.md, and GymFlow API.apidog.json with SQLAlchemy 2.0 ORM and JWT/RBAC.
---

# Spec-Driven Development (SDD) — GymFlow API Workflow

1. **Constitution (`STYLEGUIDE.md` & `AGENTS.md`)**: Enforce Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (`Mapped`, `relationship`, `selectinload`), Stateless JWT (`HS256`), RBAC (`PERSONAL` vs. `STUDENT`), and RFC 9457 (`ApiError`).
2. **Specification (`SPEC.md` & `GymFlow API.apidog.json`)**: Mirror all 26 Data Schemas and 18 endpoints from the Apidog contract.
3. **Plan (`PLAN.md`)**: Track all 6 implementation phases with `[x]` checkboxes.
4. **Verification (`pytest -v`)**: Validate all endpoints, ORM relationships, JWT tokens, RBAC rules, and RFC 9457 error responses in an isolated in-memory SQLite database.
