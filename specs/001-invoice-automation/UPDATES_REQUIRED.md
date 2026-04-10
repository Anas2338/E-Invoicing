# Required Updates for In-Memory Excel Parsing

**Date**: 2026-04-06  
**Reason**: Architecture change - Excel files parsed in memory, no file storage

## Existing Artifacts Requiring Updates

### 1. research.md

**Section to Update**: "3. File Storage Strategy"

**Current State**: Documents local filesystem storage under `uploads/{user_id}/`

**Required Changes**:
- Update Decision to: "In-memory parsing with BytesIO (no file storage)"
- Update Rationale to emphasize: memory efficiency, no filesystem dependencies, simpler deployment
- Remove implementation notes about directory creation and file paths
- Update alternatives to note file storage was considered but rejected for simplicity
- Add note about export functionality (generate Excel from database on demand)

**Impact**: Medium - affects understanding of how Excel files are handled

---

### 2. data-model.md

**Section to Update**: "3. ExcelUploadSession"

**Current State**: `file_path` field is required (non-nullable)

**Required Changes**:
- Make `file_path: Optional[str] = Field(default=None, max_length=500)`
- Update description: "File path (optional, NULL for in-memory parsing)"
- Update Storage Estimates section to remove file storage calculations
- Add note in Overview about in-memory parsing architecture

**Migration Required**: Yes - Alembic migration to alter column to nullable

```python
# New migration needed
def upgrade():
    op.alter_column('excel_upload_session', 'file_path',
                   existing_type=sa.String(500),
                   nullable=True)
```

**Impact**: High - database schema change required

---

### 3. quickstart.md

**Sections to Update**: 
- "2. Create Uploads Directory" (remove entirely)
- "Testing the Automation Flow" (update file references)
- "Troubleshooting" (remove file-related issues)

**Required Changes**:
- Remove step 2 (Create Uploads Directory) from Installation section
- Remove `.gitignore` addition for uploads/
- Update "Download Updated Excel" to "Export to Excel" (generates from database)
- Remove troubleshooting section "Excel File Not Updated"
- Remove "File Storage" section from Performance Tuning
- Update "Large File Upload Timeout" to focus on memory constraints instead

**Impact**: Medium - affects developer setup and testing procedures

---

### 4. contracts/*.yaml

**Files to Review**:
- excel-upload.yaml
- automation-dashboard.yaml
- invoice-retry.yaml

**Required Changes**:
- Verify no `file_path` fields in request/response schemas
- Update `ExcelUploadResponse` if it includes file_path
- Update dashboard download endpoint to be "export" instead of "download"
- Ensure all responses reference database-stored data only

**Impact**: Low - likely no changes needed, but verification required

---

### 5. Backend Implementation Files

**Files Requiring Updates**:

#### backend/src/models/excel_upload_session.py
- Make `file_path` optional: `file_path: Optional[str] = Field(default=None, max_length=500)`
- Update docstring to note in-memory parsing

#### backend/src/utils/excel_validator.py
- Add support for BytesIO input in addition to file paths
- Update method signatures: `validate_excel_structure(file_source: str | BytesIO)`
- Handle both file path and BytesIO in validation methods

#### backend/src/services/excel_service.py
- Update `parse_excel_file()` to accept BytesIO
- Remove or deprecate `update_excel_with_status()` method
- Add `generate_excel_from_database()` method for export functionality

#### backend/src/api/v1/automation/excel.py
- Remove file storage operations (`file_storage.save_uploaded_file()`)
- Parse Excel directly from `file_content` (BytesIO)
- Pass `None` for `file_path` when creating upload session
- Remove file cleanup operations

#### backend/src/utils/file_storage.py
- Mark as deprecated or remove entirely
- If kept, document that it's not used for Excel uploads

**Impact**: High - core implementation changes

---

### 6. Database Migrations

**New Migration Required**: Make `excel_upload_session.file_path` nullable

**File**: `backend/alembic/versions/{timestamp}_make_file_path_optional.py`

```python
"""Make file_path optional in excel_upload_session

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

revision = '{generated_id}'
down_revision = '{previous_revision}'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column('excel_upload_session', 'file_path',
                   existing_type=sa.String(500),
                   nullable=True)

def downgrade() -> None:
    # Note: This will fail if any NULL values exist
    op.alter_column('excel_upload_session', 'file_path',
                   existing_type=sa.String(500),
                   nullable=False)
```

**Impact**: High - database schema change

---

## Summary of Changes

| Artifact | Change Type | Priority | Estimated Effort |
|----------|-------------|----------|------------------|
| research.md | Documentation update | Medium | 15 min |
| data-model.md | Documentation + schema | High | 30 min |
| quickstart.md | Documentation update | Medium | 20 min |
| contracts/*.yaml | Verification | Low | 10 min |
| Backend models | Code change | High | 15 min |
| Backend services | Code change | High | 1 hour |
| Backend API | Code change | High | 45 min |
| Backend utils | Code change | Medium | 30 min |
| Database migration | Schema change | High | 15 min |

**Total Estimated Effort**: ~4 hours

---

## Testing Requirements

After implementing changes:

1. **Unit Tests**: Update tests for in-memory parsing
   - `test_excel_service.py` - test BytesIO parsing
   - `test_excel_validator.py` - test BytesIO validation

2. **Integration Tests**: Verify end-to-end flow
   - Upload Excel file (in-memory)
   - Verify data stored in database
   - Verify no files created on disk
   - Export Excel from database

3. **Migration Tests**: Verify schema change
   - Run migration on test database
   - Verify existing records still accessible
   - Verify new uploads work with NULL file_path

---

## Rollout Plan

1. Create database migration (make file_path nullable)
2. Update backend code (models, services, API)
3. Run migration on development database
4. Test end-to-end flow
5. Update documentation (research.md, data-model.md, quickstart.md)
6. Review and update contracts if needed
7. Deploy to staging for testing
8. Deploy to production

**Note**: This is a backward-compatible change. Existing records with file_path values will continue to work. New uploads will have NULL file_path.
