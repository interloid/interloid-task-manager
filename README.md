# Interloid Task Manager

A production-ready, asynchronous Task Management REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, and **Redis**.

Interloid Task Manager features robust JWT-based authentication, role-based authorization, session management, Google OAuth 2.0 integration, OTP-based email verification, password reset flows, AWS S3 file attachments, task commenting, background email queue processing via **ARQ**, and real-time event streaming with **Server-Sent Events (SSE)** over **Redis Pub/Sub**.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Architecture & Structure](#project-architecture--structure)
- [Data Models & Schema](#data-models--schema)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Dependency Management (uv)](#3-dependency-management-uv)
  - [4. Database Migrations](#4-database-migrations)
  - [5. Seed Demo Data](#5-seed-demo-data)
  - [6. Run the Application](#6-run-the-application)
  - [7. Run the Background Email Worker](#7-run-the-background-email-worker)
- [Testing](#testing)
- [Code Quality & Tooling](#code-quality--tooling)
- [Docker Deployment](#docker-deployment)
- [Security Features](#security-features)

---

## Features

### Authentication & Authorization
- **JWT & Opaque Refresh Tokens:** Short-lived JWT access tokens paired with secure, opaque refresh tokens.
- **Token Rotation & Revocation:** Refresh tokens rotate on every use. Only cryptographic SHA-256 hashes are stored in PostgreSQL; database row-locking prevents concurrent race conditions.
- **Session Management:** Track active sessions by IP and User-Agent, with family ID tracking, selective session revoking, and global logout (`logout-all`).
- **Google OAuth 2.0:** One-click OAuth login and callback authentication flow using Authlib.
- **OTP Verification & Password Recovery:** Email verification and password reset flows with timed OTP codes, attempt limits, and cooldown intervals.
- **Password Security:** High-entropy password hashing using Argon2 (`pwdlib[argon2]`).
- **Role-Based Access Control (RBAC):** Distinct roles (`ADMIN` vs `USER`). Protections prevent accidental deletion or deactivation of the last active administrator.


### Task Management
- **Full CRUD:** Create, list, retrieve, update, and delete tasks.
- **Filtering & Search:** Filter tasks by status (`Todo`, `In Progress`, `Done`), priority (`Low`, `Medium`, `High`), due date ranges, and case-insensitive keyword search.
- **Ownership Scoping:** Regular users can only access their own tasks; administrators can view and manage tasks across all users.
- **Pagination:** Configurable page size with strict query boundary constraints.

### Task Comments & S3 Attachments
- **Task Comments:** Add, update, view, and delete discussion comments on tasks.
- **AWS S3 File Storage:** Direct upload of attachments with MIME-type detection (`python-magic`) and file size validation.
- **Presigned URLs:** Time-limited presigned S3 URLs for secure file downloading.
- **Cascade Cleanup:** Deleting a task automatically cleans up associated database records and deletes uploaded files from the S3 bucket.

### Notifications & Real-Time Streaming
- **Activity Alerts:** Automated notifications triggered on task assignment and comment activity.
- **Real-Time Delivery:** Server-Sent Events (SSE) via `/api/v1/notifications/stream` powered by Redis Pub/Sub channels.
- **Notification Inbox:** Paginated notifications, mark individual or all as read, unread count tracking, and bulk deletion of read notifications.

### Asynchronous Background Workers
- **ARQ Job Queue:** Offloads email operations (welcome emails, verification OTPs, password reset codes) to background workers backed by Redis.
- **Async SMTP:** Non-blocking email sending using `aiosmtplib` and Jinja2 HTML templates, complete with automated retry policies.

### Observability & Code Quality
- **Centralized Structured Logging:** Custom JSON-compatible log formatter.
- **Request Tracing:** Unique `X-Request-ID` generated or propagated per request using Python `ContextVar`.
- **Request Time Middleware:** Precise measurement of incoming request execution latency.
- **Strict Quality Gates:** Enforced typing with Mypy, high-speed formatting and linting with Ruff, and Git hooks via Pre-commit.

---

## Tech Stack

| Category | Technology |
|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+) |
| **Server** | [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| **Database** | [PostgreSQL](https://www.postgresql.org/) |
| **ORM & Migrations** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async with `asyncpg`), [Alembic](https://alembic.sqlalchemy.org/) |
| **Cache & Real-Time** | [Redis](https://redis.io/) (Pub/Sub for SSE, Rate Limiting) |
| **Worker Queue** | [ARQ](https://arq-docs.helpmanual.io/) |
| **Object Storage** | [AWS S3](https://aws.amazon.com/s3/) (via `boto3`) |
| **Security & Auth** | Argon2 (`pwdlib`), `pyjwt`, `authlib`, `uuid6` (UUIDv7) |
| **Email Delivery** | `aiosmtplib`, `jinja2` |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) |
| **Testing** | `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` |
| **Linting & Typing** | `ruff`, `mypy`, `pre-commit` |
| **Containerization** | Docker, Docker Compose |

---

## Project Architecture & Structure

```text
.
├── app/
│   ├── api/
│   │   ├── deps.py                     # Common FastAPI dependencies (Auth, DB, etc.)
│   │   ├── responses.py                # Standardized OpenAPI error responses
│   │   └── v1/
│   │       ├── api.py                  # API router aggregator
│   │       └── endpoints/
│   │           ├── auth.py             # Login, register, refresh, logout
│   │           ├── email_auth.py       # OTP verification & resend
│   │           ├── health.py           # /health and /ready endpoints
│   │           ├── notifications.py    # Notification inbox & SSE streaming
│   │           ├── oauth.py            # Google OAuth login & callback
│   │           ├── password_recovery.py# Forgot password & OTP reset
│   │           ├── session.py          # Session listing, revocation, logout-all
│   │           ├── task_attachments.py # S3 file uploads & presigned downloads
│   │           ├── task_comments.py    # Task comment CRUD
│   │           ├── tasks.py            # Task CRUD, filters, search
│   │           ├── user_profile.py     # Profile & password updates
│   │           └── users.py            # Admin user management
│   ├── core/                           # Application configuration, security, logger
│   ├── db/                             # Database engine, session, base models
│   ├── enums/                          # Enums (Roles, TaskStatus, TaskPriority, etc.)
│   ├── exceptions/                     # Custom application exceptions and handlers
│   ├── mail/                           # Email templates and async SMTP mailer
│   ├── middleware/                     # Request ID, request logging, process timing
│   ├── models/                         # SQLAlchemy declarative models
│   ├── repositories/                   # Data access layer (CRUD patterns)
│   ├── schemas/                        # Pydantic v2 validation schemas
│   ├── services/                       # Business logic services
│   ├── workers/                        # ARQ background worker settings and jobs
│   └── main.py                         # Application factory and lifespan events
├── migrations/                         # Alembic database migrations
├── scripts/
│   ├── seed.py                         # Local database seed runner
│   └── seed_data.py                    # Initial seed data fixtures
├── tests/                              # Pytest test suite (auth, tasks, comments, etc.)
├── .env.example                        # Example local environment configuration
├── .env.test.example                   # Example test environment configuration
├── docker-compose.yml                  # Compose definition for API & worker
├── Dockerfile                          # Multi-stage production container image
├── pyproject.toml                      # Project metadata, dependencies, tool configurations
└── uv.lock                             # Locked dependency graph
```

---

## Data Models & Schema

The application uses **UUIDv7** for all primary keys to guarantee sequential, timestamp-ordered indexing with UUID collision safety.

### 1. `users`
- `id` (UUIDv7, PK)
- `email` (String(255), Unique, Indexed)
- `password_hash` (String(255), Nullable for OAuth users)
- `first_name` (String(100))
- `last_name` (String(100))
- `role` (Enum: `ADMIN`, `USER`)
- `is_active` (Boolean, Default: True)
- `is_verified` (Boolean, Default: False)
- `password_changed_at` (DateTime, Nullable)
- `created_at`, `updated_at` (DateTime with timezone)

### 2. `refresh_tokens`
- `id` (UUIDv7, PK)
- `user_id` (UUIDv7, FK -> `users.id`)
- `family_id` (UUIDv7, Session group identifier)
- `token_hash` (String(64), SHA-256 hash of opaque token, Unique, Indexed)
- `expires_at` (DateTime with timezone)
- `revoked_at` (DateTime with timezone, Nullable)
- `user_agent` (String(500), Nullable)
- `ip_address` (String(45), Nullable)
- `created_at`, `updated_at` (DateTime with timezone)

### 3. `oauth_accounts`
- `id` (UUIDv7, PK)
- `user_id` (UUIDv7, FK -> `users.id`)
- `provider` (String(50), e.g. `google`)
- `oauth_user_id` (String(255), Unique per provider)
- `created_at`, `updated_at` (DateTime with timezone)

### 4. `email_otps`
- `id` (UUIDv7, PK)
- `email` (String(255), Indexed)
- `hashed_otp` (String(64), SHA-256 hash)
- `otp_type` (Enum: `VERIFY_EMAIL`, `RESET_PASSWORD`)
- `attempts` (Integer, Default: 0)
- `expires_at` (DateTime with timezone)
- `created_at`, `updated_at` (DateTime with timezone)

### 5. `tasks`
- `id` (UUIDv7, PK)
- `owner_id` (UUIDv7, FK -> `users.id`, Indexed)
- `title` (String(200))
- `description` (Text, Nullable)
- `status` (Enum: `Todo`, `In Progress`, `Done`, Indexed)
- `priority` (Enum: `Low`, `Medium`, `High`)
- `due_date` (Date, Nullable, Indexed)
- `created_at`, `updated_at` (DateTime with timezone)

### 6. `task_comments`
- `id` (UUIDv7, PK)
- `task_id` (UUIDv7, FK -> `tasks.id`, ON DELETE CASCADE, Indexed)
- `user_id` (UUIDv7, FK -> `users.id`, ON DELETE CASCADE, Indexed)
- `content` (Text)
- `created_at`, `updated_at` (DateTime with timezone)

### 7. `task_attachments`
- `id` (UUIDv7, PK)
- `task_id` (UUIDv7, FK -> `tasks.id`, ON DELETE CASCADE, Indexed)
- `uploaded_by_id` (UUIDv7, FK -> `users.id`, ON DELETE CASCADE, Indexed)
- `original_filename` (String(255))
- `storage_key` (String(1024), Unique S3 object key)
- `content_type` (String(100))
- `file_size` (BigInteger, in bytes)
- `created_at`, `updated_at` (DateTime with timezone)

### 8. `notifications`
- `id` (UUIDv7, PK)
- `user_id` (UUIDv7, FK -> `users.id`, ON DELETE CASCADE, Indexed)
- `task_id` (UUIDv7, FK -> `tasks.id`, ON DELETE SET NULL, Nullable, Indexed)
- `type` (Enum: `TASK_ASSIGNED`, `TASK_STATUS_UPDATED`, `TASK_COMMENT_ADDED`, etc.)
- `title` (String(200))
- `message` (Text)
- `status` (Enum: `UNREAD`, `READ`, Indexed)
- `created_at`, `updated_at` (DateTime with timezone)

---

## API Reference

All API v1 routes are prefixed with `/api/v1`.

### Health & Readiness
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/health` | Liveness check (checks server responsiveness) | Public |
| `GET` | `/api/v1/ready` | Readiness check (validates database connectivity) | Public |

### Authentication
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new account and send verification OTP | Public |
| `POST` | `/api/v1/auth/login` | Authenticate with email/password; returns access & refresh tokens | Public |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token and issue new token pair | Public |
| `POST` | `/api/v1/auth/logout` | Revoke current refresh token | Authenticated |
| `POST` | `/api/v1/auth/verify-email` | Verify email address using received OTP | Public |
| `POST` | `/api/v1/auth/resend-verification` | Request a new email verification OTP | Public |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset OTP email | Public |
| `POST` | `/api/v1/auth/reset-password` | Set new password using valid reset OTP | Public |

### OAuth (Google)
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/auth/{provider}/login` | Initiate OAuth redirect (e.g. `google`) | Public |
| `GET` | `/api/v1/auth/{provider}/callback` | Handle OAuth callback from provider | Public |

### Session Management
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/auth/sessions` | List active sessions and device info for current user | Authenticated |
| `DELETE` | `/api/v1/auth/sessions/{id}` | Revoke a specific session family | Authenticated |
| `POST` | `/api/v1/auth/logout-all` | Terminate all active sessions for current user | Authenticated |

### User Profile & Administration
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/users/me` | Fetch authenticated user profile | Authenticated |
| `PATCH` | `/api/v1/users/me/password` | Change current account password | Authenticated |
| `GET` | `/api/v1/users` | List all system users with pagination | Admin |
| `PATCH` | `/api/v1/users/{id}` | Update user details, active status, or role | Admin |

### Task Management
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/tasks` | Create a new task (owner auto-assigned) | Authenticated |
| `GET` | `/api/v1/tasks` | List tasks with filters, search, and pagination | Authenticated |
| `GET` | `/api/v1/tasks/{id}` | Retrieve specific task details | Authenticated |
| `PATCH` | `/api/v1/tasks/{id}` | Update task title, description, status, priority, due date | Authenticated |
| `DELETE` | `/api/v1/tasks/{id}` | Delete task and its attachments from S3 | Authenticated |

#### Task Filtering Query Parameters
- `?status=Todo|In Progress|Done`
- `?priority=Low|Medium|High`
- `?due_from=YYYY-MM-DD`
- `?due_to=YYYY-MM-DD`
- `?search=<keyword>` (case-insensitive title search)
- `?owner_id=<uuid>` (available to administrators only)
- `?page=1&page_size=20` (defaults: page 1, size 20, max 100)

### Task Comments
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/tasks/{task_id}/comments` | Add a comment to a task | Authenticated |
| `GET` | `/api/v1/tasks/{task_id}/comments` | List all comments for a task | Authenticated |
| `PATCH` | `/api/v1/tasks/{task_id}/comments/{comment_id}` | Edit an existing comment | Comment Author |
| `DELETE` | `/api/v1/tasks/{task_id}/comments/{comment_id}` | Delete a comment | Author or Admin |

### Task Attachments
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/tasks/{task_id}/attachments` | Upload a file attachment to AWS S3 | Authenticated |
| `GET` | `/api/v1/tasks/{task_id}/attachments` | List metadata of all attachments on a task | Authenticated |
| `GET` | `/api/v1/tasks/{task_id}/attachments/{attachment_id}` | Retrieve single attachment metadata | Authenticated |
| `GET` | `/api/v1/tasks/{task_id}/attachments/{attachment_id}/download` | Generate secure presigned S3 download URL | Authenticated |
| `DELETE` | `/api/v1/tasks/{task_id}/attachments/{attachment_id}` | Delete attachment from database and S3 | Authenticated |

### Notifications
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/notifications` | List user notifications (`?page=1&page_size=10&is_read=false`) | Authenticated |
| `GET` | `/api/v1/notifications/unread-count` | Get count of unread notifications | Authenticated |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark a single notification as read | Authenticated |
| `PATCH` | `/api/v1/notifications/read-all` | Mark all user notifications as read | Authenticated |
| `DELETE` | `/api/v1/notifications` | Delete all read notifications (`?status=read`) | Authenticated |
| `DELETE` | `/api/v1/notifications/{id}` | Delete a specific notification | Authenticated |
| `GET` | `/api/v1/notifications/stream` | Server-Sent Events (SSE) real-time notification stream | Authenticated |

---

## Getting Started

### Prerequisites
- **Python 3.12+**
- **uv** (recommended package installer & runner): [Install uv](https://docs.astral.sh/uv/)
- **PostgreSQL 15+**
- **Redis 7+**
- **AWS S3 Bucket** (for attachment storage)

---

### 1. Clone Repository

```bash
git clone git@github.com:interloid/interloid-task-manager.git
cd interloid-task-manager
```

---

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to configure your local credentials:

```ini
APP_NAME="Interloid Task Manager"
APP_VERSION="0.1.0"
DEBUG=True
HOST="0.0.0.0"
PORT=8000
LOG_LEVEL="INFO"

# Database Configuration
DB_HOST="localhost"
DB_PORT=5432
DB_NAME="fastapi_db"
DB_USER="postgres"
DB_PASSWORD="your_password"
DB_SSL=false

# Redis Configuration
REDIS_URL="redis://localhost:6379/0"
REDIS_KEY_PREFIX="task_manager_dev"

# Authentication Secrets
JWT_SECRET_KEY="generate-at-least-32-byte-secret-key-here"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SECRET_KEY="session-cookie-secret-key"

# Google OAuth
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

# AWS S3 Storage
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
AWS_REGION="ap-southeast-1"
S3_BUCKET_NAME="your-s3-bucket-name"
S3_PRESIGNED_URL_EXPIRE_SECONDS=300

# SMTP & Email Settings
SMTP_HOST="smtp.example.com"
SMTP_PORT=587
SMTP_USERNAME="smtp-username"
SMTP_PASSWORD="smtp-password"
SMTP_FROM_EMAIL="noreply@example.com"
SMTP_USE_TLS=true

# OTP Configuration
OTP_SECRET_KEY="generate-at-least-32-byte-otp-secret-key"
EMAIL_OTP_EXPIRE_MINUTES=5
EMAIL_OTP_MAX_ATTEMPTS=5
EMAIL_OTP_RESEND_COOLDOWN_SECONDS=60
PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS=60
```

> [!IMPORTANT]
> Keep `JWT_SECRET_KEY` and `OTP_SECRET_KEY` secure, unique, and at least 32 characters in length. Never commit `.env` to source control.

---

### 3. Dependency Management (uv)

Install all dependencies and create the `.venv` virtual environment:

```bash
uv sync
```

Activate the virtual environment (optional when using `uv run`):

```bash
# On Linux / macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

---

### 4. Database Migrations

Apply Alembic migrations to set up the database schema:

```bash
# Check current migration status
uv run alembic current

# Upgrade database schema to latest version
uv run alembic upgrade head
```

---

### 5. Seed Demo Data

Populate the database with sample users and starter tasks:

```bash
uv run python scripts/seed.py
```

#### Demo Accounts
| Role | Email | Password |
|---|---|---|
| **Admin** | `amaldas@example.com` | `pass1234` |
| **User** | `naveen@example.com` | `pass1234` |
| **User** | `saniya@example.com` | `pass1234` |

---

### 6. Run the Application

Start the FastAPI ASGI server with auto-reload:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **Interactive OpenAPI Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 7. Run the Background Email Worker

In a separate terminal, launch the **ARQ worker** to process queued email tasks:

```bash
uv run arq app.workers.email_worker.WorkerSettings
```

---

## Testing

The project maintains an automated test suite covering endpoints, authentication guards, database repositories, and edge cases.

### Setup Test Environment
Create the `.env.test` file:

```bash
cp .env.test.example .env.test
```

### Run Tests

```bash
# Run entire test suite
ENV_FILE=.env.test uv run pytest

# Run task module tests only
ENV_FILE=.env.test uv run pytest tests/tasks

# Run tests with terminal coverage summary
ENV_FILE=.env.test uv run pytest --cov=app --cov-report=term-missing
```

---

## Code Quality & Tooling

Standardized checks run prior to every commit to maintain code health.

### Ruff (Linter & Formatter)
```bash
# Lint checks
uv run ruff check .

# Auto-fix lint issues
uv run ruff check . --fix

# Code formatting check
uv run ruff format --check .

# Auto-format files
uv run ruff format .
```

### Mypy (Static Type Checking)
```bash
uv run mypy .
```

### Pre-commit Hooks
Install the configured Git pre-commit hooks:

```bash
uv run pre-commit install
```

Execute pre-commit checks manually across all files:

```bash
uv run pre-commit run --all-files
```

---

## Docker Deployment

A multi-stage `Dockerfile` and `docker-compose.yml` are provided for containerized deployments.

### Running with Docker Compose

1. Create a production environment file:
   ```bash
   cp .env.example .env.production
   ```

2. Start the API server and the background email worker:
   ```bash
   docker compose up -d
   ```

3. View real-time container logs:
   ```bash
   docker compose logs -f
   ```

4. Tear down containers:
   ```bash
   docker compose down
   ```

---

## Security Features

- **Argon2 Password Hashing:** State-of-the-art memory-hard key derivation to prevent brute-force and GPU-based dictionary attacks.
- **Opaque Refresh Tokens:** Stored only as SHA-256 hashes in the database. Raw tokens are never persisted.
- **Strict Token Rotation:** Every refresh operation invalidates the previous refresh token and issues a fresh pair.
- **Session Locking:** Row-level locks (`SELECT FOR UPDATE`) on refresh token operations eliminate concurrency race conditions.
- **Rate-Limiting Ready:** Built-in rate limiting hooks for sensitive authentication endpoints via Redis.
- **Presigned S3 URLs:** Temporary, short-lived presigned URLs prevent public exposure of user-uploaded S3 files.
- **Safe Admin Operations:** Guard logic guarantees the last active administrator account cannot be deactivated or deleted.
- **SQL Injection Prevention:** Pure async SQLAlchemy parameterization across all queries.
