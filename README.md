# Dentist AI SaaS — Backend

Production-ready backend for dental clinic management.  
**Stack:** FastAPI · PostgreSQL · SQLAlchemy (async) · Alembic · JWT Auth

---

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Docker & Docker Compose (optional, recommended for local DB)

---

## Local Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd dentist-saas-backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your local DB credentials
```

Minimum required in `.env`:
```
APP_SECRET_KEY=any-random-256-bit-string
DATABASE_URL=postgresql+asyncpg://dentist:dentist123@localhost:5432/dentist_db
JWT_SECRET_KEY=any-random-256-bit-string
```

### 5. Start PostgreSQL (via Docker — recommended)

```bash
docker-compose up -d db
```

Or use a local PostgreSQL instance — create the database manually:
```sql
CREATE DATABASE dentist_db;
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Verify

- API: [http://localhost:8000/health](http://localhost:8000/health)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Tests

```bash
pytest tests/unit/            # Unit tests
pytest tests/integration/     # Integration tests (requires running DB)
pytest tests/rbac/            # RBAC isolation tests
pytest --cov=app tests/       # With coverage report
```

---

## Docker (Full Stack)

```bash
# Start app + db
docker-compose up

# Run migrations inside container
docker-compose exec app alembic upgrade head

# Seed development data
docker-compose exec app python scripts/seed_dev.py
```

---

## Project Structure

```
app/
├── main.py             # FastAPI app entry point
├── dependencies.py     # Shared FastAPI dependencies
├── core/               # Config, security, middleware, exceptions
├── database/           # SQLAlchemy engine, session, mixins
├── models/             # ORM models (DB tables)
├── schemas/            # Pydantic request/response schemas
├── api/v1/             # Route definitions
├── services/           # Business logic
├── repositories/       # DB queries
├── rbac/               # Role-based access control
├── tasks/              # Celery tasks (POST-MVP, stubbed)
├── integrations/       # Third-party integrations (stubbed)
├── utils/              # Pure utility functions
└── constants/          # Enums and string constants
```

---

## Environment Variables

See [`.env.example`](.env.example) for all required and optional variables.

---

## Development Build Phases

See [`engineering/DEVELOPMENT_PHASES.md`](engineering/DEVELOPMENT_PHASES.md) for the full build plan.
