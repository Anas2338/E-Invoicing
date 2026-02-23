<!-- SYNC IMPACT REPORT:
Version change: 1.0.0 -> 1.1.0
Modified principles: Architectural Constraints (Database provider changed from Supabase to Neon)
Added sections: None
Removed sections: None
Templates requiring updates:
- .specify/templates/plan-template.md ⚠ pending review
- .specify/templates/spec-template.md ⚠ pending review
- .specify/templates/tasks-template.md ⚠ pending review
- .specify/templates/commands/*.md ⚠ pending review
- README.md ⚠ pending review
Follow-up TODOs: Review all templates and docs for Supabase references
-->

# FBR Sale & Purchase Invoice Integration Portal Constitution

## Core Principles

### Compliance-First Development
All development must strictly follow FBR technical specifications. Every feature, model, and validation rule must be derived directly from official FBR documentation and technical specifications. No assumptions or interpretations outside the official spec are permitted.

### Security by Design
Security measures must be implemented from the ground up in every component and feature. No feature may be developed without considering access control, input validation, and data protection requirements. All security controls must be validated before feature completion.

### Spec-Driven Implementation
All models, APIs, and validations must be derived directly from FBR specifications. Generated models must fail if any spec mismatch occurs. No hardcoded field assumptions may exist outside of the official FBR specification. The FBR spec file serves as the single source of truth for all field structures, data types, validation logic, and error codes.

### Data Integrity and Auditability
Every FBR interaction must be logged and traceable for compliance and debugging purposes. Complete audit trails must be maintained for all invoice operations, including state transitions, API calls, and user actions. All FBR responses must be stored unmodified for audit purposes.

### Environment Isolation
Sandbox and Production environments must never mix or share configuration. Strict separation must be maintained between testing and production systems. Configuration variables must be explicitly separated to prevent accidental cross-environment contamination.

## Security Standards

- JWT-based authentication via Better Auth must be implemented across all protected endpoints
- Token verification middleware is mandatory in all FastAPI routes
- Row-level data isolation must be enforced in database queries to ensure users can access only their own data
- Sensitive data must be encrypted at rest where applicable
- Rate limiting must be implemented for all invoice submission endpoints
- Input sanitization must be applied to all form fields to prevent injection attacks
- Protection against replay attacks must be implemented for invoice posting operations
- Authentication required for every endpoint (no public routes allowed)
- JWT verification required at backend for all protected routes
- Authorization rule: users can access ONLY their own data (user_id isolation)

## Architectural Constraints

- Frontend: Next.js 16+ App Router only
- Backend: FastAPI only
- ORM: SQLModel only
- Database: Neon PostgreSQL only
- Authentication provider: Better Auth only
- No business logic inside frontend components
- All FBR communication must go through backend service layer
- Sandbox and Production must use separate configuration variables
- No hardcoded secrets or tokens; use .env and documentation

## Data Rules

- Invoice payloads stored as structured JSON + normalized metadata
- FBR responses stored unmodified for audit
- Invoice logs must record endpoint, environment, and status
- Deleting invoices is prohibited; only status transitions allowed
- Every invoice state transition must be persisted (draft → validated → posted → failed)
- All monetary values must use precise numeric handling (no float rounding)
- All external API calls must include structured logging (request, response, timestamp)

## API Design Rules

- RESTful conventions required for all endpoints
- All endpoints must be versionable using /api/v1/ pattern
- Bulk invoice posting must support transactional integrity
- Validation endpoint must NOT post invoices
- Posting endpoint must only accept validated invoices
- All API contracts must be schema-based and version-controlled
- Error handling must preserve original FBR response payloads

## Environment Workflow Rules

- New users must operate in Sandbox first before accessing Production
- Production posting only allowed after system approval flag is set
- Environment must be explicitly selected per invoice to prevent accidental production posting
- Clear distinction between sandbox and production data flows required

## Non-Functional Standards

- All endpoints must respond in < 3 seconds under normal load
- System must support concurrent invoice submissions without conflicts
- All validations must align with FBR validation rules and error codes
- All invoice fields must match FBR specification exactly (names, types, formats)

## Development Guidelines

- Prefer the smallest viable diff; do not refactor unrelated code
- Cite existing code with code references (start:end:path); propose new code in fenced blocks
- Keep reasoning private; output only decisions, artifacts, and justifications
- All changes must be small, testable, and reference code precisely
- Every user input must be recorded verbatim in a Prompt History Record (PHR)
- Architectural Decision Records (ADRs) must be created for significant decisions

## Governance

This constitution supersedes all other development practices and standards within the project. All team members must comply with these principles. Any deviation from these principles requires formal amendment to this constitution with proper justification and approval. All pull requests and code reviews must verify compliance with these principles. All architectural decisions that meet significance criteria (long-term consequences, multiple viable options, cross-cutting influence) must be documented in ADRs. Use standard development workflow with proper testing, validation, and approval processes.

**Version**: 1.1.0 | **Ratified**: 2026-01-29 | **Last Amended**: 2026-02-22