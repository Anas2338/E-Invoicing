# Quickstart: Invoice PDF Printing Feature

**Feature**: 001-invoice-pdf-printing  
**Date**: 2026-04-14  
**For**: Developers implementing the PDF printing feature

## Overview

This guide helps you set up and implement the invoice PDF printing feature with FBR compliance. The feature generates on-demand PDFs for submitted invoices with logo and QR code elements.

## Prerequisites

- Python 3.11+ installed
- Backend development environment set up
- Access to existing automation invoice system
- Basic understanding of FastAPI and ReportLab

## Setup Steps

### 1. Install Dependencies

Add the following to `backend/pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "reportlab>=4.0.0",
    "qrcode>=7.4.2",
    "Pillow>=10.0.0",
]
```

Install dependencies:

```bash
cd backend
uv sync
```

### 2. Download Required Assets

#### Noto Sans Arabic Font (for Unicode support)

```bash
# Create assets directory
mkdir -p backend/src/assets

# Download font
cd backend/src/assets
wget https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic-Regular.ttf
```

Or download manually from [Google Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+Arabic) and place in `backend/src/assets/`.

#### FBR Digital Invoicing Logo

**Action Required**: Obtain the official FBR Digital Invoicing System logo.

**Options**:
1. Request from FBR technical support
2. Download from FBR digital invoicing portal (if accessible)
3. Use placeholder during development

**Placement**: Save as `backend/src/assets/fbr_logo.png` (PNG format, 300+ DPI recommended)

**Placeholder for Development**:
```bash
# Create a simple placeholder (optional)
cd backend/src/assets
# Use any placeholder image or create text-based placeholder in code
```

### 3. Verify Assets

Check that assets are in place:

```bash
ls -la backend/src/assets/
# Should show:
# - NotoSansArabic-Regular.ttf
# - fbr_logo.png (or placeholder)
```

## Implementation Checklist

### Backend Implementation

- [ ] **Create PDF Service** (`backend/src/services/pdf_service.py`)
  - [ ] Implement `generate_invoice_pdf(invoice)` method
  - [ ] Implement `generate_batch_pdf(invoices)` method
  - [ ] Add QR code generation helper
  - [ ] Add logo loading helper
  - [ ] Register Unicode font
  - [ ] Implement invoice page rendering
  - [ ] Add error handling

- [ ] **Create PDF API Endpoints** (`backend/src/api/v1/automation/pdf.py`)
  - [ ] Implement `GET /invoices/{invoice_id}/pdf`
  - [ ] Implement `POST /invoices/batch-pdf`
  - [ ] Add authentication middleware
  - [ ] Add authorization checks (user ownership)
  - [ ] Add validation (status, USIN presence)
  - [ ] Add error responses

- [ ] **Register Routes** (`backend/src/api/v1/automation/__init__.py`)
  - [ ] Import pdf router
  - [ ] Include in automation router

- [ ] **Write Tests**
  - [ ] Unit tests for PDF service
  - [ ] Integration tests for API endpoints
  - [ ] Test Unicode character handling
  - [ ] Test batch generation (50 invoices)
  - [ ] Test error scenarios

### Frontend Implementation

- [ ] **Update API Service** (`frontend/src/services/automationApi.ts`)
  - [ ] Add `printInvoice(invoiceId)` function
  - [ ] Add `printBatchInvoices(invoiceIds)` function
  - [ ] Handle blob responses
  - [ ] Add error handling

- [ ] **Create Print Button Component** (`frontend/src/components/automation/PrintInvoiceButton.tsx`)
  - [ ] Implement button with loading state
  - [ ] Handle PDF download
  - [ ] Show error messages
  - [ ] Disable for non-submitted invoices

- [ ] **Update Invoice Detail Page** (`frontend/src/app/(protected)/automation/dashboard/page.tsx`)
  - [ ] Add print button to invoice detail view
  - [ ] Handle print action
  - [ ] Show loading state

- [ ] **Update Invoice Table** (`frontend/src/components/automation/InvoiceTable.tsx`)
  - [ ] Add checkbox selection
  - [ ] Add "Print Selected" button
  - [ ] Validate batch size (max 50)
  - [ ] Handle batch print action

- [ ] **Write Tests**
  - [ ] Component tests for print button
  - [ ] Test loading states
  - [ ] Test error handling
  - [ ] Test batch selection

## Development Workflow

### 1. Start with Backend

**Create PDF Service First**:

```python
# backend/src/services/pdf_service.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO
import qrcode

class PDFService:
    def generate_invoice_pdf(self, invoice: AutomationInvoice) -> bytes:
        """Generate PDF for single invoice."""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # TODO: Implement invoice rendering
        
        c.save()
        return buffer.getvalue()
```

**Test Locally**:

```python
# Test script
from backend.src.services.pdf_service import PDFService
from backend.src.models.automation_invoice import AutomationInvoice

# Load test invoice from database
invoice = session.get(AutomationInvoice, "test-uuid")

# Generate PDF
pdf_service = PDFService()
pdf_bytes = pdf_service.generate_invoice_pdf(invoice)

# Save to file for inspection
with open("test_invoice.pdf", "wb") as f:
    f.write(pdf_bytes)
```

### 2. Create API Endpoints

```python
# backend/src/api/v1/automation/pdf.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter()

@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # TODO: Implement endpoint
    pass
```

**Test with curl**:

```bash
# Get JWT token first
TOKEN="your-jwt-token"

# Test single invoice PDF
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/automation/invoices/{invoice-id}/pdf \
     --output test.pdf

# Test batch PDF
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"invoice_ids": ["uuid1", "uuid2"]}' \
     http://localhost:8000/api/v1/automation/invoices/batch-pdf \
     --output batch.pdf
```

### 3. Implement Frontend

**Add API Functions**:

```typescript
// frontend/src/services/automationApi.ts
export const printInvoice = async (invoiceId: string): Promise<Blob> => {
  const response = await fetch(`/api/v1/automation/invoices/${invoiceId}/pdf`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to generate PDF');
  }
  
  return response.blob();
};
```

**Create Print Button**:

```tsx
// frontend/src/components/automation/PrintInvoiceButton.tsx
'use client';

import { useState } from 'react';
import { printInvoice } from '@/services/automationApi';

export function PrintInvoiceButton({ invoiceId, invoiceNumber, disabled }) {
  const [loading, setLoading] = useState(false);
  
  const handlePrint = async () => {
    setLoading(true);
    try {
      const blob = await printInvoice(invoiceId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice-${invoiceNumber}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Print failed:', error);
      // Show error toast
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <button onClick={handlePrint} disabled={disabled || loading}>
      {loading ? 'Generating...' : 'Print Invoice'}
    </button>
  );
}
```

## Testing Guide

### Manual Testing

1. **Single Invoice PDF**:
   - Navigate to automation dashboard
   - Click on a submitted invoice
   - Click "Print Invoice" button
   - Verify PDF downloads with correct filename
   - Open PDF and verify:
     - All invoice data present
     - FBR logo visible
     - QR code present and scannable
     - Unicode characters render correctly

2. **Batch PDF**:
   - Navigate to invoice list
   - Select 3-5 submitted invoices
   - Click "Print Selected"
   - Verify batch PDF downloads
   - Open PDF and verify:
     - All invoices present in selection order
     - Page breaks between invoices
     - Each invoice has logo and QR code

3. **Error Cases**:
   - Try printing non-submitted invoice (should be disabled)
   - Try batch with >50 invoices (should show error)
   - Try printing invoice without USIN (should show error)

### Automated Testing

```bash
# Backend tests
cd backend
pytest tests/unit/test_pdf_service.py -v
pytest tests/integration/test_pdf_api.py -v

# Frontend tests
cd frontend
npm test -- PrintInvoiceButton.test.tsx
```

## Troubleshooting

### Common Issues

**Issue**: "FBR logo file not found"
- **Solution**: Ensure `backend/src/assets/fbr_logo.png` exists
- **Workaround**: Use placeholder or text-based logo temporarily

**Issue**: "Font not found" or Unicode characters not rendering
- **Solution**: Verify `NotoSansArabic-Regular.ttf` is in `backend/src/assets/`
- **Check**: Font registration code in PDF service

**Issue**: QR code not scannable
- **Solution**: Verify QR code version is 2.0 and size is 1.0x1.0 inch
- **Test**: Use multiple QR code readers (phone camera, dedicated apps)

**Issue**: Batch PDF generation timeout
- **Solution**: Check batch size (max 50), increase timeout if needed
- **Monitor**: Memory usage during generation
- **Note**: Default timeout is 180 seconds for batch operations

**Issue**: PDF layout broken
- **Solution**: Check A4 page size settings, verify coordinate calculations
- **Test**: Print PDF and measure physical dimensions

**Issue**: "Only submitted invoices can be printed" error
- **Solution**: Verify invoice status is 'submitted' in database
- **Check**: Invoice must have valid FBR response with USIN

**Issue**: Long product descriptions causing layout issues
- **Solution**: Product descriptions are automatically truncated to 100 characters
- **Note**: Full description still available in invoice data

**Issue**: Authorization errors when printing
- **Solution**: Verify JWT token is valid and user owns the invoice
- **Check**: User ID in token matches invoice.user_id

**Issue**: Batch print fails with "exceeds maximum limit"
- **Solution**: Reduce selection to 50 or fewer invoices
- **Workaround**: Split into multiple batches

## Performance Optimization

### Tips for Fast PDF Generation

1. **Load assets once**: Cache logo and font at service initialization
2. **Reuse canvas objects**: Don't recreate for each invoice in batch
3. **Optimize table rendering**: Use ReportLab's Table class efficiently
4. **Monitor memory**: Profile batch generation with 50 invoices

### Expected Performance

- Single invoice: <3 seconds
- Batch (10 invoices): <15 seconds
- Batch (50 invoices): <150 seconds

## Next Steps

After completing implementation:

1. **Run `/sp.tasks`** to generate detailed implementation tasks
2. **Execute tasks** in priority order (P1 → P2 → P3)
3. **Test thoroughly** with real invoice data
4. **Obtain FBR logo** before production deployment
5. **Deploy** to staging for user acceptance testing

## Resources

- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [QR Code Library](https://github.com/lincolnloop/python-qrcode)
- [FastAPI Responses](https://fastapi.tiangolo.com/advanced/custom-response/)
- [FBR Technical Specification](../../../TECHNICAL.txt)

## Support

For questions or issues:
- Review `specs/001-invoice-pdf-printing/plan.md`
- Check `specs/001-invoice-pdf-printing/research.md` for technical decisions
- Refer to API contracts in `specs/001-invoice-pdf-printing/contracts/`
