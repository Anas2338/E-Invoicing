"""
PDF generation service for FBR-compliant invoice printing.

Generates A4 portrait invoice PDFs carrying the full FBR invoice template
data:

- A4 portrait page (595.28 x 841.89 pt), 30pt side margins
- Helvetica fonts throughout (matching sample template)
- Header: company name + FBR logo/QR code, then a full-width Invoice
  Summary strip with side-by-side Seller and Buyer blocks below it
- Full 22-column line items table with gray grid lines; column widths keep
  the landscape template proportions and drop to a per-column minimum so
  figures stay legible on the narrower page
- Wrapped table headers sized to their column
- Auto-sized rows with text wrapping (top-aligned cell content)
- Multi-page with page numbers, no header on continuation pages
- Totals row with merged "Total:" label cell

Every field shown on the landscape template is still shown here; only the
page orientation and the arrangement of the header change.
"""
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Tuple
import logging

from reportlab.pdfgen import canvas as canvas_module
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from PIL import Image
import qrcode

from ..models.invoice import Invoice

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# PAGE DIMENSIONS (A4 portrait)
# ═══════════════════════════════════════════════════════════════════════
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.28 x 841.89 pt
PAGE_SIZE = A4

MARGIN_X = 30.0

# ═══════════════════════════════════════════════════════════════════════
# GRID COLORS (exact match to sample.pdf)
# ═══════════════════════════════════════════════════════════════════════
GRID_GRAY = colors.Color(0.827, 0.827, 0.827)  # RGB(211,211,211)
BLACK = colors.Color(0, 0, 0)

# ═══════════════════════════════════════════════════════════════════════
# COLUMN DEFINITIONS (based on sample.pdf, with Item Rate added)
# ═══════════════════════════════════════════════════════════════════════
# Relative column widths, in the proportions of the FBR landscape template.
# The table is rescaled to the portrait page width at render time (see
# _fit_column_widths).
COL_WIDTH_WEIGHTS = [
    33.2,    # Sr. No.
    48.0,    # HS Code
    122.0,   # Product Description
    55.0,    # Sales Type
    39.0,    # Quantity
    50.0,    # Item Rate
    26.0,    # UoM
    26.0,    # Rate
    50.0,    # Sales Value
    46.0,    # Retail Price
    47.0,    # Sales Tax
    43.0,    # Extra Tax
    55.0,    # Further Tax
    30.5,    # FED
    41.0,    # ST WHT
    45.0,    # Discount
    66.0,    # SRO / Schedule No.
    34.0,    # SRO Item Sr. No.
    64.0,    # Total Amount
    46.0,    # Income Tax Type
    52.0,    # Income Tax Value
    64.0,    # Total Value Including Advance Tax
]

# Minimum width (pt) each column may shrink to on the portrait page. Wide
# description columns give up space first so figures stay readable.
MIN_COL_WIDTHS = [
    18.0,    # Sr. No.
    30.0,    # HS Code
    62.0,    # Product Description
    34.0,    # Sales Type
    32.0,    # Quantity
    32.0,    # Item Rate
    34.0,    # UoM  (fits "Numbers", the longest common FBR unit)
    20.0,    # Rate
    42.0,    # Sales Value
    40.0,    # Retail Price
    38.0,    # Sales Tax
    34.0,    # Extra Tax
    38.0,    # Further Tax
    26.0,    # FED
    34.0,    # ST WHT
    34.0,    # Discount
    34.0,    # SRO / Schedule No.
    24.0,    # SRO Item Sr. No.
    46.0,    # Total Amount
    34.0,    # Income Tax Type
    34.0,    # Income Tax Value
    46.0,    # Total Value Including Advance Tax
]

N_COLS = len(COL_WIDTH_WEIGHTS)  # 22 columns

# Leading columns folded into the single "Total:" label cell of the totals
# row. Every column up to and including "Rate" is always visible, so the
# merge always spans exactly this many columns.
TOTALS_MERGE_COLS = 8

# Table spans the full content width of the portrait page.
TABLE_LEFT = MARGIN_X                        # 30.0
TABLE_RIGHT = PAGE_WIDTH - MARGIN_X          # 565.28
TABLE_WIDTH = TABLE_RIGHT - TABLE_LEFT       # 535.28

# Columns hidden entirely from the PDF when every item has a zero/empty
# value in the item field named here: column index -> invoice item field.
# The field only decides visibility — the text drawn comes from
# _build_item_row. The three income tax columns share one trigger, so they
# appear and disappear together.
HIDEABLE_COLUMNS = {
    11: 'extra_tax',
    12: 'further_tax',
    13: 'fed_payable',
    14: 'sales_tax_withheld_at_source',
    15: 'discount',
    16: 'sro_schedule_no',
    17: 'sro_item_serial_no',
    19: 'withholding_tax_amount',  # Income Tax Type
    20: 'withholding_tax_amount',  # Income Tax Value
    21: 'withholding_tax_amount',  # Total Value Including Advance Tax
}

# Column alignments: 'L'=left, 'R'=right, 'C'=center
COL_ALIGN = [
    'C',  # Sr. No.
    'L',  # HS Code
    'L',  # Product Description
    'L',  # Sales Type
    'C',  # Quantity
    'C',  # Item Rate
    'C',  # UoM
    'C',  # Rate
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
    'R',  # Total Amount
    'C',  # Income Tax Type
    'R',  # Income Tax Value
    'R',  # Total Value Including Advance Tax
]

# ═══════════════════════════════════════════════════════════════════════
# TABLE HEADERS (two rows for SRO columns, matching sample)
# ═══════════════════════════════════════════════════════════════════════
TABLE_HEADERS_ROW1 = [
    'Sr. No.', 'HS Code', 'Product Description', 'Sales Type',
    'Quantity', 'Item Rate', 'UoM', 'Rate', 'Sales Value',
    'Retail Price', 'Sales Tax', 'Extra Tax ', 'Further Tax', 'FED',
    'ST WHT ', 'Discount', 'SRO / Schedule ', 'SRO Item ',
    'Total Amount', 'Income Tax Type', 'Income Tax Value',
    'Total Value Including Advance Tax',
]
TABLE_HEADERS_ROW2 = [
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'No.', 'Sr. No.', '', '', '', '',
]

# ═══════════════════════════════════════════════════════════════════════
# FONT SIZES (portrait)
# ═══════════════════════════════════════════════════════════════════════
COMPANY_NAME_SIZE = 15
SECTION_HEADER_SIZE = 10
FIELD_LABEL_SIZE = 8
FIELD_VALUE_SIZE = 9
TABLE_HEADER_SIZE = 7
TABLE_DATA_SIZE = 7
TOTALS_LABEL_SIZE = 9
TOTALS_VALUE_SIZE = 7
PAGE_NUM_SIZE = 8

# Line spacing for wrapped cell text
CELL_LINE_HEIGHT = 8.5  # 7pt font + 1.5pt leading
CELL_PADDING_LEFT = 2
CELL_PADDING_TOP = 2

# Line spacing elsewhere (measured top-down within a block)
FIELD_LINE_HEIGHT = 12.0          # 9pt value + 3pt leading
LABEL_LINE_HEIGHT = 11.0          # 8pt label + 3pt leading
TABLE_HEADER_LINE_HEIGHT = 9.0    # one wrapped table-header line

# Smallest font a numeric cell may shrink to before it wraps instead
MIN_CELL_FONT_SIZE = 5.0

# ═══════════════════════════════════════════════════════════════════════
# HEADER LAYOUT (portrait)
# ═══════════════════════════════════════════════════════════════════════
HEADER_TOP = 28.0          # Distance from the page top to the header's first row
COMPANY_LINE_HEIGHT = 17.0  # 15pt company name + leading
COMPANY_EXTRA_GAP = 18.0    # Gap below the company name / logo block

# FBR logo + QR code, reserved at the top-right of the first page.
# The logo artwork is square, so it is drawn at the QR code's size to keep
# the two marks visually equal (a smaller bound rendered it short next to
# the QR code).
QR_SIZE = 0.55 * inch
LOGO_MAX_W = QR_SIZE
LOGO_MAX_H = QR_SIZE
LOGO_QR_GAP = 6.0
LOGO_BLOCK_W = LOGO_MAX_W + LOGO_QR_GAP + QR_SIZE
LOGO_BLOCK_H = max(LOGO_MAX_H, QR_SIZE)

# Seller and Buyer blocks sit side by side beneath the Invoice Summary
SELLER_BLOCK_W = 294.0
BLOCK_COL_GAP = 12.0
BUYER_BLOCK_X = TABLE_LEFT + SELLER_BLOCK_W + BLOCK_COL_GAP
BUYER_BLOCK_W = TABLE_WIDTH - SELLER_BLOCK_W - BLOCK_COL_GAP

# Invoice Summary strip — four label/value columns across the table width
SUMMARY_COL_GAP = 8.0
SUMMARY_COL_W = (TABLE_WIDTH - 3 * SUMMARY_COL_GAP) / 4.0

# Section title ("Seller Information") with a rule above its fields
SECTION_RULE_GAP = 4.0
SECTION_BODY_GAP = 10.0
SECTION_TITLE_H = SECTION_HEADER_SIZE + SECTION_RULE_GAP + SECTION_BODY_GAP

HEADER_BLOCK_GAP = 20.0    # Gap between header blocks
TABLE_GAP = 16.0           # Gap between the header and the table
FIELD_GAP = 9.0            # Gap between stacked fields inside a block

# ═══════════════════════════════════════════════════════════════════════
# CONTENT AREA BOUNDARIES (measured from the page top)
# ═══════════════════════════════════════════════════════════════════════
CONTENT_TOP = 210.0     # Fallback table top on the first page
PAGE_TOP = 30.0         # Table top on continuation pages
FOOTER_BASELINE = 26.0  # Page number baseline, measured from the page bottom
BOTTOM_MARGIN = 46.0    # Space reserved at the bottom for the page number

# ═══════════════════════════════════════════════════════════════════════
# ASSETS
# ═══════════════════════════════════════════════════════════════════════
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "NotoSansArabic-Regular.ttf"
LOGO_PATH = ASSETS_DIR / "fbr_logo.png"


def fmt_num(value) -> str:
    """Format a numeric value for display.

    Shared by PDFService and ReportPDFService so both documents use the
    exact same number formatting.
    """
    if value is None or value == '':
        return '0.00'
    try:
        v = float(value)
        if v == int(v) and abs(v) < 1000:
            return str(int(v))
        return f"{v:,.2f}"
    except (ValueError, TypeError):
        return str(value)


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
                    # Character-wrap long word across multiple lines (no "...")
                    line = ''
                    for ch in word:
                        if c.stringWidth(line + ch, font_name, font_size) > max_width:
                            lines.append(line)
                            line = ch
                        else:
                            line += ch
                    if line:
                        lines.append(line)
                else:
                    current = word
        if current:
            lines.append(current)
        return lines if lines else ['']

    @staticmethod
    def _is_numeric(value: str) -> bool:
        """True if the cell string is a number.

        Numeric cells shrink their font when too wide; text cells wrap to
        multiple lines instead.
        """
        try:
            float(str(value).replace(',', ''))
            return True
        except (ValueError, TypeError):
            return False

    def _fit_font_size(self, text: str, max_width: float, font_name: str,
                       max_size: int, min_size: int = 5) -> int:
        """Largest font size at which `text` fits on one line within max_width.

        Used to show full values (e.g. long numbers) that would otherwise be
        truncated with "...".
        """
        c = self._get_measure_canvas()
        size = max_size
        while size >= min_size:
            c.setFont(font_name, size)
            if c.stringWidth(text, font_name, size) <= max_width:
                return size
            size -= 1
        return min_size

    def _cell_draw(self, text: str, col_w: float, font: str, max_size: int):
        """How a table cell is drawn, as (font_size, lines).

        Numbers shrink to keep the whole figure on one line; text wraps at the
        base size. A number too wide even at MIN_CELL_FONT_SIZE wraps at its
        comma boundaries rather than overlapping its neighbours.
        """
        text_w = max(col_w - CELL_PADDING_LEFT * 2, 10)
        if self._is_numeric(text):
            size = self._fit_font_size(text, text_w, font, max_size,
                                       MIN_CELL_FONT_SIZE)
            if self._string_width(text, font, size) <= text_w:
                return size, [text]
            return size, self._wrap_number(text, text_w, font, size)
        return max_size, self._wrap_text(text, text_w, font, max_size)

    def _wrap_number(self, text: str, max_width: float, font: str,
                     size: float) -> List[str]:
        """Split a figure across lines at commas (e.g. 303,523,532.25)."""
        parts = text.split(',')
        lines = []
        current = ''
        for i, part in enumerate(parts):
            chunk = part + (',' if i < len(parts) - 1 else '')
            if current and self._string_width(current + chunk, font, size) > max_width:
                lines.append(current)
                current = chunk
            else:
                current += chunk
        if current:
            lines.append(current)

        # Anything still too wide (a single long chunk) is character-wrapped.
        wrapped = []
        for line in lines:
            if self._string_width(line, font, size) > max_width:
                wrapped.extend(self._wrap_text(line, max_width, font, size))
            else:
                wrapped.append(line)
        return wrapped or [text]

    @staticmethod
    def _fmt_num(value) -> str:
        """Format a numeric value for display."""
        return fmt_num(value)

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

        # First-page table top shifts down when the header grows (e.g. wrapped
        # addresses), so it must be computed before pagination.
        first_page_top = max(CONTENT_TOP, self._compute_header_bottom(invoice, font))

        # Column layout — zero-valued columns (11-17) are hidden
        layout = self._build_table_layout(items)

        # Split items into pages. The table header row sits above the data
        # rows on every page, so its height comes off the available space.
        header_h = self._header_height(layout)
        first_page_available = PAGE_HEIGHT - first_page_top - BOTTOM_MARGIN - header_h
        cont_page_available = PAGE_HEIGHT - PAGE_TOP - BOTTOM_MARGIN - header_h

        pages = self._paginate_items(
            items, font, first_page_available, cont_page_available, layout=layout)
        total_pages = len(pages)

        # Pre-compute totals from ALL items (not just page items)
        totals_data = self._build_totals_row(items)

        for page_num, page_items in enumerate(pages, 1):
            is_first = (page_num == 1)
            y_start = first_page_top if is_first else PAGE_TOP

            if is_first:
                self._draw_first_page_header(c, invoice, font)
                # FBR logo and QR code at top-right
                self._draw_fbr_logo_and_qr(c, usin, font)

            is_last = (page_num == total_pages)

            # Compute row heights for this page's items
            row_heights = self._compute_row_heights(page_items, font, layout=layout)

            # Draw table
            self._draw_table_grid(
                c, page_items, row_heights, font,
                y_start=y_start, is_last=is_last,
                start_sr_no=sum(len(p) for p in pages[:page_num - 1]) + 1,
                totals_data=totals_data, layout=layout
            )

            # Page number (bottom-right)
            self._draw_page_number(c, page_num, total_pages, font)

            if not is_last:
                c.showPage()

        return total_pages

    def _paginate_items(
        self, items: list, font: str,
        first_page_avail: float, cont_page_avail: float,
        layout: Optional[dict] = None
    ) -> List[list]:
        """Split items into pages based on available vertical space."""
        all_heights = self._compute_row_heights(items, font, layout=layout)
        totals_h = self._calc_totals_height(items, font, layout=layout)

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
    # DYNAMIC COLUMN LAYOUT
    # ═══════════════════════════════════════════════════════════════════

    def _build_table_layout(self, items: list) -> dict:
        """Compute the column layout for an invoice's line items.

        Columns 11-17 (Extra Tax, Further Tax, FED, ST WHT, Discount,
        SRO / Schedule, SRO Item) are dropped when every item has a zero
        or empty value in that column, and the income tax block (Income Tax
        Type, Income Tax Value, Total Value Including Advance Tax) is dropped
        when no item carries an income tax value. Remaining columns keep the
        template proportions and are rescaled to span the full table width.

        Returns: {'indices', 'xs', 'widths', 'aligns', 'headers1', 'headers2'}
        """
        hidden = set()
        for col, field in HIDEABLE_COLUMNS.items():
            if all(self._is_zero_or_empty(item.get(field)) for item in items):
                hidden.add(col)

        vis = [i for i in range(N_COLS) if i not in hidden]
        return self._layout_for(vis)

    def _layout_for(self, indices: list) -> dict:
        """Build a layout dict for the given visible column indices."""
        widths = self._fit_column_widths(indices)
        xs = [TABLE_LEFT]
        for w in widths[:-1]:
            xs.append(xs[-1] + w)
        xs.append(TABLE_RIGHT)

        return {
            'indices': indices,
            'xs': xs,
            'widths': widths,
            'aligns': [COL_ALIGN[i] for i in indices],
            'headers1': [TABLE_HEADERS_ROW1[i] for i in indices],
            'headers2': [TABLE_HEADERS_ROW2[i] for i in indices],
        }

    @staticmethod
    def _fit_column_widths(indices: list) -> List[float]:
        """Widths for `indices`, fitted to the portrait table width.

        Widths start from the FBR landscape template proportions and are
        floored at MIN_COL_WIDTHS so figures stay legible. When the floors no
        longer fit the narrower page, the deficit is taken from the columns
        still above their minimum (the wide description columns first).
        """
        weights = [COL_WIDTH_WEIGHTS[i] for i in indices]
        scale = TABLE_WIDTH / sum(weights)
        widths = [max(w * scale, MIN_COL_WIDTHS[i])
                  for w, i in zip(weights, indices)]

        excess = sum(widths) - TABLE_WIDTH
        if excess > 0:
            spare = [max(w - MIN_COL_WIDTHS[i], 0.0)
                     for w, i in zip(widths, indices)]
            room = sum(spare)
            if room > 0:
                give = min(excess, room) / room
                widths = [w - s * give for w, s in zip(widths, spare)]

        # Fill the table width exactly (absorbs rounding and any shortfall
        # left when every column already sits at its floor).
        factor = TABLE_WIDTH / sum(widths)
        return [w * factor for w in widths]

    # ═══════════════════════════════════════════════════════════════════
    # TABLE HEADER (wrapped, sized to its column)
    # ═══════════════════════════════════════════════════════════════════

    def _header_size(self, layout: dict) -> int:
        """Header font size for this layout.

        Steps the whole header row down when a narrow column cannot fit its
        longest word, so labels wrap at word boundaries instead of breaking
        mid-word. One size is used across the table to keep the row even.
        """
        bold = self._font(bold=True)
        sizes = []
        for j, header in enumerate(layout['headers1']):
            text_w = max(layout['widths'][j] - CELL_PADDING_LEFT * 2, 8)
            words = f"{header} {layout['headers2'][j]}".split()
            sizes.append(self._fit_font_size(
                max(words, key=len) if words else '', text_w, bold,
                TABLE_HEADER_SIZE, MIN_CELL_FONT_SIZE))
        return min(sizes) if sizes else TABLE_HEADER_SIZE

    def _header_lines(self, layout: dict, size: int) -> List[List[str]]:
        """Wrapped header text per column, wrapped at `size`.

        SRO columns carry a second header row ("No." / "Sr. No."), which is
        stacked under the first so both read as one wrapped label.
        """
        bold = self._font(bold=True)
        lines = []
        for j, header in enumerate(layout['headers1']):
            text_w = max(layout['widths'][j] - CELL_PADDING_LEFT * 2, 8)
            col_lines = self._wrap_text(header, text_w, bold, size)
            second = layout['headers2'][j]
            if second:
                col_lines = col_lines + self._wrap_text(second, text_w, bold, size)
            lines.append(col_lines)
        return lines

    def _header_height(self, layout: dict) -> float:
        """Height of the table header row for this layout."""
        size = self._header_size(layout)
        max_lines = max(len(l) for l in self._header_lines(layout, size))
        return max(max_lines * TABLE_HEADER_LINE_HEIGHT + CELL_PADDING_TOP * 2,
                   18.0)

    @staticmethod
    def _is_zero_or_empty(value) -> bool:
        """True for None, empty string, or a numeric value equal to zero."""
        if value is None:
            return True
        s = str(value).strip()
        if s == '':
            return True
        try:
            return float(s) == 0
        except ValueError:
            return False

    # ═══════════════════════════════════════════════════════════════════
    # FIRST PAGE HEADER
    # ═══════════════════════════════════════════════════════════════════

    def _header_fields(self, invoice: Invoice) -> dict:
        """Header fields as (label, value) lists, one list per block."""
        return {
            'seller': [
                ("Business Name", invoice.seller_business_name or ''),
                ("Registration No.", invoice.seller_ntn_cnic or ''),
                ("Province", invoice.seller_province or ''),
                ("Address", invoice.seller_address or ''),
            ],
            'buyer': [
                ("Business Name", invoice.buyer_business_name or ''),
                ("Registration No.", invoice.buyer_ntn_cnic or ''),
                ("Province", invoice.buyer_province or ''),
                ("Address", invoice.buyer_address or ''),
            ],
            'summary': [
                ("FBR Invoice No.", invoice.fbr_reference_number or ''),
                ("Local Invoice No.", invoice.external_id or ''),
                ("Invoice Date", invoice.invoice_date or ''),
                ("Invoice Type", invoice.invoice_type or ''),
            ],
        }

    def _compute_header_metrics(self, invoice: Invoice, font: str) -> dict:
        """Wrapped header text and top-down positions for the first page.

        Every position is measured from the page top. Shared by
        _compute_header_bottom and _draw_first_page_header so the table always
        starts where the drawn header actually ends, however much the values
        wrap.
        """
        bold = self._font(bold=True)

        def stack(rows: list, width: float) -> tuple:
            """Wrap each (label, value) pair; return them with the block height."""
            wrapped = []
            height = 0.0
            for label, value in rows:
                lines = self._wrap_text(value, width, font, FIELD_VALUE_SIZE)
                wrapped.append((label, lines))
                height += (LABEL_LINE_HEIGHT + len(lines) * FIELD_LINE_HEIGHT
                           + FIELD_GAP)
            return wrapped, height

        # ── Company name (top-left) and FBR logo + QR code (top-right) ──
        company_lines = self._wrap_text(
            invoice.seller_business_name or '',
            TABLE_WIDTH - LOGO_BLOCK_W - 8.0, bold, COMPANY_NAME_SIZE)
        company_h = len(company_lines) * COMPANY_LINE_HEIGHT

        y = HEADER_TOP + max(company_h, LOGO_BLOCK_H) + COMPANY_EXTRA_GAP

        # ── Invoice Summary strip across the full table width ──
        fields = self._header_fields(invoice)
        summary_rows = []
        summary_h = 0.0
        for label, value in fields['summary']:
            lines = self._wrap_text(value, SUMMARY_COL_W, font, FIELD_VALUE_SIZE)
            summary_rows.append((label, lines))
            summary_h = max(summary_h, LABEL_LINE_HEIGHT
                            + len(lines) * FIELD_LINE_HEIGHT)

        summary_title_y = y
        y += SECTION_TITLE_H + summary_h + HEADER_BLOCK_GAP

        # ── Seller and Buyer blocks, side by side ──
        seller_rows, seller_h = stack(fields['seller'], SELLER_BLOCK_W)
        buyer_rows, buyer_h = stack(fields['buyer'], BUYER_BLOCK_W)

        seller_title_y = y
        y += SECTION_TITLE_H + max(seller_h, buyer_h)

        return {
            'company_lines': company_lines,
            'company_y': HEADER_TOP,
            'seller_rows': seller_rows,
            'buyer_rows': buyer_rows,
            'seller_title_y': seller_title_y,
            'seller_fields_y': seller_title_y + SECTION_TITLE_H,
            'summary_rows': summary_rows,
            'summary_title_y': summary_title_y,
            'summary_fields_y': summary_title_y + SECTION_TITLE_H,
            'bottom': y + TABLE_GAP,
        }

    def _compute_header_bottom(self, invoice: Invoice, font: str) -> float:
        """Distance from the page top to where the first-page header ends."""
        return self._compute_header_metrics(invoice, font)['bottom']

    def _draw_first_page_header(
        self, c: canvas_module.Canvas, invoice: Invoice, font: str
    ) -> None:
        """Draw the company name, Invoice Summary and Seller/Buyer blocks.

        Long values (e.g. an address) wrap within their column; the blocks
        grow downwards and the table start follows (_compute_header_metrics).
        """
        m = self._compute_header_metrics(invoice, font)
        bold = self._font(bold=True)

        # Company name — top-left, bold, wrapped clear of the logo/QR block
        c.setFont(bold, COMPANY_NAME_SIZE)
        c.setFillColor(BLACK)
        y = PAGE_HEIGHT - m['company_y'] - COMPANY_NAME_SIZE * 0.8
        for line in m['company_lines']:
            c.drawString(TABLE_LEFT, y, line)
            y -= COMPANY_LINE_HEIGHT

        # Section titles with a hairline rule beneath
        self._draw_section_title(
            c, "Invoice Summary", TABLE_LEFT, TABLE_WIDTH,
            m['summary_title_y'], bold)
        self._draw_section_title(
            c, "Seller Information", TABLE_LEFT, SELLER_BLOCK_W,
            m['seller_title_y'], bold)
        self._draw_section_title(
            c, "Buyer Information", BUYER_BLOCK_X, BUYER_BLOCK_W,
            m['seller_title_y'], bold)

        # Invoice Summary — one label/value column per field
        for i, (label, lines) in enumerate(m['summary_rows']):
            x = TABLE_LEFT + i * (SUMMARY_COL_W + SUMMARY_COL_GAP)
            self._draw_header_fields(c, font, [(label, lines)], x,
                                     m['summary_fields_y'], bold)

        # Seller / Buyer fields
        self._draw_header_fields(c, font, m['seller_rows'], TABLE_LEFT,
                                 m['seller_fields_y'], bold)
        self._draw_header_fields(c, font, m['buyer_rows'], BUYER_BLOCK_X,
                                 m['seller_fields_y'], bold)

    def _draw_section_title(
        self, c: canvas_module.Canvas, text: str, x: float, width: float,
        top: float, bold: str
    ) -> None:
        """Draw a section title and its rule at `top` (from the page top)."""
        c.setFont(bold, SECTION_HEADER_SIZE)
        c.setFillColor(BLACK)
        c.drawString(x, PAGE_HEIGHT - top - SECTION_HEADER_SIZE * 0.8, text)
        self._draw_hline(c, x, x + width,
                         PAGE_HEIGHT - (top + SECTION_HEADER_SIZE + SECTION_RULE_GAP),
                         line_width=0.5)

    def _draw_header_fields(
        self, c: canvas_module.Canvas, font: str, rows: list,
        x: float, top: float, bold: str
    ) -> None:
        """Draw stacked label/value fields downwards from `top`."""
        y = top
        for label, lines in rows:
            c.setFont(bold, FIELD_LABEL_SIZE)
            c.setFillColor(BLACK)
            c.drawString(x, PAGE_HEIGHT - y - FIELD_LABEL_SIZE * 0.8, label)
            y += LABEL_LINE_HEIGHT

            c.setFont(font, FIELD_VALUE_SIZE)
            for line in lines:
                c.drawString(x, PAGE_HEIGHT - y - FIELD_VALUE_SIZE * 0.8, line)
                y += FIELD_LINE_HEIGHT

            y += FIELD_GAP

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
        is_last: bool,
        start_sr_no: int = 1,
        totals_data: Optional[list] = None,
        layout: Optional[dict] = None
    ) -> None:
        """Draw the complete table with grid lines, headers, data rows, and totals."""
        if layout is None:
            layout = self._full_layout()
        bold = self._font(bold=True)
        y_top = PAGE_HEIGHT - y_start  # Convert to canvas Y
        current_y = y_top
        xs = layout['xs']
        widths = layout['widths']

        # ── Table header row (labels wrapped to their column width) ──
        header_h = self._header_height(layout)
        header_y_bottom = current_y - header_h

        # Draw header grid
        self._draw_grid_rect(c, TABLE_LEFT, current_y, TABLE_RIGHT, header_y_bottom,
                             line_width=1.0, fill=False)
        # Vertical lines in header
        for x in xs[1:-1]:
            self._draw_vline(c, x, current_y, header_y_bottom, line_width=1.0)

        # Header text, vertically centred within the header row
        c.setFillColor(BLACK)
        size = self._header_size(layout)
        for j, lines in enumerate(self._header_lines(layout, size)):
            block_h = len(lines) * TABLE_HEADER_LINE_HEIGHT
            line_top = current_y - (header_h - block_h) / 2.0
            for i, line in enumerate(lines):
                self._draw_cell_str(
                    c, line, xs[j],
                    line_top - i * TABLE_HEADER_LINE_HEIGHT - size * 0.8,
                    widths[j], bold, size, 'C')

        current_y = header_y_bottom

        # ── Data rows ──
        for idx, (item, rh) in enumerate(zip(items, row_heights)):
            row_bottom = current_y - rh
            sr_no = start_sr_no + idx

            # Row horizontal borders
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, current_y, line_width=1.0)
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, row_bottom, line_width=0.5)

            # Vertical lines through row
            for x in xs:
                self._draw_vline(c, x, current_y, row_bottom, line_width=1.0)

            # Cell content
            row_data = self._build_item_row(item, sr_no)
            c.setFont(font, TABLE_DATA_SIZE)
            c.setFillColor(BLACK)

            for j, col_idx in enumerate(layout['indices']):
                cell_str = str(row_data[col_idx])
                col_w = widths[j]
                align = layout['aligns'][j]
                col_x = xs[j]

                # Numbers are shrunk to fit (or wrapped at their commas);
                # text wraps at the base size.
                size, lines = self._cell_draw(cell_str, col_w, font, TABLE_DATA_SIZE)
                # Draw each line top-aligned within the cell
                line_y = current_y - CELL_PADDING_TOP - CELL_LINE_HEIGHT * 0.8
                for line in lines:
                    if line_y < row_bottom + CELL_PADDING_TOP:
                        break  # Truncate if text exceeds row height
                    self._draw_text_aligned(c, line, col_x, line_y, col_w,
                                            font, size, align)
                    line_y -= CELL_LINE_HEIGHT

            current_y = row_bottom

        # ── Totals row (only on last page) ──
        if is_last and totals_data:
            # Compute row height from the actual totals data being displayed
            max_lines = 1
            for j, col_idx in enumerate(layout['indices']):
                if col_idx < TOTALS_MERGE_COLS:
                    continue  # Skip merged columns
                _, lines = self._cell_draw(str(totals_data[col_idx]),
                                           widths[j], bold, TOTALS_VALUE_SIZE)
                max_lines = max(max_lines, len(lines))
            totals_rh = max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2 + 6
            totals_bottom = current_y - totals_rh

            # Top border of totals row (thicker to separate from data)
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, current_y, line_width=1.5)
            # Bottom border
            self._draw_hline(c, TABLE_LEFT, TABLE_RIGHT, totals_bottom, line_width=0.5)

            # Vertical lines: only the merged cell's outer edges and the
            # numeric total columns — no internal lines inside the merged
            # "Total:" area (it would look like empty columns).
            for x in [xs[0]] + xs[TOTALS_MERGE_COLS:]:
                self._draw_vline(c, x, current_y, totals_bottom, line_width=1.0)

            # Merged cell: the first TOTALS_MERGE_COLS columns (Sr. No.
            # through Rate) show "Total:". Those columns are never hidden, so
            # xs[0] and xs[TOTALS_MERGE_COLS] are their outer edges.
            merge_left = xs[0]
            merge_right = xs[TOTALS_MERGE_COLS]
            self._draw_hline(c, merge_left, merge_right, current_y, line_width=1.5)
            self._draw_hline(c, merge_left, merge_right, totals_bottom, line_width=0.5)

            # Text position — use same offset as data rows for consistency
            text_offset = CELL_PADDING_TOP + CELL_LINE_HEIGHT * 0.8
            totals_label_y = current_y - text_offset
            totals_val_y = current_y - text_offset

            # "Total:" label — centered in the merged cell
            c.setFont(bold, TOTALS_LABEL_SIZE)
            c.setFillColor(BLACK)
            self._draw_text_aligned(c, "Total:", merge_left, totals_label_y,
                                    merge_right - merge_left, bold, TOTALS_LABEL_SIZE, 'C')

            # Numeric totals in the visible columns after the merged cell
            c.setFont(bold, TOTALS_VALUE_SIZE)
            for j, col_idx in enumerate(layout['indices']):
                if col_idx < TOTALS_MERGE_COLS:
                    continue
                col_x = xs[j]
                col_w = widths[j]
                align = layout['aligns'][j]

                cell_str = str(totals_data[col_idx])
                size, lines = self._cell_draw(cell_str, col_w, bold, TOTALS_VALUE_SIZE)
                line_y = totals_val_y
                for line in lines:
                    if line_y < totals_bottom + 2:
                        break
                    self._draw_text_aligned(c, line, col_x, line_y, col_w,
                                            bold, size, align)
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

    def _compute_row_heights(
        self, items: list, font: str, layout: Optional[dict] = None
    ) -> List[float]:
        """Compute the required height for each data row.

        Uses the same cell layout as _draw_table_grid, so a row is exactly as
        tall as the content drawn into it.
        """
        if layout is None:
            layout = self._full_layout()
        heights = []
        for item in items:
            row_data = self._build_item_row(item, 1)
            max_lines = 1
            for j, col_idx in enumerate(layout['indices']):
                _, lines = self._cell_draw(str(row_data[col_idx]),
                                           layout['widths'][j], font, TABLE_DATA_SIZE)
                max_lines = max(max_lines, len(lines))
            rh = max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2
            heights.append(max(rh, 14.0))  # Minimum row height
        return heights

    def _calc_totals_height(
        self, items: list, font: str, layout: Optional[dict] = None
    ) -> float:
        """Calculate totals row height."""
        if layout is None:
            layout = self._full_layout()
        totals_data = self._build_totals_row(items)
        max_lines = 1
        for j, col_idx in enumerate(layout['indices']):
            if col_idx < TOTALS_MERGE_COLS:
                continue  # Skip merged columns
            _, lines = self._cell_draw(str(totals_data[col_idx]),
                                       layout['widths'][j], font, TOTALS_VALUE_SIZE)
            max_lines = max(max_lines, len(lines))
        # +6 matches the height _draw_table_grid gives the drawn totals row
        return max_lines * CELL_LINE_HEIGHT + CELL_PADDING_TOP * 2 + 6

    def _full_layout(self) -> dict:
        """Layout with every column visible (used when none is provided)."""
        return self._layout_for(list(range(N_COLS)))

    # ── Data builders ──────────────────────────────────────────────────

    @staticmethod
    def _num(value) -> float:
        """Coerce a raw item value to float, defaulting to 0."""
        try:
            return float(value or 0)
        except (ValueError, TypeError):
            return 0

    def _line_total(self, item: dict) -> float:
        """Net payable for a line item (Retail Price not included).

        Sales Value + Sales Tax + Extra Tax + Further Tax + FED
        − ST WHT − Discount.
        """
        num = self._num
        return (num(item.get('value_sales_excluding_st')) + num(item.get('sales_tax_applicable'))
                + num(item.get('extra_tax')) + num(item.get('further_tax')) + num(item.get('fed_payable'))
                - num(item.get('sales_tax_withheld_at_source')) - num(item.get('discount')))

    def _total_incl_advance_tax(self, item: dict) -> float:
        """Total Amount plus the Income Tax Value (advance income tax).

        _line_total leaves out the income tax withheld under FTN 236G/236H,
        so it is added back here: the amount payable including advance tax.
        """
        return self._line_total(item) + self._num(item.get('withholding_tax_amount'))

    def _build_item_row(self, item: dict, sr_no: int) -> list:
        """Build a table row from an invoice item dict."""
        # Unit price; fall back to value/quantity for older invoices that
        # predate the item_rate field.
        item_rate = item.get('item_rate')
        if item_rate is None:
            qty = float(item.get('quantity') or 0)
            item_rate = (float(item.get('value_sales_excluding_st') or 0) / qty) if qty else 0
        return [
            str(sr_no),
            str(item.get('hs_code', '')),
            str(item.get('product_description', '')),
            str(item.get('sale_type', '')),
            self._fmt_num(item.get('quantity', 0)),
            self._fmt_num(item_rate),
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
            self._fmt_num(self._line_total(item)),
            str(item.get('income_tax_type', '') or ''),
            self._fmt_num(item.get('withholding_tax_amount', 0)),
            self._fmt_num(self._total_incl_advance_tax(item)),
        ]

    def _build_totals_row(self, items: list) -> list:
        """Build the totals summary row."""
        sums = {}
        for field in ['value_sales_excluding_st', 'fixed_notified_value_or_retail_price',
                       'sales_tax_applicable', 'extra_tax', 'further_tax',
                       'fed_payable', 'sales_tax_withheld_at_source',
                       'withholding_tax_amount', 'discount']:
            sums[field] = sum(float(it.get(field, 0) or 0) for it in items)

        return [
            '',  # Sr. No.
            '',  # HS Code
            '',  # Product Description
            '',  # Sales Type
            '',  # Quantity
            '',  # Item Rate (unit price — not summed, part of merged label cell)
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
            self._fmt_num(sum(self._line_total(it) for it in items)),
            '',  # Income Tax Type (text column — no total)
            self._fmt_num(sums['withholding_tax_amount']),
            self._fmt_num(sum(self._total_incl_advance_tax(it) for it in items)),
        ]

    # ── FBR compliance elements ──────────────────────────────────────

    def _draw_fbr_logo_and_qr(
        self, c: canvas_module.Canvas, usin: str, font: str
    ) -> None:
        """Draw FBR logo and QR code side by side at top-right of the first page."""
        logo = self._load_fbr_logo()
        qr_img = self._generate_qr_code(usin) if usin else None

        if logo is None and qr_img is None:
            return

        logo_w, logo_h = LOGO_MAX_W, LOGO_MAX_H
        if logo is not None:
            lw, lh = logo.size
            aspect = lw / lh
            logo_h = LOGO_MAX_W / aspect
            if logo_h > LOGO_MAX_H:
                logo_h = LOGO_MAX_H
                logo_w = logo_h * aspect
            else:
                logo_w = LOGO_MAX_W
        else:
            logo_w = 0.0

        total_w = logo_w + (LOGO_QR_GAP + QR_SIZE if qr_img else 0)
        start_x = TABLE_RIGHT - total_w
        top = HEADER_TOP + 2.0  # aligned with the company name

        if logo is not None and logo_w:
            try:
                c.drawInlineImage(logo, start_x, PAGE_HEIGHT - top - logo_h,
                                  width=logo_w, height=logo_h,
                                  preserveAspectRatio=True)
            except Exception as e:
                logger.warning(f"Could not draw FBR logo: {e}")

        if qr_img is not None:
            try:
                qr_x = start_x + logo_w + LOGO_QR_GAP
                c.drawInlineImage(qr_img, qr_x, PAGE_HEIGHT - top - QR_SIZE,
                                  width=QR_SIZE, height=QR_SIZE,
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
        c.drawString(TABLE_RIGHT - tw, FOOTER_BASELINE, text)
