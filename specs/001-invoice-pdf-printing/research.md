# Research: Invoice PDF Printing with FBR Compliance

**Feature**: 001-invoice-pdf-printing  
**Date**: 2026-04-14  
**Purpose**: Resolve technical unknowns before implementation

## 1. PDF Generation Library Evaluation

### Question
Which Python PDF library best supports our requirements (Unicode, QR codes, precise layout control)?

### Options Evaluated

| Library | Unicode Support | Layout Control | QR Integration | Performance | Maturity |
|---------|----------------|----------------|----------------|-------------|----------|
| ReportLab | ✅ Excellent | ✅ Excellent | ✅ Easy | ✅ Fast | ✅ Mature |
| WeasyPrint | ✅ Good | ⚠️ CSS-based | ⚠️ Manual | ⚠️ Slower | ✅ Mature |
| FPDF | ⚠️ Limited | ⚠️ Basic | ⚠️ Manual | ✅ Fast | ⚠️ Older |
| pdfkit | ✅ Good | ⚠️ HTML-based | ⚠️ Manual | ❌ Slow | ⚠️ Wrapper |

### Decision: ReportLab

**Rationale**:
- **Precise Layout Control**: ReportLab provides pixel-perfect positioning for FBR logo and QR code placement (required 1.0x1.0 inch dimensions)
- **Unicode Support**: Excellent support for Urdu and Arabic characters with proper font registration
- **Performance**: Generates single-page PDFs in <1 second, suitable for our <3 second target
- **QR Code Integration**: Easy to embed PIL/Pillow images (QR codes) directly into canvas
- **Table Support**: Built-in Table and TableStyle classes for invoice line items
- **Production Ready**: Used by thousands of production systems, well-documented, actively maintained

**Alternatives Considered**:
- **WeasyPrint**: CSS-based layout is less precise for exact positioning requirements
- **pdfkit**: HTML-to-PDF conversion adds overhead, slower performance
- **FPDF**: Limited Unicode support, would require significant workarounds

**Implementation Approach**:
```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle

def generate_invoice_pdf(invoice_data, fbr_response):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    # Add content, logo, QR code
    c.save()
    return buffer.getvalue()
```

**Dependencies to Add**:
- `reportlab>=4.0.0`

---

## 2. QR Code Generation Specifications

### Question
How to generate QR Code Version 2.0 (25x25 modules) at exactly 1.0x1.0 inch in PDF?

### Research Findings

**QR Code Version 2.0 Specifications**:
- Version 2: 25x25 modules (confirmed in FBR spec)
- Module size calculation: 1.0 inch / 25 modules = 0.04 inch per module
- At 72 DPI (PDF standard): 72 pixels / 25 = 2.88 pixels per module
- At 300 DPI (print quality): 300 pixels / 25 = 12 pixels per module

**Library Selection**: `qrcode` with PIL backend

**Rationale**:
- Supports explicit version specification
- Generates PIL Image objects (compatible with ReportLab)
- Configurable box_size for precise dimensions
- Mature, widely used library

**Implementation Approach**:
```python
import qrcode
from PIL import Image

def generate_qr_code(usin: str, size_inches: float = 1.0) -> Image:
    """Generate QR code Version 2.0 at specified size."""
    qr = qrcode.QRCode(
        version=2,  # 25x25 modules
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=12,  # 12 pixels per module = 300 DPI quality
        border=0,  # No border (we'll add our own spacing)
    )
    qr.add_data(usin)
    qr.make(fit=False)  # Don't auto-adjust version
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Verify size: 25 modules * 12 pixels = 300 pixels = 1 inch at 300 DPI
    return img

# In ReportLab canvas:
qr_img = generate_qr_code(usin)
c.drawImage(qr_img, x, y, width=1*inch, height=1*inch)
```

**Validation**:
- QR code will be exactly 1.0x1.0 inch when rendered in PDF
- Version 2.0 ensures 25x25 module structure as required by FBR
- Scannable at standard printer resolutions (300 DPI)

**Dependencies to Add**:
- `qrcode>=7.4.2`
- `Pillow>=10.0.0` (for image handling)

---

## 3. FBR Logo Asset Acquisition

### Question
Where to obtain the official FBR Digital Invoicing System logo?

### Research Findings

**Official Sources**:
1. FBR Technical Documentation (TECHNICAL.txt) mentions "FBR Digital Invoicing System image" but doesn't provide the actual file
2. FBR official website: https://fbr.gov.pk/
3. Digital Invoicing portal (if accessible)

**Acquisition Plan**:

**Option A: Request from FBR** (Recommended)
- Contact FBR technical support for official logo file
- Request high-resolution PNG or SVG format
- Ensure usage rights for invoice printing

**Option B: Extract from FBR Portal**
- If user has access to FBR digital invoicing portal
- Download logo from portal interface
- Verify it's the official "Digital Invoicing System" logo

**Option C: Placeholder Approach** (Development)
- Use placeholder text "FBR Digital Invoicing System" during development
- Replace with official logo before production deployment
- Document logo requirements clearly

**Storage Location**:
```
backend/src/assets/
└── fbr_logo.png  (or fbr_logo.svg)
```

**Specifications**:
- **Format**: PNG (preferred) or SVG
- **Resolution**: Minimum 300 DPI for print quality
- **Dimensions**: Flexible (will be scaled to fit invoice layout)
- **Color**: Official FBR branding colors

**Implementation Note**:
```python
from pathlib import Path

LOGO_PATH = Path(__file__).parent.parent / "assets" / "fbr_logo.png"

def load_fbr_logo() -> Image:
    if not LOGO_PATH.exists():
        raise FileNotFoundError("FBR logo not found. Please add fbr_logo.png to backend/src/assets/")
    return Image.open(LOGO_PATH)
```

**Action Required**: User must obtain official FBR logo before production deployment.

---

## 4. Unicode Font Handling

### Question
Which fonts support Urdu/Arabic characters in ReportLab PDFs?

### Research Findings

**Font Requirements**:
- Must support Arabic script (used for Urdu)
- Must support Latin characters (for English text)
- Must be embeddable in PDFs
- Must be freely licensed for commercial use

**Recommended Font: Noto Sans Arabic**

**Rationale**:
- **Comprehensive Coverage**: Supports Arabic, Urdu, Persian, and Latin scripts
- **Free License**: Open Font License (OFL), free for commercial use
- **High Quality**: Designed by Google for universal coverage
- **ReportLab Compatible**: TrueType format works with ReportLab's TTFont

**Alternative: Arial Unicode MS**
- Broader coverage but requires Windows license
- Not freely distributable
- Larger file size

**Implementation Approach**:

1. **Download Font**:
```bash
# Download Noto Sans Arabic from Google Fonts
wget https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic-Regular.ttf
```

2. **Register Font in ReportLab**:
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

FONT_PATH = Path(__file__).parent.parent / "assets" / "NotoSansArabic-Regular.ttf"

def register_fonts():
    """Register Unicode fonts for PDF generation."""
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont('NotoSansArabic', str(FONT_PATH)))
    else:
        # Fallback to Helvetica (limited Unicode support)
        pass

# Use in canvas:
c.setFont('NotoSansArabic', 10)
c.drawString(x, y, "نص عربي")  # Arabic text
```

3. **Font Storage**:
```
backend/src/assets/
├── fbr_logo.png
└── NotoSansArabic-Regular.ttf
```

**Testing Strategy**:
- Test with sample Urdu buyer/seller names
- Test with Arabic product descriptions
- Verify rendering in PDF readers (Adobe, Chrome, Firefox)

**Fallback Handling**:
- If font file missing, log warning and use Helvetica
- Document font requirement in setup instructions

---

## 5. PDF Response Patterns

### Question
Best practice for serving PDFs in FastAPI (streaming vs in-memory, content-disposition headers)?

### Research Findings

**FastAPI PDF Response Pattern**:

**Recommended Approach: In-Memory with StreamingResponse**

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO

@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: UUID, current_user: User = Depends(get_current_user)):
    # Generate PDF
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice)
    
    # Create in-memory buffer
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    
    # Return as streaming response
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Invoice-{invoice.invoice_number}-{invoice.scheduled_date}.pdf"'
        }
    )
```

**Rationale**:
- **StreamingResponse**: Efficient for binary data, supports large files
- **In-Memory Generation**: PDFs are small (<1MB typically), no need for disk I/O
- **Content-Disposition**: `attachment` triggers download, `inline` opens in browser
- **Filename**: Descriptive format with invoice number and date

**Headers Explained**:
- `media_type="application/pdf"`: Tells browser it's a PDF
- `Content-Disposition: attachment`: Forces download (vs inline display)
- `filename="..."`: Suggests filename for download

**Browser Compatibility**:
- Chrome: Downloads or opens based on Content-Disposition
- Firefox: Same behavior
- Safari: Same behavior
- Edge: Same behavior

**Alternative for Preview** (P3 feature):
```python
# For "Open in New Tab" option
headers={
    "Content-Disposition": f'inline; filename="Invoice-{invoice.invoice_number}.pdf"'
}
```

**Error Handling**:
```python
try:
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice)
except Exception as e:
    logger.error(f"PDF generation failed: {e}")
    raise HTTPException(status_code=500, detail="PDF generation failed")
```

---

## 6. Batch PDF Memory Management

### Question
How to efficiently generate 50-invoice PDFs without memory issues?

### Research Findings

**Memory Considerations**:
- Single invoice PDF: ~100-500 KB
- 50 invoices: ~5-25 MB total
- ReportLab canvas: Accumulates in memory before save
- Python memory overhead: ~2-3x PDF size during generation

**Recommended Approach: Sequential Generation with Single Canvas**

```python
def generate_batch_pdf(invoices: list[AutomationInvoice]) -> bytes:
    """Generate batch PDF with memory-efficient approach."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    for idx, invoice in enumerate(invoices):
        # Generate one invoice page
        _create_invoice_page(c, invoice, page_num=idx+1)
        
        # Add page break (except for last invoice)
        if idx < len(invoices) - 1:
            c.showPage()  # Finalize current page, start new one
    
    # Save all pages at once
    c.save()
    return buffer.getvalue()
```

**Key Techniques**:
1. **Single Canvas**: One canvas object for all pages (efficient)
2. **showPage()**: Finalizes current page, starts new one (manages memory)
3. **Sequential Processing**: Process invoices one at a time (no parallel overhead)
4. **No Intermediate Storage**: Generate directly to BytesIO buffer

**Memory Profile**:
- Peak memory: ~50-100 MB for 50 invoices (acceptable)
- No disk I/O required
- Garbage collection handles cleanup after response sent

**Performance Optimization**:
- Load logo and font once (reuse across all pages)
- Pre-calculate common elements (headers, footers)
- Use ReportLab's built-in caching

**Alternative Approach** (if memory issues occur):
```python
# Generate PDFs separately and merge (higher overhead)
from PyPDF2 import PdfMerger

merger = PdfMerger()
for invoice in invoices:
    pdf_bytes = generate_invoice_pdf(invoice)
    merger.append(BytesIO(pdf_bytes))

output = BytesIO()
merger.write(output)
return output.getvalue()
```

**Recommendation**: Start with single-canvas approach. Only use merger if memory issues observed in testing.

**Testing Strategy**:
- Test with 50 invoices containing maximum line items (50+ items each)
- Monitor memory usage during generation
- Test on production-like server specs
- Implement timeout (e.g., 180 seconds for batch)

---

## Summary of Decisions

| Research Area | Decision | Dependencies |
|--------------|----------|--------------|
| PDF Library | ReportLab | reportlab>=4.0.0 |
| QR Code | qrcode with PIL | qrcode>=7.4.2, Pillow>=10.0.0 |
| FBR Logo | User must provide (placeholder for dev) | N/A |
| Unicode Font | Noto Sans Arabic | Font file in assets/ |
| PDF Response | StreamingResponse with attachment header | Built-in FastAPI |
| Batch Memory | Single canvas, sequential generation | N/A |

## Next Steps

1. Add dependencies to `backend/pyproject.toml`
2. Download Noto Sans Arabic font to `backend/src/assets/`
3. Create placeholder for FBR logo (document requirement)
4. Proceed to Phase 1: Data model and API contracts
