"""
PDF generation service for FBR-compliant invoice printing.

Generates PDFs matching the official FBR invoice template format EXACTLY:
- Landscape wide-format (1080 x 841.68 pt)
- Helvetica fonts throughout (matching sample template)
- Three-column header: Seller | Buyer | Invoice Summary
- Full 18-column line items table with gray grid lines
- Auto-sized rows with text wrapping (top-aligned cell content)
- Multi-page with page numbers, no header on continuation pages
- Totals row with merged "Total:" label cell

All measurements match sample.pdf precisely.
"""
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Tuple
import logging

from reportlab.pdfgen import canvas as canvas_module
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from PIL import Image
import qrcode

from ..models.invoice import Invoice

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# PAGE DIMENSIONS (exact match to sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
PAGE_WIDTH = 1080.0
PAGE_HEIGHT = 841.68
PAGE_SIZE = (PAGE_WIDTH, PAGE_HEIGHT)

# ═══════════════════════════════════════════════════════════════════════
# GRID COLORS (exact match to sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
GRID_GRAY = colors.Color(0.827, 0.827, 0.827)  # RGB(211,211,211)
BLACK = colors.Color(0, 0, 0)

# ═══════════════════════════════════════════════════════════════════════
# COLUMN DEFINITIONS (exact x-positions from sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
COL_X = [
    53.0,    # Sr. No.
    86.2,    # HS Code
    140.2,   # HS Code Description
    235.4,   # Product Description
    375.4,   # Sales Type
    434.0,   # Quantity
    474.9,   # UoM
    523.5,   # Rate
    559.5,   # Sales Value
    611.2,   # Retail Price
    668.1,   # Sales Tax
    715.4,   # Extra Tax
    759.0,   # Further Tax
    814.0,   # FED
    846.9,   # ST WHT
    890.1,   # Discount
    935.9,   # SRO / Schedule No.
    1008.8,  # SRO Item Sr. No.
    1051.7,  # Right edge of last column
]

N_COLS = len(COL_X) - 1  # 18 columns

COL_WIDTHS = [COL_X[i + 1] - COL_X[i] for i in range(N_COLS)]

TABLE_LEFT = COL_X[0]    # 53.0
TABLE_RIGHT = COL_X[-1]  # 1051.7
TABLE_WIDTH = TABLE_RIGHT - TABLE_LEFT  # 998.7

# Column alignments: 'L'=left, 'R'=right, 'C'=center
COL_ALIGN = [
    'C',  # Sr. No.
    'L',  # HS Code
    'L',  # HS Code Description
    'L',  # Product Description
    'L',  # Sales Type
    'C',  # Quantity
    'C',  # UoM
    'R',  # Rate
    'R',  # Sales Value
    'R',  # Retail Price
    'R',  # Sales Tax
    'R',  # Extra Tax
    'R',  # Further Tax
    'R',  # FED
    'R',  # ST WHT
    'R',  # Discount
    'L',  # SRO / Schedule No.
    'C',  # SRO Item Sr. No.
]

# ═══════════════════════════════════════════════════════════════════════
# TABLE HEADERS (two rows for SRO columns, matching sample)
# ═══════════════════════════════════════════════════════════════════════
TABLE_HEADERS_ROW1 = [
    'Sr. No.', 'HS Code', 'HS Code Description',
    'Product Description', 'Sales Type', 'Quantity', 'UoM', 'Rate',
    'Sales Value', 'Retail Price', 'Sales Tax', 'Extra Tax ',
    'Further Tax', 'FED', 'ST WHT ', 'Discount',
    'SRO / Schedule ', 'SRO Item ',
]
TABLE_HEADERS_ROW2 = [
    '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '',
    'No.', 'Sr. No.',
]

# ═══════════════════════════════════════════════════════════════════════
# FONT SIZES (exact match to sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
COMPANY_NAME_SIZE = 16
SECTION_HEADER_SIZE = 12
FIELD_LABEL_SIZE = 10
FIELD_VALUE_SIZE = 10
TABLE_HEADER_SIZE = 8
TABLE_DATA_SIZE = 8
TOTALS_LABEL_SIZE = 10
TOTALS_VALUE_SIZE = 8
PAGE_NUM_SIZE = 10

# Line spacing for wrapped cell text
CELL_LINE_HEIGHT = 9  # 8pt font + 1pt leading
CELL_PADDING_LEFT = 2
CELL_PADDING_TOP = 2

# ═══════════════════════════════════════════════════════════════════════
# HEADER Y POSITIONS (exact match to sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
COMPANY_NAME_Y = 69.0
SECTION_HEADER_Y = 121.3   # "Seller Information" / "Buyer Information" / "Invoice Summary"
FIELD_ROW1_Y = 140.5       # Business Name / FBR Invoice No.
FIELD_ROW2_Y = 155.7       # Registration No. / Invoice Date
FIELD_ROW3_Y = 171.7       # Province / Invoice Type
FIELD_ROW4_Y = 188.9       # Invoice Type (summary only)

# Header column X positions
SELLER_LABEL_X = 54.8
SELLER_VALUE_X = 145.1
BUYER_LABEL_X = 408.1
BUYER_VALUE_X = 490.1
SUMMARY_LABEL_X = 799.1
SUMMARY_VALUE_X = 883.7

# ═══════════════════════════════════════════════════════════════════════
# CONTENT AREA BOUNDARIES
# ═══════════════════════════════════════════════════════════════════════
CONTENT_TOP = 211.3     # Table header top on first page
PAGE_TOP = 34.5         # Table top on continuation pages
PAGE_BOTTOM = 819.6     # Page number Y position
BOTTOM_MARGIN = 55.0    # Space reserved at bottom for page numbers

# ═══════════════════════════════════════════════════════════════════════
# ASSETS
# ═══════════════════════════════════════════════════════════════════════
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "NotoSansArabic-Regular.ttf"
LOGO_PATH = ASSETS_DIR / "fbr_logo.png"


class PDFService:
    """Service for generating FBR-compliant invoice PDFs matching sample template."""

    def __init__(self):
        self._fonts_registered = False
        self._unicode_font: Optional[str] = None
        self._measure_canvas: Optional[canvas_module.Canvas] = None
        self._logo_cache: Optional[Image.Image] = None

    # ── Font helpers ───────────────────────────────────────────────────

    def _register_fonts(self) -> str:
        """Register fonts; returns best available font name."""
        if self._fonts_registered and self._unicode_font:
            return self._unicode_font

        if FONT_PATH.exists():
            try:
                pdfmetrics.registerFont(TTFont('NotoSansArabic', str(FONT_PATH)))
                self._unicode_font = 'NotoSansArabic'
                self._fonts_registered = True
            except Exception:
                self._unicode_font = 'Helvetica'
                self._fonts_registered = True
        else:
            self._unicode_font = 'Helvetica'
            self._fonts_registered = True

        return self._unicode_font

    def _font(self, bold: bool = False) -> str:
        font = self._register_fonts()
        if bold and font == 'Helvetica':
            return 'Helvetica-Bold'
        return font

    # ── FBR Assets ────────────────────────────────────────────────────

    def _load_fbr_logo(self) -> Optional[Image.Image]:
        """Load FBR logo with caching. Returns None if not found."""
        if self._logo_cache is not None:
            return self._logo_cache
        if LOGO_PATH.exists():
            try:
                self._logo_cache = Image.open(LOGO_PATH)
                return self._logo_cache
            except Exception as e:
                logger.warning(f"Failed to load FBR logo: {e}")
        return None

    def _generate_qr_code(self, data: str) -> Optional[Image.Image]:
        """Generate QR code for FBR invoice number (USIN)."""
        if not data:
            return None
        try:
            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=12,
                border=0,
            )
            qr.add_data(data)
            qr.make(fit=False)
            return qr.make_image(fill_color="black", back_color="white")
        except Exception as e:
            logger.warning(f"Failed to generate QR code: {e}")
            return None

    # ── Text helpers ───────────────────────────────────────────────────

    def _get_measure_canvas(self) -> canvas_module.Canvas:
        if self._measure_canvas is None:
            self._measure_canvas = canvas_module.Canvas(BytesIO(), pagesize=PAGE_SIZE)
        return self._measure_canvas

    def _string_width(self, text: str, font_name: str, font_size: int) -> float:
        return self._get_measure_canvas().stringWidth(text, font_name, font_size)

    def _wrap_text(self, text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
        """Wrap text to fit within max_width. Returns list of lines."""
        if not text:
            return ['']

        c = self._get_measure_canvas()
        c.setFont(font_name, font_size)

        words = str(text).split(' ')
        lines = []
        current = ''

        for word in words:
            test = word if not current else current + ' ' + word
            if c.stringWidth(test, font_name, font_size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                if c.stringWidth(word, font_name, font_size) > max_width:
                    # Character-wrap long word
                    truncated = ''
                    for ch in word:
                        if c.stringWidth(truncated + ch, font_name, font_size) > max_width - 5:
                            truncated += '...'
                            break
                        truncated += ch
                    lines.append(truncated)
                else:
                    current = word
        if current:
            lines.append(current)
        return lines if lines else ['']

    @staticmethod
    def _fmt_num(value) -> str:
        """Format a numeric value for display."""
        if value is None or value == '':
            return '0.00'
        try:
            v = float(value)
            if v == int(v) and abs(v) < 1000:
                return str(int(v))
            return f"{v:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════

    def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """Generate PDF for a single invoice matching the FBR template."""
        if not invoice.items:
            raise ValueError("Invoice must have at least one item")
        items = invoice.items
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Invoice must have at least one line item")

        invoice_number = invoice.external_id
        logger.info(f"Generating PDF for invoice {invoice_number}")

        try:
            buffer = BytesIO()
            c = canvas_module.Canvas(buffer, pagesize=PAGE_SIZE)
            font = self._register_fonts()

            total_pages = self._render_all_pages(c, invoice, items, font)
            c.save()

            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info(f"Generated PDF for {invoice_number}: {len(pdf_bytes)} bytes, {total_pages} pages")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to generate PDF for invoice {invoice_number}: {e}")
            raise

    def generate_batch_pdf(self, invoices: List[Invoice]) -> bytes:
        """Generate PDF for multiple invoices. Each starts on a new page."""
        if not invoices:
            raise ValueError("No invoices provided for batch PDF generation")
        if len(invoices) > 50:
            raise ValueError(f"Batch size exceeds maximum limit of 50 invoices")

        logger.info(f"Generating batch PDF for {len(invoices)} invoices")

        try:
            buffer = BytesIO()
            c = canvas_module.Canvas(buffer, pagesize=PAGE_SIZE)
            font = self._register_fonts()

            for idx, invoice in enumerate(invoices):
                items = invoice.items
                if not items:
                    raise ValueError(f"Invoice {invoice.external_id} has no line items")
                self._render_all_pages(c, invoice, items, font)
                if idx < len(invoices) - 1:
                    c.showPage()

            c.save()
            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info(f"Generated batch PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to generate batch PDF: {e}")
            raise

    # ═══════════════════════════════════════════════════════════════════
    # MULTI-PAGE RENDERING
    # ═══════════════════════════════════════════════════════════════════

    def _render_all_pages(
        self,
        c: canvas_module.Canvas,
        invoice: Invoice,
        items: list,
        font: str
    ) -> int:
        """Render all pages. Returns total page count."""
        usin = invoice.fbr_reference_number  # FBR invoice number for QR code

        # Split items into pages
        first_page_available = PAGE_HEIGHT - CONTENT_TOP - BOTTOM_MARGIN
        cont_page_available = PAGE_HEIGHT - PAGE_TOP - BOTTOM_MARGIN

        pages = self._paginate_items(items, font, first_page_available, cont_page_available)
        total_pages = len(pages)

        # Pre-compute totals from ALL items (not just page items)
        totals_data = self._build_totals_row(items)

        for page_num, page_items in enumerate(pages, 1):
            is_first = (page_num == 1)
            y_start = CONTENT_TOP if is_first else PAGE_TOP

            if is_first:
                self._draw_first_page_header(c, invoice, font)
                # FBR logo and QR code at top-right
                self._draw_fbr_logo_and_qr(c, usin, font)

            is_last = (page_num == total_pages)

            # Compute row heights for this page's items
            row_heights = self._compute_row_heights(page_items, font)

            # Draw table
            self._draw_table_grid(
                c, page_items, row_heights, font,
                y_start=y_start, is_first=is_first, is_last=is_last,
                start_sr_no=sum(len(p) for p in pages[:page_num - 1]) + 1,
                totals_data=totals_data
            )

            # Page number (bottom-right)
            self._draw_page_number(c, page_num, total_pages, font)

            if not is_last:
                c.showPage()

        return total_pages

    def _paginate_items(
        self, items: list, font: str,
        first_page_avail: float, cont_page_avail: float
    ) -> List[list]:
        """Split items into pages based on available vertical space."""
        all_heights = self._compute_row_heights(items, font)
        totals_h = self._calc_totals_height(items, font)

        pages = []
        remaining = list(items)
        remaining_h = list(all_heights)
        is_first = True

        while remaining:
            avail = first_page_avail if is_first else cont_page_avail
            is_first = False

            used = 0
            count = 0
            for i, h in enumerate(remaining_h):
                needed = used + h
                if i == len(remaining_h) - 1:
                    needed += totals_h  # Last item needs room for totals
                if needed <= avail:
                    used += h
                    count += 1
                else:
                    if count == 0:
                        count = 1  # At least one item per page
                    break

            pages.append(remaining[:count])
            remaining = remaining[count:]
            remaining_h = remaining_h[count:]

        return pages

    # ═══════════════════════════════════════════════════════════════════
    # FIRST PAGE HEADER
    # ═══════════════════════════════════════════════════════════════════

    def _draw_first_page_header(
        self, c: canvas_module.Canvas, invoice: Invoice, font: str
    ) -> None:
        """Draw the company name and three-column header on the first page."""
        bold = self._font(bold=True)
        company = invoice.seller_business_name or ''

        # Company name — left-aligned, bold 16pt
        c.setFont(bold, COMPANY_NAME_SIZE)
        c.setFillColor(BLACK)
        c.drawString(SELLER_LABEL_X, PAGE_HEIGHT - COMPANY_NAME_Y, company)

        # Section labels — bold 12pt
        c.setFont(bold, SECTION_HEADER_SIZE)
        c.drawString(SELLER_LABEL_X, PAGE_HEIGHT - SECTION_HEADER_Y, "Seller Information")
        c.drawString(BUYER_LABEL_X, PAGE_HEIGHT - SECTION_HEADER_Y, "Buyer Information")
        c.drawString(SUMMARY_LABEL_X, PAGE_HEIGHT - SECTION_HEADER_Y, "Invoice Summary")

        # Field values — regular 10pt
        c.setFont(font, FIELD_VALUE_SIZE)

        # SELLER column
        self._draw_header_field(c, font, SELLER_LABEL_X, SELLER_VALUE_X,
                                FIELD_ROW1_Y, "Business Name:", company)
        self._draw_header_field(c, font, SELLER_LABEL_X, SELLER_VALUE_X,
                                FIELD_ROW2_Y, "Registration No.:",
                                invoice.seller_ntn_cnic or '')
        self._draw_header_field(c, font, SELLER_LABEL_X, SELLER_VALUE_X,
                                FIELD_ROW3_Y, "Province:",
                                invoice.seller_province or '')

        # BUYER column
        self._draw_header_field(c, font, BUYER_LABEL_X, BUYER_VALUE_X,
                                FIELD_ROW1_Y, "Business Name:",
                                invoice.buyer_business_name or '')
        self._draw_header_field(c, font, BUYER_LABEL_X, BUYER_VALUE_X,
                                FIELD_ROW2_Y, "Registration No.:",
                                invoice.buyer_ntn_cnic or '')
        self._draw_header_field(c, font, BUYER_LABEL_X, BUYER_VALUE_X,
                                FIELD_ROW3_Y, "Province:",
                                invoice.buyer_province or '')

        # INVOICE SUMMARY column
        self._draw_header_field(c, font, SUMMARY_LABEL_X, SUMMARY_VALUE_X,
                                FIELD_ROW1_Y, "FBR Invoice No.:",
                                invoice.fbr_reference_number or '')
        self._draw_header_field(c, font, SUMMARY_LABEL_X, SUMMARY_VALUE_X,
                                FIELD_ROW2_Y, "Local Invoice No.:",
                                invoice.external_id or '')
        self._draw_header_field(c, font, SUMMARY_LABEL_X, SUMMARY_VALUE_X,
                                FIELD_ROW3_Y, "Invoice Date:",
                                invoice.invoice_date or '')
        self._draw_header_field(c, font, SUMMARY_LABEL_X, SUMMARY_VALUE_X,
                                FIELD_ROW4_Y, "Invoice Type:",
                                invoice.invoice_type or '')

    def _draw_header_field(
        self, c: canvas_module.Canvas, font: str,
        label_x: float, value_x: float, y_from_top: float,
        label: str, value: str
    ) -> None:
        """Draw a label:value pair in the header area."""
        y = PAGE_HEIGHT - y_from_top
        c.setFont(font, FIELD_LABEL_SIZE)
        c.drawString(label_x, y, label)
        c.setFont(font, FIELD_VALUE_SIZE)
        c.drawString(value_x, y, value)

    # ═══════════════════════════════════════════════════════════════════
    # TABLE DRAWING
    # ═══════════════════════════════════════════════════════════════════

    def _draw_table_grid(
        self,
        c: canvas_module.Canvas,
        items: list,
        row_heights: List[float],
        font: str,
        y_start: float,
        is_first: bool,
        is_last: bool,
        start_sr_no: int = 1,
        totals_data: Optional[list] = None
    ) -> None:
        """Draw the complete table with grid lines, headers, data rows, and totals."""
        bold = self._font(bold=True)
        y_top = PAGE_HEIGHT - y_start  # Convert to canvas Y
        current_y = y_top

        # ── Table header row ──
        header_h = 24.0
        header_y_bottom = current_y - header_h

        # Draw header grid
        self._draw_grid_rect(c, TABLE_LEFT, current_y, TABLE_RIGHT, header_y_bottom,
                             line_width=1.0, fill=False)
        # Vertical lines in header
        for x in COL_X[1:-1]:
            self._draw_vline(c, x, current_y, header_y_bottom, line_width=1.0)

        # Header text row 1 — main columns (0-15) at y=219.5
        # SRO columns (16,17) have their own two-row header at y=215.0 / y=224.0
        header_text_y1 = PAGE_HEIGHT - 219.5
        c.setFont(bold, TABLE_HEADER_SIZE)
        c.setFillColor(BLACK)
        for i in range(16):  # Only columns 0-15 (Sr. No. through Discount)
            header = TABLE_HEADERS_ROW1[i]
            if not header:
                continue
            col_w = COL_WIDTHS[i]
            self._draw_cell_str(c, header, COL_X[i], header_text_y1, col_w,
                                bold, TABLE_HEADER_SIZE, 'C')

        # SRO two-row header
        sro_top_y = PAGE_HEIGHT - 215.0     # "SRO / Schedule " / "SRO Item "
        sro_bottom_y = PAGE_HEIGHT - 224.0  # "No." / "Sr. No."
        sro_labels_top = [('SRO / Schedule ', 16), ('SRO Item ', 17)]
        sro_labels_bottom = [('No.', 16), ('Sr. No.', 17)]

        for text, col_idx in sro_labels_top:
            self._draw_cell_str(c, text, COL_X[col_idx], sro_top_y, COL_WIDTHS[col_idx],
                                bold, TABLE_HEADER_SIZE, 'C')
        for text, col_idx in sro_labels_bottom:
            self._draw_cell_str(c, text, COL_X[col_idx], sro_bottom_y, COL_WIDTHS[col_idx],
                                bold, TABLE_HEADER_SIZE, 'C')

        current_y = header_y_bottom

        # ── Data rows ──
        for idx, (item, rh) in enumerate(zip(items, row_heights)):
            row_bottom = current_y - rh
            sr_no = start_sr_no + idx

            # Row horizontal borders
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, current_y, line_width=1.0)
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, row_bottom, line_width=0.5)

            # Vertical lines through row
            for x in COL_X:
                self._draw_vline(c, x, current_y, row_bottom, line_width=1.0)

            # Cell content
            row_data = self._build_item_row(item, sr_no)
            c.setFont(font, TABLE_DATA_SIZE)
            c.setFillColor(BLACK)

            for col_idx, (cell_text, col_w) in enumerate(zip(row_data, COL_WIDTHS)):
                align = COL_ALIGN[col_idx]
                col_x = COL_X[col_idx]
                text_w = max(col_w - CELL_PADDING_LEFT * 2, 10)

                # Wrap text to column width
                lines = self._wrap_text(str(cell_text), text_w, font, TABLE_DATA_SIZE)
                # Draw each line top-aligned within the cell
                line_y = current_y - CELL_PADDING_TOP - CELL_LINE_HEIGHT * 0.8
                for line in lines:
                    if line_y < row_bottom + CELL_PADDING_TOP:
                        break  # Truncate if text exceeds row height
                    self._draw_text_aligned(c, line, col_x, line_y, col_w,
                                            font, TABLE_DATA_SIZE, align)
                    line_y -= CELL_LINE_HEIGHT

            current_y = row_bottom

        # ── Totals row (only on last page) ──
        if is_last and totals_data:
            # Compute row height from the actual totals data being displayed
            max_lines = 1
            for col_idx in range(8, N_COLS):
                cell_text = str(totals_data[col_idx])
                text_w = max(COL_WIDTHS[col_idx] - CELL_PADDING_LEFT * 2, 10)
                lines = self._wrap_text(cell_text, text_w, bold, TOTALS_VALUE_SIZE)
                max_lines = max(max_lines, len(lines))
            totals_rh = max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2 + 6
            totals_bottom = current_y - totals_rh

            # Top border of totals row (thicker to separate from data)
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, current_y, line_width=1.5)
            # Bottom border
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, totals_bottom, line_width=0.5)

            # Vertical lines for all columns in totals row
            for x in COL_X:
                self._draw_vline(c, x, current_y, totals_bottom, line_width=1.0)

            # Merged cell: columns 0-7 (Sr. No. through Rate) show "Total:" right-aligned
            merge_left = COL_X[0]
            merge_right = COL_X[8]
            self._draw_hline(c, merge_left, merge_right, current_y, line_width=1.5)
            self._draw_hline(c, merge_left, merge_right, totals_bottom, line_width=0.5)

            # Text position — use same offset as data rows for consistency
            text_offset = CELL_PADDING_TOP + CELL_LINE_HEIGHT * 0.8
            totals_label_y = current_y - text_offset
            totals_val_y = current_y - text_offset

            # "Total:" label
            c.setFont(bold, TOTALS_LABEL_SIZE)
            c.setFillColor(BLACK)
            self._draw_text_aligned(c, "Total:", merge_left, totals_label_y,
                                    merge_right - merge_left, bold, TOTALS_LABEL_SIZE, 'R')

            # Numeric totals in columns 8-17
            c.setFont(bold, TOTALS_VALUE_SIZE)
            for col_idx in range(8, N_COLS):
                cell_text = totals_data[col_idx]
                col_x = COL_X[col_idx]
                col_w = COL_WIDTHS[col_idx]
                align = COL_ALIGN[col_idx]
                text_w = max(col_w - CELL_PADDING_LEFT * 2, 10)

                lines = self._wrap_text(str(cell_text), text_w, bold, TOTALS_VALUE_SIZE)
                line_y = totals_val_y
                for line in lines:
                    if line_y < totals_bottom + 2:
                        break
                    self._draw_text_aligned(c, line, col_x, line_y, col_w,
                                            bold, TOTALS_VALUE_SIZE, align)
                    line_y -= CELL_LINE_HEIGHT

            current_y = totals_bottom

    # ── Grid drawing primitives ────────────────────────────────────────

    def _draw_grid_rect(self, c, x1, y1, x2, y2, line_width=1.0, fill=False):
        """Draw a rectangle with given stroke."""
        c.setStrokeColor(GRID_GRAY)
        c.setLineWidth(line_width)
        if fill:
            c.setFillColor(colors.white)
            c.rect(x1, y2, x2 - x1, y1 - y2, fill=1, stroke=1)
        else:
            c.rect(x1, y2, x2 - x1, y1 - y2, fill=0, stroke=1)

    def _draw_hline(self, c, x1, x2, y, line_width=0.5):
        c.setStrokeColor(GRID_GRAY)
        c.setLineWidth(line_width)
        c.line(x1, y, x2, y)

    def _draw_vline(self, c, x, y1, y2, line_width=1.0):
        c.setStrokeColor(GRID_GRAY)
        c.setLineWidth(line_width)
        c.line(x, y1, x, y2)

    def _draw_cell_str(self, c, text, x, y, col_w, font_name, font_size, align):
        """Draw text within a cell. x is the left edge of the cell."""
        self._draw_text_aligned(c, text, x, y, col_w, font_name, font_size, align)

    def _draw_text_aligned(self, c, text, x, y, cell_w, font_name, font_size, align):
        """Draw text with alignment. x is the left edge of the cell."""
        if not text:
            return
        c.setFont(font_name, font_size)
        if align == 'R':
            c.drawRightString(x + cell_w - CELL_PADDING_LEFT, y, text)
        elif align == 'C':
            c.drawCentredString(x + cell_w / 2, y, text)
        else:  # Left
            c.drawString(x + CELL_PADDING_LEFT, y, text)

    # ── Row height calculation ─────────────────────────────────────────

    def _compute_row_heights(self, items: list, font: str) -> List[float]:
        """Compute the required height for each data row."""
        heights = []
        for item in items:
            row_data = self._build_item_row(item, 1)
            max_lines = 1
            for col_idx, cell_text in enumerate(row_data):
                text_w = max(COL_WIDTHS[col_idx] - CELL_PADDING_LEFT * 2, 10)
                lines = self._wrap_text(str(cell_text), text_w, font, TABLE_DATA_SIZE)
                max_lines = max(max_lines, len(lines))
            rh = max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2
            heights.append(max(rh, 14.0))  # Minimum row height
        return heights

    def _calc_totals_height(self, items: list, font: str) -> float:
        """Calculate totals row height."""
        totals_data = self._build_totals_row(items)
        max_lines = 1
        for col_idx, cell_text in enumerate(totals_data):
            if col_idx < 8:
                continue  # Skip merged columns
            text_w = max(COL_WIDTHS[col_idx] - CELL_PADDING_LEFT * 2, 10)
            lines = self._wrap_text(str(cell_text), text_w, font, TOTALS_VALUE_SIZE)
            max_lines = max(max_lines, len(lines))
        return max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2 + 4

    # ── Data builders ──────────────────────────────────────────────────

    def _build_item_row(self, item: dict, sr_no: int) -> list:
        """Build a table row from an invoice item dict."""
        return [
            str(sr_no),
            str(item.get('hs_code', '')),
            '',  # HS Code Description — not in model, left blank
            str(item.get('product_description', '')),
            str(item.get('sale_type', '')),
            self._fmt_num(item.get('quantity', 0)),
            str(item.get('uom', '')),
            str(item.get('rate', '')),
            self._fmt_num(item.get('value_sales_excluding_st', 0)),
            self._fmt_num(item.get('fixed_notified_value_or_retail_price', 0)),
            self._fmt_num(item.get('sales_tax_applicable', 0)),
            self._fmt_num(item.get('extra_tax', 0)),
            self._fmt_num(item.get('further_tax', 0)),
            self._fmt_num(item.get('fed_payable', 0)),
            self._fmt_num(item.get('sales_tax_withheld_at_source', 0)),
            self._fmt_num(item.get('discount', 0)),
            str(item.get('sro_schedule_no', '')),
            str(item.get('sro_item_serial_no', '')),
        ]

    def _build_totals_row(self, items: list) -> list:
        """Build the totals summary row."""
        sums = {}
        for field in ['value_sales_excluding_st', 'fixed_notified_value_or_retail_price',
                       'sales_tax_applicable', 'extra_tax', 'further_tax',
                       'fed_payable', 'sales_tax_withheld_at_source', 'discount']:
            sums[field] = sum(float(it.get(field, 0) or 0) for it in items)

        return [
            '',  # Sr. No.
            '',  # HS Code
            '',  # HS Code Description
            '',  # Product Description
            '',  # Sales Type
            '',  # Quantity
            '',  # UoM
            '',  # Rate
            self._fmt_num(sums['value_sales_excluding_st']),
            self._fmt_num(sums['fixed_notified_value_or_retail_price']),
            self._fmt_num(sums['sales_tax_applicable']),
            self._fmt_num(sums['extra_tax']),
            self._fmt_num(sums['further_tax']),
            self._fmt_num(sums['fed_payable']),
            self._fmt_num(sums['sales_tax_withheld_at_source']),
            self._fmt_num(sums['discount']),
            '',  # SRO Schedule No.
            '',  # SRO Item Sr. No.
        ]

    # ── Page number ────────────────────────────────────────────────────

    # ── FBR compliance elements ──────────────────────────────────────

    def _draw_fbr_logo_and_qr(
        self, c: canvas_module.Canvas, usin: str, font: str
    ) -> None:
        """Draw FBR logo and QR code side by side at top-right of the first page."""
        logo = self._load_fbr_logo()
        qr_img = self._generate_qr_code(usin) if usin else None

        if logo is None and qr_img is None:
            return

        # Size constants
        logo_max_w = 1.6 * inch
        logo_max_h = 0.55 * inch
        qr_size = 0.65 * inch
        gap = 8  # gap between logo and QR

        logo_display_w = logo_max_w
        logo_display_h = logo_max_h

        if logo is not None:
            lw, lh = logo.size
            aspect = lw / lh
            logo_display_h = logo_max_w / aspect
            if logo_display_h > logo_max_h:
                logo_display_h = logo_max_h
                logo_display_w = logo_display_h * aspect
            else:
                logo_display_w = logo_max_w

        total_w = logo_display_w + (gap + qr_size if qr_img else 0)
        start_x = TABLE_RIGHT - total_w

        try:
            if logo is not None:
                logo_y = PAGE_HEIGHT - COMPANY_NAME_Y - logo_display_h + 4
                c.drawInlineImage(logo, start_x, logo_y,
                                  width=logo_display_w, height=logo_display_h,
                                  preserveAspectRatio=True)
        except Exception as e:
            logger.warning(f"Could not draw FBR logo: {e}")

        if qr_img is not None:
            try:
                qr_x = start_x + logo_display_w + gap
                qr_y = PAGE_HEIGHT - COMPANY_NAME_Y - qr_size + 4
                c.drawInlineImage(qr_img, qr_x, qr_y,
                                  width=qr_size, height=qr_size,
                                  preserveAspectRatio=True)
            except Exception as e:
                logger.warning(f"Could not draw QR code: {e}")

    # ── Page number ──────────────────────────────────────────────────

    def _draw_page_number(self, c, page_num: int, total_pages: int, font: str):
        """Draw 'Page X of Y' at bottom-right."""
        text = f"Page {page_num} of {total_pages}"
        bold = self._font(bold=True)
        c.setFont(bold, PAGE_NUM_SIZE)
        c.setFillColor(BLACK)
        tw = self._string_width(text, bold, PAGE_NUM_SIZE)
        c.drawString(TABLE_RIGHT - tw, PAGE_HEIGHT - PAGE_BOTTOM, text)
