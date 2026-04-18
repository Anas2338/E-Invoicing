# Implementation Plan: User Approval System

**Branch**: `002-user-approval-system` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-user-approval-system/spec.md`

**Note**: This is a retroactive plan documenting the architectural decisions for the already-implemented user approval system.

## Summary

Implement an admin approval workflow for new user registrations to prevent unauthorized access to the FBR invoice integration system. The solution adds account status tracking (pending/approved/rejected) to the existing user model, creates admin-only API endpoints for approval management, blocks login for non-approved users, and provides email notifications for registration and approval events. The implementation leverages the existing JWT authentication system and extends it with admin role checking, while maintaining backward compatibility by auto-approving all existing users during migration.

## Technical Context

**Language/Version**: Python 3.13+ (backend), TypeScript/JavaScript (frontend)  
**Primary Dependencies**: FastAPI, SQLModel, SQLAlchemy, Alembic (backend); Next.js 16+, React (frontend)  
**Storage**: Neon PostgreSQL (cloud-hosted)  
**Testing**: pytest (backend), Jest/React Testing Library (frontend)  
**Target Platform**: Web application (Linux server backend, browser frontend)  
**Project Type**: Web (separate backend/frontend)  
**Performance Goals**: <2s admin panel load time, <2s approval/rejection action completion  
**Constraints**: Must not disrupt existing user authentication flow, must maintain backward compatibility  
**Scale/Scope**: 4 existing users (auto-approved), expected <100 pending users at any time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Security Standards
- ✓ **JWT-based authentication**: Extends existing Better Auth JWT system with admin role checking
- ✓ **Token verification**: All admin endpoints require JWT verification via existing middleware
- ✓ **Row-level isolation**: Admin endpoints filter by user_id where applicable; approval actions are admin-only
- ✓ **Input sanitization**: Email and name fields sanitized during registration
- ✓ **Authentication required**: All endpoints protected (registration is public but creates pending accounts)
- ✓ **Authorization**: Admin endpoints verify `approval_flags.is_admin = true` before allowing access

### Architectural Constraints
- ✓ **Frontend**: Next.js 16+ App Router (admin panel at `/admin/users`)
- ✓ **Backend**: FastAPI (new admin router at `/api/v1/admin`)
- ✓ **ORM**: SQLModel (extended User model with approval fields)
- ✓ **Database**: Neon PostgreSQL (migration adds approval columns)
- ✓ **Authentication**: Better Auth (no changes to auth provider)
- ✓ **No business logic in frontend**: Admin panel calls backend API for all operations
- ✓ **No hardcoded secrets**: Email configuration uses .env variables

### Data Rules
- ✓ **State transitions persisted**: Account status changes (pending → approved/rejected) are logged
- ✓ **Audit trail**: Records admin_id, timestamp, and rejection reason for all approval actions
- ✓ **No deletion of audit data**: Approval/rejection records are permanent

### API Design Rules
- ✓ **RESTful conventions**: Admin endpoints follow REST patterns (GET for list, POST for actions)
- ✓ **Versioned endpoints**: All endpoints use `/api/v1/` pattern
- ✓ **Schema-based contracts**: Pydantic models define request/response schemas

### Development Guidelines
- ✓ **Small, testable changes**: Feature adds minimal new code, extends existing models
- ✓ **No unrelated refactoring**: Only touches user model, auth endpoints, and adds admin endpoints
- ✓ **Backward compatibility**: Existing users auto-approved during migration

**GATE STATUS**: ✓ PASSED - All constitution principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/002-user-approval-system/
├── plan.md              # This file (implementation plan)
├── spec.md              # Feature specification
├── research.md          # Architectural decisions and research
├── data-model.md        # Database schema and entity relationships
├── quickstart.md        # Setup and usage guide
├── contracts/           # API contracts (OpenAPI schemas)
│   ├── admin-api.yaml   # Admin endpoints contract
│   └── auth-api.yaml    # Updated auth endpoints contract
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── user.py                    # Extended with approval fields
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py                # Updated login/register logic
│   │       └── admin.py               # New admin endpoints
│   ├── utils/
│   │   └── email_utils.py             # New email notification utilities
│   └── main.py                        # Added admin router
├── alembic/
│   └── versions/
│       └── a1b2c3d4e5f7_add_user_approval_fields.py  # Migration
├── run_migration.py                   # Migration utility script
├── make_admin.py                      # Admin creation utility
├── list_users.py                      # User listing utility
└── USER_APPROVAL_SETUP.md             # Setup documentation

frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── register/
│   │   │       └── page.tsx           # Updated registration flow
│   │   └── (protected)/
│   │       └── admin/
│   │           └── users/
│   │               └── page.tsx       # New admin panel
│   ├── services/
│   │   └── adminApi.ts                # New admin API client
│   └── providers/
│       └── auth-provider.tsx          # Updated signup flow
└── IMPLEMENTATION_SUMMARY.md          # Implementation documentation
```

**Structure Decision**: Web application structure with separate backend (FastAPI) and frontend (Next.js). Admin functionality added as new routes in both layers without disrupting existing structure. Database migration handled via Alembic. Utility scripts created for admin management and migration execution.

---

## Phase 0: Research & Architectural Decisions

See [research.md](./research.md) for detailed architectural decisions and alternatives considered.

## Phase 1: Design Artifacts

- **Data Model**: [data-model.md](./data-model.md) - Database schema and entity relationships
- **API Contracts**: [contracts/](./contracts/) - OpenAPI specifications for admin and auth endpoints
- **Quickstart Guide**: [quickstart.md](./quickstart.md) - Setup and usage instructions

## Phase 2: Implementation Tasks

Implementation tasks will be generated using `/sp.tasks` command and documented in [tasks.md](./tasks.md).
