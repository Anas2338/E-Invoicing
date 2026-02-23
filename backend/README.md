---
title: E-Invoicing Backend
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# FBR Invoice Integration Portal - Backend

Backend service for FBR invoice processing with validation and posting capabilities.

## Overview

This is a FastAPI-based backend service that provides:
- JWT-based authentication
- Invoice validation against FBR specifications
- Invoice posting to FBR Sandbox and Production environments
- Complete audit trail of FBR interactions
- RESTful API with versioned endpoints

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL with SQLModel ORM
- **Authentication**: JWT tokens (Better Auth integration)
- **Migrations**: Alembic
- **Package Manager**: uv
- **Python**: 3.11+

## Project Structure

```
backend/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── config/                 # Configuration and settings
│   ├── models/                 # SQLModel database models
│   ├── schemas/                # Pydantic schemas for API
│   ├── api/                    # API endpoints and middleware
│   │   ├── v1/                 # API version 1 endpoints
│   │   └── middleware/         # Authentication middleware
│   ├── services/               # Business logic services
│   ├── utils/                  # Utility functions
│   └── database/               # Database session management
├── alembic/                    # Database migrations
├── tests/                      # Test suite
├── pyproject.toml              # Project dependencies
└── .env                        # Environment variables
```

## Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- uv package manager

### Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository and navigate to backend:
```bash
cd backend
```

3. Install dependencies:
```bash
uv sync
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
uv run alembic upgrade head
```

### Running the Server

Development mode with auto-reload:
```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, access the interactive API documentation:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Environment Variables

Required environment variables (see `.env` file):

- `DATABASE_URL`: PostgreSQL connection string
- `AUTH_JWT_SECRET`: Secret key for JWT token verification
- `FBR_CLIENT_ID`: FBR API client ID
- `FBR_CLIENT_SECRET`: FBR API client secret
- `FBR_API_KEY`: FBR API key

## Database Migrations

Create a new migration:
```bash
uv run alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

Rollback migration:
```bash
uv run alembic downgrade -1
```

## Testing

Run tests:
```bash
uv run pytest
```

Run tests with coverage:
```bash
uv run pytest --cov=src tests/
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

### Invoices
- `GET /api/v1/invoices` - List user's invoices
- `POST /api/v1/invoices` - Create new invoice
- `GET /api/v1/invoices/{id}` - Get invoice details
- `PUT /api/v1/invoices/{id}` - Update invoice

### FBR Integration
- `POST /api/v1/fbr/validate` - Validate invoice against FBR
- `POST /api/v1/fbr/post` - Post validated invoice to FBR

## Development

### Code Style

The project follows PEP 8 style guidelines. Format code with:
```bash
uv run black src/
```

### Adding Dependencies

Add a new dependency:
```bash
uv add package-name
```

Add a development dependency:
```bash
uv add --dev package-name
```

## Architecture

### Models
- **User**: Represents authenticated users
- **Invoice**: Stores invoice data and status
- **FBRResponse**: Audit trail of FBR API interactions

### Services
- **InvoiceService**: Invoice CRUD operations
- **ValidationService**: Invoice validation logic
- **PostingService**: FBR posting operations
- **FBRClient**: FBR API communication
- **AuditService**: Audit logging

### Middleware
- **AuthMiddleware**: JWT token verification and user context

## Security

- All endpoints require JWT authentication (except health check)
- User data isolation enforced at database level
- FBR credentials stored securely in environment variables
- SQL injection prevention through SQLModel ORM
- Input validation using Pydantic schemas

## Performance

- Connection pooling for database
- Async operations where applicable
- Response time target: <3 seconds p95

## License

MIT License

## Support

For issues and questions, please refer to the project documentation or contact the development team.
