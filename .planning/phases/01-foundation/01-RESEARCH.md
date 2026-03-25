# Phase 1: Foundation - Research

**Researched:** 2026-03-24
**Domain:** FastAPI + SQLAlchemy + SQLite, CRUD API, Pydantic validation
**Confidence:** HIGH

## Summary

Phase 1 establishes the project skeleton: a FastAPI application with SQLite persistence via SQLAlchemy, exposing a REST API for managing Route Groups (Grupos de Rota). The stack is well-documented and mature. The key technical decisions are: (1) use synchronous SQLAlchemy with SQLite (async adds complexity without benefit for a single-user tool), (2) use `SQLAlchemy.JSON` column type to store lists of IATA codes natively, (3) use Pydantic v2 `@field_validator` for IATA code validation with a simple 3-uppercase-letter regex, and (4) use FastAPI's lifespan context manager for auto-creating tables on startup.

The "max 10 active groups" constraint should be enforced at the application level (service layer check before insert/update) rather than a database trigger, since SQLite triggers are harder to test and the constraint involves counting rows rather than a simple column check. This keeps the logic visible, testable, and aligned with the TDD methodology required by CLAUDE.md.

**Primary recommendation:** Use synchronous SQLAlchemy 2.0 with mapped_column style, Pydantic v2 schemas with field validators, and FastAPI dependency injection for session management. Keep the project in a small modular structure (not single-file, but not over-engineered).

## Project Constraints (from CLAUDE.md)

- Spec-Driven Development + TDD (Red-Green-Refactor) is mandatory
- Tests MUST be written BEFORE implementation code
- Tests must follow AAA / Given-When-Then pattern
- Coverage must include: happy path, edge cases, expected errors, integration
- Tests must follow FIRST principles (Fast, Independent, Repeatable, Self-validating, Timely)
- Implementation must be the MINIMUM necessary to pass tests (YAGNI strict)
- Refactoring checklist must be executed after GREEN phase
- No emojis in responses
- No " -- " in responses
- Communication in pt-BR

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Aplicacao inicia com um unico comando (python main.py ou uvicorn app.main:app) | FastAPI + uvicorn; lifespan event for setup |
| INFRA-02 | Configuracao via .env (Amadeus keys, Telegram bot token, chat ID) | python-dotenv + Pydantic BaseSettings |
| INFRA-03 | Banco SQLite criado automaticamente na primeira execucao com todas as tabelas | SQLAlchemy create_all in lifespan startup |
| ROUTE-01 | Criar Grupo de Rota com nome, origens, destinos, duracao, periodo | POST endpoint + Pydantic schema + SQLAlchemy model with JSON columns |
| ROUTE-02 | Preco-alvo opcional por Grupo de Rota | Optional float field in model and schema |
| ROUTE-03 | Ativar e desativar Grupo de Rota sem deletar | PATCH endpoint toggling is_active boolean |
| ROUTE-04 | Editar Grupo de Rota existente | PATCH/PUT endpoint with partial update schema |
| ROUTE-05 | Deletar Grupo de Rota | DELETE endpoint |
| ROUTE-06 | Limitar a 10 grupos ativos simultaneamente | Application-level count check before activate/create |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.2 | Web framework / API | De facto Python async web framework; built-in OpenAPI docs, dependency injection |
| uvicorn | 0.42.0 | ASGI server | Standard server for FastAPI; production-grade |
| sqlalchemy | 2.0.48 | ORM / database | Industry standard Python ORM; 2.0 style with type annotations |
| pydantic | 2.12.5 | Data validation / schemas | Ships with FastAPI; v2 has better performance and validators |
| python-dotenv | 1.2.2 | Environment variable loading | Simple .env file loading; works with Pydantic BaseSettings |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | 2.13.1 | Settings management from .env | Loading and validating configuration from environment |
| pytest | 9.0.2 | Test framework | All testing (TDD methodology requires it from the start) |
| httpx | 0.28.1 | HTTP client for testing | FastAPI TestClient is built on httpx |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy sync | SQLAlchemy async (aiosqlite) | Async adds complexity; SQLite is inherently sync; single-user app has no concurrency need |
| SQLAlchemy create_all | Alembic migrations | Alembic is overkill for v1 of a personal tool; create_all is sufficient; can add Alembic later |
| SQLModel | Plain SQLAlchemy + Pydantic | SQLModel merges ORM + validation but has fewer features and less documentation than using them separately |

**Installation:**
```bash
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-dotenv pytest httpx
```

**Version verification:** All versions verified against PyPI on 2026-03-24.

## Architecture Patterns

### Recommended Project Structure
```
flight-monitor/
  .env                    # credentials (gitignored)
  .env.example            # template without secrets (committed)
  main.py                 # entry point: uvicorn launch
  app/
    __init__.py
    config.py             # Pydantic BaseSettings loading .env
    database.py           # engine, SessionLocal, Base, get_db dependency
    models.py             # SQLAlchemy ORM models
    schemas.py            # Pydantic request/response schemas
    routes/
      __init__.py
      route_groups.py     # CRUD endpoints for route groups
    services/
      __init__.py
      route_group_service.py  # business logic (max 10 check, validation)
  tests/
    __init__.py
    conftest.py           # fixtures: test db, test client, session override
    test_route_groups.py  # API-level tests for all ROUTE-* requirements
    test_models.py        # model-level tests (optional, for complex logic)
```

This structure separates concerns without over-engineering. For a personal project of this scale, a single `models.py` and `schemas.py` is sufficient. The `services/` layer is important because it holds the business rules (like the max-10-active constraint) in a testable location separate from the HTTP layer.

### Pattern 1: Synchronous SQLAlchemy Session with FastAPI Dependency Injection
**What:** Create a session factory, yield sessions via a dependency, and inject into route handlers.
**When to use:** Every route that touches the database.
**Example:**
```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Pattern 2: Pydantic BaseSettings for Configuration
**What:** Load .env variables with type validation into a settings object.
**When to use:** Application configuration (API keys, database path, etc).
**Example:**
```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./flight_monitor.db"
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

### Pattern 3: SQLAlchemy Model with JSON Columns for Lists
**What:** Store lists of IATA codes as JSON in SQLite using SQLAlchemy JSON type.
**When to use:** RouteGroup model for origins and destinations fields.
**Example:**
```python
# app/models.py
from sqlalchemy import JSON, String, Integer, Float, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import datetime

class RouteGroup(Base):
    __tablename__ = "route_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    origins: Mapped[list] = mapped_column(JSON)       # ["GRU", "CGH"]
    destinations: Mapped[list] = mapped_column(JSON)   # ["LIS", "OPO"]
    duration_days: Mapped[int] = mapped_column(Integer)
    travel_start: Mapped[datetime.date] = mapped_column(Date)
    travel_end: Mapped[datetime.date] = mapped_column(Date)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

### Pattern 4: Pydantic Schemas with IATA Validation
**What:** Separate Create/Update/Response schemas with field validators for IATA codes.
**When to use:** All API request/response handling.
**Example:**
```python
# app/schemas.py
import datetime
import re
from pydantic import BaseModel, field_validator

IATA_PATTERN = re.compile(r"^[A-Z]{3}$")

class RouteGroupCreate(BaseModel):
    name: str
    origins: list[str]
    destinations: list[str]
    duration_days: int
    travel_start: datetime.date
    travel_end: datetime.date
    target_price: float | None = None

    @field_validator("origins", "destinations")
    @classmethod
    def validate_iata_codes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one IATA code is required")
        for code in v:
            if not IATA_PATTERN.match(code):
                raise ValueError(f"Invalid IATA code: {code}. Must be 3 uppercase letters.")
        return v

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Duration must be at least 1 day")
        return v

class RouteGroupUpdate(BaseModel):
    name: str | None = None
    origins: list[str] | None = None
    destinations: list[str] | None = None
    duration_days: int | None = None
    travel_start: datetime.date | None = None
    travel_end: datetime.date | None = None
    target_price: float | None = None
    is_active: bool | None = None

    @field_validator("origins", "destinations")
    @classmethod
    def validate_iata_codes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("At least one IATA code is required")
        for code in v:
            if not IATA_PATTERN.match(code):
                raise ValueError(f"Invalid IATA code: {code}")
        return v

class RouteGroupResponse(BaseModel):
    id: int
    name: str
    origins: list[str]
    destinations: list[str]
    duration_days: int
    travel_start: datetime.date
    travel_end: datetime.date
    target_price: float | None
    is_active: bool

    model_config = {"from_attributes": True}
```

### Pattern 5: Lifespan Event for Table Creation
**What:** Use FastAPI lifespan context manager to create tables on startup.
**When to use:** Application initialization.
**Example:**
```python
# main.py
import sys
sys.stdout.reconfigure(encoding="utf-8")  # Windows UTF-8 fix

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Flight Monitor", lifespan=lifespan)

# Import and include routers
from app.routes.route_groups import router as route_groups_router
app.include_router(route_groups_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

### Pattern 6: Max 10 Active Groups Constraint (Service Layer)
**What:** Check count of active groups before allowing creation or activation.
**When to use:** Before any operation that would increase active group count.
**Example:**
```python
# app/services/route_group_service.py
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import RouteGroup

MAX_ACTIVE_GROUPS = 10

def check_active_group_limit(db: Session, exclude_id: int | None = None) -> None:
    query = select(func.count()).select_from(RouteGroup).where(RouteGroup.is_active == True)
    if exclude_id is not None:
        query = query.where(RouteGroup.id != exclude_id)
    count = db.scalar(query)
    if count >= MAX_ACTIVE_GROUPS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum of {MAX_ACTIVE_GROUPS} active route groups reached."
        )
```

### Anti-Patterns to Avoid
- **Single-file monolith:** Even for a small project, separating models/schemas/routes/services prevents confusion as the project grows through 5 phases.
- **Async SQLAlchemy with SQLite:** Adds aiosqlite dependency and complexity for zero benefit in a single-user local tool.
- **Database-level triggers for business rules:** SQLite triggers are harder to test and debug; keep constraints in the service layer.
- **Hardcoding IATA airport list:** A full IATA database is 10,000+ codes and changes regularly. A regex (3 uppercase letters) is sufficient for v1; the Amadeus API will reject truly invalid codes at query time.
- **Alembic for v1:** Auto-create with create_all is the right choice for initial development. Add Alembic when schema evolution becomes a real need.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env loading | Custom file parser | python-dotenv + pydantic-settings | Handles encoding, defaults, type coercion |
| JSON serialization in SQLite | Custom TEXT + json.loads/dumps | SQLAlchemy JSON type | Automatic serialization/deserialization, transparent to ORM |
| Request validation | Manual if/else checks | Pydantic v2 schemas | Automatic HTTP 422 responses, type coercion, nested validation |
| Test HTTP client | Manual requests to running server | FastAPI TestClient | In-process, no server needed, same session override |
| API documentation | Swagger/OpenAPI manual files | FastAPI auto-generated /docs | Automatic from type annotations and schemas |

**Key insight:** FastAPI + Pydantic + SQLAlchemy 2.0 together form a tightly integrated stack where type annotations flow from schema validation through ORM to database. Fighting this integration by hand-rolling any piece creates friction in every other piece.

## Common Pitfalls

### Pitfall 1: SQLite check_same_thread
**What goes wrong:** SQLite raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread` when FastAPI handles concurrent requests.
**Why it happens:** SQLite defaults to single-thread mode; FastAPI uses a thread pool for sync endpoints.
**How to avoid:** Always pass `connect_args={"check_same_thread": False}` to `create_engine`.
**Warning signs:** Intermittent database errors under load.

### Pitfall 2: Windows stdout encoding
**What goes wrong:** `UnicodeEncodeError` when printing non-ASCII characters (Portuguese city names, etc).
**Why it happens:** Windows console defaults to cp1252 encoding.
**How to avoid:** Add `sys.stdout.reconfigure(encoding="utf-8")` at the top of main.py.
**Warning signs:** Crashes when logging/printing strings with accents.

### Pitfall 3: JSON column mutation tracking
**What goes wrong:** Modifying a JSON column in-place (e.g., `group.origins.append("GIG")`) does not trigger SQLAlchemy's dirty tracking, so the change is never saved.
**Why it happens:** SQLAlchemy tracks attribute reassignment, not in-place mutation of mutable types.
**How to avoid:** Always reassign the entire list: `group.origins = group.origins + ["GIG"]` or use `flag_modified(group, "origins")` from `sqlalchemy.orm.attributes`.
**Warning signs:** Updates seem to succeed but changes disappear after reload.

### Pitfall 4: Pydantic v2 model_config instead of class Config
**What goes wrong:** Using `class Config: orm_mode = True` (Pydantic v1 style) silently does nothing in v2.
**Why it happens:** Pydantic v2 replaced `class Config` with `model_config` dict and `orm_mode` with `from_attributes`.
**How to avoid:** Use `model_config = {"from_attributes": True}` in response schemas.
**Warning signs:** Response serialization fails or returns empty objects.

### Pitfall 5: Date serialization in JSON
**What goes wrong:** `datetime.date` objects cause serialization errors when stored in JSON columns or returned in responses.
**Why it happens:** JSON has no native date type; SQLAlchemy JSON column uses standard json.dumps.
**How to avoid:** Keep date fields as dedicated Date columns (not inside JSON). Pydantic handles date serialization in responses automatically.
**Warning signs:** TypeError during JSON serialization.

### Pitfall 6: Forgetting to override get_db in tests
**What goes wrong:** Tests modify the production database.
**Why it happens:** FastAPI dependency injection uses the real get_db unless explicitly overridden.
**How to avoid:** In conftest.py, use `app.dependency_overrides[get_db] = override_get_db` with an in-memory SQLite database.
**Warning signs:** Test data leaking between test runs; tests failing on second run.

## Code Examples

### Test Fixture Pattern (conftest.py)
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db")
def db_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

### CRUD Route Pattern
```python
# app/routes/route_groups.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RouteGroup
from app.schemas import RouteGroupCreate, RouteGroupUpdate, RouteGroupResponse
from app.services.route_group_service import check_active_group_limit

router = APIRouter(prefix="/route-groups", tags=["route-groups"])
DbDep = Annotated[Session, Depends(get_db)]

@router.post("/", response_model=RouteGroupResponse, status_code=201)
def create_route_group(data: RouteGroupCreate, db: DbDep):
    if data.is_active is not False:  # default is active
        check_active_group_limit(db)
    group = RouteGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

@router.get("/", response_model=list[RouteGroupResponse])
def list_route_groups(db: DbDep):
    return db.query(RouteGroup).all()

@router.get("/{group_id}", response_model=RouteGroupResponse)
def get_route_group(group_id: int, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    return group

@router.patch("/{group_id}", response_model=RouteGroupResponse)
def update_route_group(group_id: int, data: RouteGroupUpdate, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    update_data = data.model_dump(exclude_unset=True)
    # If activating, check limit
    if update_data.get("is_active") is True and not group.is_active:
        check_active_group_limit(db, exclude_id=group.id)
    for key, value in update_data.items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group

@router.delete("/{group_id}", status_code=204)
def delete_route_group(group_id: int, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    db.delete(group)
    db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `class Config: orm_mode = True` | Pydantic v2 `model_config = {"from_attributes": True}` | Pydantic 2.0 (2023) | Must use new syntax |
| SQLAlchemy 1.x `Column(Integer)` | SQLAlchemy 2.0 `Mapped[int] = mapped_column()` | SQLAlchemy 2.0 (2023) | Type-annotated models, better IDE support |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.95+ (2023) | on_event is deprecated; use lifespan |
| `pydantic.BaseSettings` | `pydantic_settings.BaseSettings` | Pydantic 2.0 (2023) | Moved to separate package |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: Deprecated in favor of lifespan context manager
- `pydantic.BaseSettings`: Moved to `pydantic-settings` package
- SQLAlchemy `declarative_base()` function: Replaced by inheriting from `DeclarativeBase`

## Open Questions

1. **IATA code validation strictness**
   - What we know: 3-uppercase-letter regex covers the format; Amadeus API itself rejects invalid codes at query time
   - What's unclear: Whether to also reject obviously wrong codes (like "ZZZ") at creation time
   - Recommendation: Use regex only for v1. The Amadeus API is the authoritative validator. A hardcoded list would require maintenance and adds no value since Phase 2 will validate against the actual API.

2. **created_at / updated_at timestamps on RouteGroup**
   - What we know: Not explicitly in requirements, but useful for debugging and future features
   - What's unclear: Whether to add them in Phase 1 or defer
   - Recommendation: Add them in Phase 1 since create_all makes schema changes free at this stage. They cost nothing and help debugging.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | Yes | 3.13.3 | None needed |
| pip | Package installation | Yes | 25.0.1 | None needed |
| venv | Virtual environment | Yes | Built-in with Python 3.13 | None needed |
| SQLite | Database | Yes | Built-in with Python | None needed |

**Missing dependencies with no fallback:** None. All dependencies are installable via pip.

**Missing dependencies with fallback:** None.

**Note:** On Windows, use `python` (not `python3`) and `venv\Scripts\activate` (not `source venv/bin/activate`).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (Wave 0 must create pytest.ini or pyproject.toml [tool.pytest] section) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | App starts and responds on localhost | smoke | `python -m pytest tests/test_app_startup.py -x` | Wave 0 |
| INFRA-02 | .env controls configuration | unit | `python -m pytest tests/test_config.py -x` | Wave 0 |
| INFRA-03 | SQLite created with tables on first run | integration | `python -m pytest tests/test_database.py -x` | Wave 0 |
| ROUTE-01 | Create RouteGroup with all fields | integration | `python -m pytest tests/test_route_groups.py::test_create_route_group -x` | Wave 0 |
| ROUTE-02 | Optional target_price field | integration | `python -m pytest tests/test_route_groups.py::test_create_with_target_price -x` | Wave 0 |
| ROUTE-03 | Activate/deactivate without deleting | integration | `python -m pytest tests/test_route_groups.py::test_toggle_active -x` | Wave 0 |
| ROUTE-04 | Edit existing RouteGroup | integration | `python -m pytest tests/test_route_groups.py::test_update_route_group -x` | Wave 0 |
| ROUTE-05 | Delete RouteGroup | integration | `python -m pytest tests/test_route_groups.py::test_delete_route_group -x` | Wave 0 |
| ROUTE-06 | Reject 11th active group | integration | `python -m pytest tests/test_route_groups.py::test_max_active_groups_limit -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/__init__.py` (empty, needed for package)
- [ ] `tests/conftest.py` (shared fixtures: test db, test client, session override)
- [ ] `tests/test_route_groups.py` (covers ROUTE-01 through ROUTE-06)
- [ ] `tests/test_config.py` (covers INFRA-02)
- [ ] `tests/test_database.py` (covers INFRA-03)
- [ ] `tests/test_app_startup.py` (covers INFRA-01)
- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` section
- [ ] Framework install: `pip install pytest httpx`

## Sources

### Primary (HIGH confidence)
- FastAPI official docs: https://fastapi.tiangolo.com/tutorial/sql-databases/ (SQLAlchemy + SQLite patterns)
- FastAPI official docs: https://fastapi.tiangolo.com/advanced/events/ (lifespan events)
- Pydantic official docs: https://docs.pydantic.dev/latest/concepts/validators/ (field validators v2)
- PyPI registry: version numbers verified via `pip index versions` on 2026-03-24

### Secondary (MEDIUM confidence)
- https://chaoticengineer.hashnode.dev/fastapi-sqlalchemy (SQLAlchemy 2.0 patterns with FastAPI)
- https://github.com/zhanymkanov/fastapi-best-practices (project structure best practices)
- https://github.com/sqlalchemy/sqlalchemy/discussions/8640 (JSON lists in SQLite)
- https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/ (testing strategies)

### Tertiary (LOW confidence)
- None. All findings verified with official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (all packages verified on PyPI, official docs consulted)
- Architecture: HIGH (follows FastAPI official tutorial patterns, adapted for project scale)
- Pitfalls: HIGH (well-documented issues with SQLite threading, JSON mutation tracking, Pydantic v2 migration)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable stack, no rapid changes expected)
