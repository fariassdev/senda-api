# Senda Development Guide

This document provides quick reference for working with the Senda project (clean architecture migration target).

## Quick Start

### 1. Verify Setup
```bash
make verify
```
This checks:
- All dependencies are installed
- Imports work correctly
- Settings are configured
- Routes are registered

### 2. Run Development Server
```bash
make runserver-dev
```
Server will start on: http://localhost:8081

API Documentation: http://localhost:8081/docs

### 3. View Available Commands
```bash
make help
```

## Common Commands

### Server Management
```bash
make runserver          # Production mode (port 8081)
make runserver-dev      # Development mode with auto-reload
```

### Database Migrations
```bash
# Create a new migration
make migration message="add courses table"

# Apply migrations
make migrate

# Rollback one migration
make migrate-down

# View migration history
make migrate-history

# Reset database (careful!)
make db-reset
```

### Testing
```bash
make test              # Run all tests
make test-cov          # Run with coverage report
```

### Code Quality
```bash
make lint              # Check code with Ruff (linting)
make lint-fix          # Auto-fix linting issues
make format            # Check formatting
make format-fix        # Auto-fix formatting
make types             # Type check with mypy
make check             # Run all checks (lint + format + types)
make fix               # Auto-fix all issues (lint + format)
```

### Docker
```bash
make docker-build      # Build and start containers
make docker-up         # Start existing containers
make docker-down       # Stop containers
make docker-logs       # View logs
```

## Project Structure

```
senda/
├── api/                    # API Layer (Routes & Schemas)
│   ├── routes/            # HTTP endpoints
│   ├── schemas/           # Request/Response models
│   └── middlewares.py     # API middleware
├── core/                   # Application Core
│   ├── container.py       # Dependency injection
│   ├── dependencies.py    # FastAPI dependencies
│   ├── config.py          # Configuration
│   └── security.py        # Auth utilities
├── domain/                 # Domain Layer (Business Logic Interfaces)
│   ├── dtos/              # Data transfer objects
│   ├── repositories/      # Repository interfaces (ABC)
│   └── services/          # Service interfaces (ABC)
├── infrastructure/         # Infrastructure Layer (Data Access)
│   ├── models.py          # SQLAlchemy models
│   ├── mappers/           # Model↔DTO mappers
│   ├── repositories/      # Repository implementations
│   └── alembic/           # Database migrations
└── services/               # Services Layer (Business Logic)
    └── *.py               # Service implementations
```

## Architecture Layers

1. **Domain Layer** (`domain/`)
   - Pure business logic
   - No framework dependencies
   - Interfaces only (ABC)

2. **Infrastructure Layer** (`infrastructure/`)
   - Database access
   - External services
   - Implements domain interfaces

3. **Services Layer** (`services/`)
   - Business logic orchestration
   - Uses repositories
   - Implements service interfaces

4. **API Layer** (`api/`)
   - HTTP request/response
   - Input validation
   - Uses services

## Environment Variables

Create a `.env` file with:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/senda_db

# Security
SECRET_KEY=your-secret-key-here

# Application
DEBUG=true
ENVIRONMENT=development
```

## Code Quality Tools

### Senda Uses Ruff

Senda uses **[Ruff](https://github.com/astral-sh/ruff)** - an extremely fast Python linter and formatter written in Rust.

**Why Ruff?**
- ⚡ **10-100x faster** than traditional tools
- 🔧 Replaces: flake8, black, isort, pyupgrade, autoflake, and more
- 🎯 Single tool, single configuration
- ✅ Compatible with existing configs

**Ruff includes:**
- **Linting** - Checks code quality (replaces flake8)
- **Formatting** - Auto-formats code (replaces black)
- **Import sorting** - Organizes imports (replaces isort)
- **Code upgrades** - Modernizes syntax (replaces pyupgrade)

**Quick Commands:**
```bash
# Check everything
make check

# Fix everything
make fix

# Or run individual checks
make lint          # Just linting
make format        # Just formatting
make types         # Just type checking (mypy)
```

**Configuration:**
- Ruff config: `pyproject.toml` under `[tool.ruff]`
- Pre-commit: Automatically runs on Senda files

## Next Steps

1. **Analyze**: Review `SENDA_ORIGINAL_ANALYSIS.md` for original project details
2. **Plan**: Check `SENDA_MIGRATION_GUIDE.md` for implementation steps
3. **Implement**: Follow `DOMAIN_MAPPING.md` for entity translations
4. **Test**: Write tests in `tests/`

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8081
netstat -ano | findstr :8081

# Kill the process (Windows)
taskkill /PID <process_id> /F
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start PostgreSQL
docker-compose up -d postgres
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
make verify
```

## Resources

- **Copilot Instructions**: `.github/copilot-instructions.md`
- **Migration Guide**: `SENDA_MIGRATION_GUIDE.md`
- **Original Analysis**: `SENDA_ORIGINAL_ANALYSIS.md`
- **Domain Mapping**: `DOMAIN_MAPPING.md`
