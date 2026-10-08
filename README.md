# Interloid Task Manager

A production-oriented Task Management REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **JWT authentication**.

The project provides secure authentication, role-based authorization, refresh-token management, user administration, task management, automated testing, code-quality checks, and containerized deployment.

---

## Features

### Authentication

* User registration
* User login
* JWT access-token generation
* Opaque refresh tokens
* Refresh-token rotation
* Refresh-token revocation
* Concurrency-safe refresh-token rotation using database row locking
* Logout
* Get current user (`/me`)
* Change password
* Revoke all refresh tokens after password change
* Inactive-user validation
* Password hashing using Argon2
* Dummy password verification to reduce login timing differences
* Database-level duplicate email protection

### Authorization

The application supports two roles:

* `admin`
* `user`

Authorization features include:

* Admin-only user listing
* Admin user-role management
* User activation/deactivation
* Protection against admin self-demotion
* Protection against admin self-deactivation
* Protection against removing the last active admin
* Database locking for concurrent last-active-admin protection
* Active-user validation on authenticated requests
* Task ownership protection
* Users can manage only their own tasks
* Admins can view and manage all users' tasks

### Task Management

Task management supports:

* Create a task
* List tasks
* Get a task by ID
* Update a task
* Delete a task
* Filter tasks by status
* Filter tasks by priority
* Filter tasks by due-date range
* Case-insensitive title search
* Admin filtering by `owner_id`
* Ownership-based access control

Task ownership is determined from the authenticated user and is never accepted from the task-creation request body.

---

## Tech Stack

* Python 3.12+
* FastAPI
* PostgreSQL
* SQLAlchemy 2.x (Async)
* Alembic
* PyJWT
* Argon2
* Pydantic
* Pytest
* HTTPX
* Ruff
* Mypy
* Pre-commit
* uv
* Docker
* AWS EC2

---

## Project Structure

```text
app/
├── api/
│   ├── deps.py
│   ├── responses.py
│   └── v1/
│       ├── api.py
│       └── endpoints/
│           ├── auth.py
│           ├── health.py
│           ├── tasks.py
│           └── users.py
├── core/
├── db/
├── enums/
├── exceptions/
├── middleware/
├── models/
├── repositories/
├── schemas/
├── services/
└── main.py

migrations/
scripts/
tests/
Dockerfile
alembic.ini
pyproject.toml
```

---

## Data Models

### User

The `users` table contains:

* UUID7 ID
* Email
* Password hash
* First name
* Last name
* Role
* Active status
* Created timestamp
* Updated timestamp

### Refresh Token

The `refresh_tokens` table contains:

* UUID7 ID
* User ID
* Token hash
* Expiration time
* Revocation time
* Created timestamp
* Updated timestamp

Only the **SHA-256 hash** of the opaque refresh token is stored in the database. The raw refresh token is returned to the client and is not persisted.

### Task

The `tasks` table contains:

* UUID7 ID
* Owner ID
* Title
* Description
* Status
* Priority
* Due date
* Created timestamp
* Updated timestamp

Indexes are used for commonly queried task fields, including:

* `owner_id`
* `status`
* `due_date`

---

## Task Status and Priority

Supported task statuses:

```text
Todo
In Progress
Done
```

Supported task priorities:

```text
Low
Medium
High
```

---

## API Endpoints

### Authentication

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
```

### Email Authentication

```text
POST  /api/v1/auth/verify-email
POST  /api/v1/auth/resend-verification
GET    /api/v1/auth/sessions
DELETE  /api/v1/auth/sessions/{id}
```

### Password Recovery
```text
POST  /api/v1/auth/forget-password
POST  /api/v1/auth/reset-password
```

### Session Management
```text
GET  /api/v1/auth/sessions
DELETE  /api/v1/auth/sessions/{id}
POST   /api/v1/auth/logout-all

```

### User Profile
```text
GET    /api/v1/users/me
PATCH  /api/v1/users/me/password
```

### User Administration

```text
GET    /api/v1/users
PATCH  /api/v1/users/{id}
```

These endpoints require `ADMIN` privileges.

### Tasks

```text
POST    /api/v1/tasks
GET     /api/v1/tasks
GET     /api/v1/tasks/{id}
PATCH   /api/v1/tasks/{id}
DELETE  /api/v1/tasks/{id}
```

The task-list endpoint supports:

```text
?owner_id=
?status=
?priority=
?due_from=
?due_to=
?search=
```

`owner_id` filtering is available to administrators. Normal users always receive only their own tasks.

Pagination defaults:

```text
page=1
page_size=20
```

The maximum allowed `limit` is:

```text
100
```

### Health Checks

```text
GET    /api/v1/health
GET    /api/v1/ready
```

`/health` reports whether the application is running.

`/ready` verifies whether the application is ready to serve requests by checking required dependencies such as the database.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone git@github.com:interloid/interloid-task-manager.git
cd interloid-task-manager
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Update `.env` with the configuration required for your local environment.

The application configuration includes:

```text
Application settings
Database connection
JWT secret
JWT algorithm
Access-token expiration
Refresh-token expiration
Logging configuration
```

The `JWT_SECRET_KEY` must be at least **32 bytes** long.

The value provided in `.env.example` is only a development placeholder. Generate and use a secure secret for real deployments.

Do not commit `.env`, database passwords, JWT secrets, or other production credentials to Git.

### 3. Install Dependencies and Create the Virtual Environment

The project uses `uv` for dependency and virtual-environment management.

Run:

```bash
uv sync
```

This installs the project dependencies and normally creates:

```text
.venv/
```

You can activate the environment manually on Linux/macOS:

```bash
source .venv/bin/activate
```

After activation, the terminal normally displays:

```text
(.venv)
```

To deactivate it:

```bash
deactivate
```

Manual activation is optional when using `uv run`.

For example:

```bash
uv run uvicorn app.main:app --reload
uv run pytest
uv run mypy .
uv run ruff check .
```

### 4. Apply Database Migrations

Check the current migration:

```bash
uv run alembic current
```

Apply all migrations:

```bash
uv run alembic upgrade head
```

### 5. Seed Demo Data

Create the demo users:

```bash
uv run python scripts/seed.py
```

The seed data is intended only for local development, testing, and demonstration purposes.

#### Admin Account

```text
Email: amaldas@example.com
Password: pass1234
```

#### User Accounts

```text
Email: naveen@example.com
Password: pass1234
```

```text
Email: jeffy@example.com
Password: pass1234
```

```text
Email: saniya@example.com
Password: pass1234
```

### 6. Run the Application

Start the FastAPI development server:

```bash
uv run uvicorn app.main:app --reload
```

The application runs locally on port `8000` by default.

Swagger UI:

```text
http://localhost:8000/docs
```

### Test Environment

Create the test environment file:

```bash
cp .env.test.example .env.test
---

## Authentication Flow

The application uses short-lived JWT access tokens and opaque refresh tokens.

```text
Login
  ↓
Verify email and password
  ↓
Check user is active
  ↓
Generate JWT access token
  ↓
Generate opaque refresh token
  ↓
Hash refresh token using SHA-256
  ↓
Store refresh-token hash
  ↓
Return access + refresh tokens
```

### Refresh-Token Rotation

When a refresh token is used:

```text
Refresh request
      ↓
Hash received refresh token
      ↓
Find token in database
      ↓
Lock token row
      ↓
Validate expiration/revocation
      ↓
Revoke old refresh token
      ↓
Generate new access token
      ↓
Generate new refresh token
      ↓
Store new refresh-token hash
      ↓
Return new token pair
```

Database row locking prevents concurrent requests from successfully rotating the same refresh token.

---

## Task Authorization Flow

For normal users:

```text
Authenticated USER
      ↓
Create/List/Get/Update/Delete Task
      ↓
owner_id determined from current user
      ↓
Only own tasks are accessible
```

For administrators:

```text
Authenticated ADMIN
      ↓
Task operations
      ↓
Can access tasks belonging to any user
```

When creating a task, `owner_id` always comes from the authenticated user rather than the request body.

---

## Testing

The project uses **Pytest**, **HTTPX AsyncClient**, and a separate test database for integration testing.

### Run All Tests

```bash
ENV_FILE=.env.test uv run pytest
```

### Run Task Tests

```bash
ENV_FILE=.env.test uv run pytest tests/tasks
```

### Run Tests with Coverage

```bash
ENV_FILE=.env.test uv run pytest \
  --cov=app \
  --cov-report=term-missing
```

Test coverage includes:

* Authentication
* Login
* Registration
* Refresh-token rotation
* Refresh-token revocation
* Logout
* Change password
* Authorization
* User administration
* Task CRUD
* Task ownership
* Admin task access
* Task filtering
* Task search
* Task pagination
* Request validation
* Explicit `null` PATCH validation

---

## Code Quality

The project uses:

* Ruff for linting and formatting
* Mypy for static type checking
* Pre-commit for automatic code-quality checks

### Ruff Linting

```bash
uv run ruff check .
```

Automatically fix supported issues:

```bash
uv run ruff check . --fix
```

### Ruff Formatting

```bash
uv run ruff format .
```

Check formatting without modifying files:

```bash
uv run ruff format --check .
```

### Mypy

```bash
uv run mypy .
```

### Pre-commit

Install the Git hooks:

```bash
uv run pre-commit install
```

Run all configured hooks:

```bash
uv run pre-commit run --all-files
```

Current pre-commit checks include:

```text
Trailing whitespace
End-of-file fixing
YAML validation
Ruff linting
Ruff formatting
```

Before pushing changes, run:

```bash
uv run ruff check .
uv run mypy .
ENV_FILE=.env.test uv run pytest
uv run pre-commit run --all-files
```

---


## API Documentation

FastAPI automatically provides interactive API documentation using Swagger UI.

Local Swagger UI:

```text
http://localhost:8000/docs
```

---

## Security Notes

* Passwords are hashed using Argon2.
* Raw passwords are never stored.
* Refresh tokens are generated using cryptographically secure randomness.
* Only refresh-token hashes are stored in the database.
* Refresh tokens are rotated after successful use.
* Logout revokes the corresponding refresh token.
* Password changes revoke existing refresh-token sessions.
* JWT access tokens have a limited lifetime.
* Inactive users are rejected from protected operations.
* Task ownership is determined from the authenticated user.
* Database constraints provide final protection against duplicate emails.
* Database row locking is used for concurrency-sensitive operations.
---
