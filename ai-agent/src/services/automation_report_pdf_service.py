"""
Automation report PDF generation service (platypus).

Generates professional A4 portrait reports for a date range over the
automation database:
- Invoice report: title / info header, full summary table (all tax totals,
  reusing the exact numbers the aggregation service returns), a multi-page
  invoice details table with a repeating header row, and a grand-total row.
- Party-wise report: the same header, then one row per customer with their
  invoice count and tax totals, and a grand-total row.
- Income tax report: the same header, then one row per income tax section
  (236G / 236H / None) with the rate applied, the number of invoices under
  it, and the sales value and withholding tax it was charged on.
- Party-wise income tax report: one row per customer *and* section, so the
  income tax position can be read per party.

Mirror of the main backend's ``report_pdf_service.py``: same header blocks,
palette, column geometry and footers, so an automation report and a manual
report are visually indistinguishable apart from the period and the filter
note they describe. The only difference is the data source — rows here come
from ``automation_report_service`` (automation payloads flattened out of the
``invoice_data`` JSON column), and the period is the scheduled-date range the
dashboard was filtered to.

All four share the title/info header blocks and the table styling, and end
with "Page X of Y" footers via a two-pass numbered canvas.

Uses the installed reportlab platypus engine (part of reportlab>=4.0.0,
no new dependency). Number formatting matches the main backend's
PDFService.fmt_num so both services render figures identically.
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape

import logging

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as canvas_module
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Same asset location convention as the invoice PDFService (src/../assets).
# The Unicode font is optional: when it is absent every report falls back to
# Helvetica, which is what the main backend does too.
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "NotoSansArabic-Regular.ttf"


def fmt_num(value) -> str:
    """Format a numeric value for display.

    Copied from the main backend's PDFService.fmt_num so an automation
    report formats money exactly like a manual one.
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


PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 x 841.89 pt

MARGIN_LEFT = 36
MARGIN_RIGHT = 36
MARGIN_TOP = 54
MARGIN_BOTTOM = 54
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 523 pt

# Brand / palette (matches frontend theme tokens)
BRAND_GREEN = colors.HexColor('#008060')
BRAND_GREEN_DARK = colors.HexColor('#00a876')
TEXT_PRIMARY = colors.HexColor('#202223')
TEXT_MUTED = colors.HexColor('#6d7175')
GRID_GRAY = colors.HexColor('#D3D3D3')
ROW_ALT = colors.HexColor('#f4f6f8')
WHITE = colors.white

# Summary block rows: (label, summary key, is_currency).
# Mirrors the report page's summary table, so PDF and UI show the same
# full tax picture. Keys must exist in the summary built by
# automation_report_service.build_report_data.
SUMMARY_ROWS = [
    ("Total Number of Invoices", 'total_invoices', False),
    ("Total Sales Value Excl. Tax", 'sales_value_excluding_st', True),
    ("Total Sales Tax", 'sales_tax', True),
    ("Total Sales Tax Withheld at Source", 'sales_tax_withheld_at_source', True),
    ("Total Further Tax", 'further_tax', True),
    ("Total Extra Tax", 'extra_tax', True),
    ("Total FED Payable", 'fed_payable', True),
    ("Total Withholding Tax", 'withholding_tax_amount', True),
    ("Total Discount", 'discount', True),
    ("Total Value Incl. Tax", 'value_including_tax', True),
]

# Invoice details table columns (widths sum to CONTENT_WIDTH)
COLUMNS = [
    ('Sr.', 26, TA_CENTER),
    ('Invoice #', 68, TA_LEFT),
    ('FBR Ref #', 56, TA_LEFT),
    ('Invoice Date', 50, TA_CENTER),
    ('Type', 54, TA_LEFT),
    ('Buyer', 92, TA_LEFT),
    ('Sales Value Excl. Tax', 48, TA_RIGHT),
    ('Sales Tax', 44, TA_RIGHT),
    ('Further Tax', 42, TA_RIGHT),
    ('Value Incl. Tax', 43, TA_RIGHT),
]
COL_WIDTHS = [c[1] for c in COLUMNS]
COL_HEADERS = [c[0] for c in COLUMNS]

# Party-wise (per-customer) table columns (widths sum to CONTENT_WIDTH).
# One row per customer, so the table is far narrower than the invoice one
# and the money columns can be wide enough to read at a glance.
PARTY_COLUMNS = [
    ('Sr.', 26, TA_CENTER),
    ('Customer', 150, TA_LEFT),
    ('NTN/CNIC', 75, TA_LEFT),
    ('Invoices', 42, TA_CENTER),
    ('Sales Value Excl. Tax', 60, TA_RIGHT),
    ('Sales Tax', 55, TA_RIGHT),
    ('Further Tax', 55, TA_RIGHT),
    ('Value Incl. Tax', 60, TA_RIGHT),
]
PARTY_COL_WIDTHS = [c[1] for c in PARTY_COLUMNS]
PARTY_COL_HEADERS = [c[0] for c in PARTY_COLUMNS]

# Income tax summary table: one row per section (236G / 236H / None) with the
# rate applied and the values it was charged on. Widths sum to CONTENT_WIDTH.
INCOME_TAX_COLUMNS = [
    ('Sr.', 30, TA_CENTER),
    ('Income Tax Type', 108, TA_LEFT),
    ('Rate', 60, TA_CENTER),
    ('Invoices', 65, TA_CENTER),
    ('Sales Value Excl. Tax', 130, TA_RIGHT),
    ('Withholding Tax', 130, TA_RIGHT),
]
INCOME_TAX_COL_WIDTHS = [c[1] for c in INCOME_TAX_COLUMNS]
INCOME_TAX_COL_HEADERS = [c[0] for c in INCOME_TAX_COLUMNS]

# Party-wise income tax table: one row per (customer, section) pair, so the
# section is explicit on every row rather than being a column group that
# breaks for a customer selling under both. Widths sum to CONTENT_WIDTH.
PARTY_INCOME_TAX_COLUMNS = [
    ('Sr.', 28, TA_CENTER),
    ('Customer', 145, TA_LEFT),
    ('NTN/CNIC', 70, TA_LEFT),
    ('Type', 55, TA_LEFT),
    ('Invoices', 45, TA_CENTER),
    ('Sales Value Excl. Tax', 90, TA_RIGHT),
    ('Withholding Tax', 90, TA_RIGHT),
]
PARTY_INCOME_TAX_COL_WIDTHS = [c[1] for c in PARTY_INCOME_TAX_COLUMNS]
PARTY_INCOME_TAX_COL_HEADERS = [c[0] for c in PARTY_INCOME_TAX_COLUMNS]


def _fmt_rate(rate: float) -> str:
    """Withholding rate as a percentage: 0.001 -> '0.1%', 0.005 -> '0.5%'."""
    return f"{rate * 100:g}%"


class _NumberedCanvas(canvas_module.Canvas):
    """Canvas that stamps a 'Page X of Y' footer after the document is built."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_footer(num_pages)
            super().showPage()
        super().save()

    def _draw_page_footer(self, page_count: int):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(TEXT_MUTED)
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawCentredString(PAGE_WIDTH / 2, 30, text)
        self.restoreState()


class AutomationReportPDFService:
    """Service for generating date-range automation report PDFs."""

    def __init__(self):
        self._fonts_registered = False
        self._unicode_font: Optional[str] = None

    # ── Fonts (same policy as PDFService) ─────────────────────────────

    def _register_fonts(self) -> str:
        """Register fonts; returns the base font name (unicode or Helvetica)."""
        if self._fonts_registered and self._unicode_font:
            return self._unicode_font

        if FONT_PATH.exists():
            try:
                pdfmetrics.registerFont(TTFont('NotoSansArabic', str(FONT_PATH)))
                self._unicode_font = 'NotoSansArabic'
            except Exception:
                self._unicode_font = 'Helvetica'
        else:
            self._unicode_font = 'Helvetica'

        self._fonts_registered = True
        return self._unicode_font

    def _base_font(self) -> str:
        return self._register_fonts()

    def _bold_font(self) -> str:
        font = self._register_fonts()
        if font == 'Helvetica':
            return 'Helvetica-Bold'
        return font

    # ── Styles ────────────────────────────────────────────────────────

    def _styles(self):
        base = self._base_font()
        bold = self._bold_font()
        return {
            'title': ParagraphStyle(
                'report-title', fontName=bold, fontSize=16,
                textColor=BRAND_GREEN, leading=20),
            'generated': ParagraphStyle(
                'report-generated', fontName=base, fontSize=8,
                textColor=TEXT_MUTED, alignment=TA_RIGHT, leading=10),
            'info': ParagraphStyle(
                'report-info', fontName=base, fontSize=9.5,
                textColor=TEXT_PRIMARY, leading=13),
            'summary_label': ParagraphStyle(
                'report-summary-label', fontName=base, fontSize=9.5,
                textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=12),
            'summary_value': ParagraphStyle(
                'report-summary-value', fontName=bold, fontSize=9.5,
                textColor=TEXT_PRIMARY, alignment=TA_RIGHT, leading=12),
            'header': ParagraphStyle(
                'report-table-header', fontName=bold, fontSize=8,
                textColor=WHITE, alignment=TA_CENTER, leading=10),
            'cell_left': ParagraphStyle(
                'report-cell-left', fontName=base, fontSize=7.5,
                textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=9),
            'cell_center': ParagraphStyle(
                'report-cell-center', fontName=base, fontSize=7.5,
                textColor=TEXT_PRIMARY, alignment=TA_CENTER, leading=9),
            'cell_right': ParagraphStyle(
                'report-cell-right', fontName=base, fontSize=7.5,
                textColor=TEXT_PRIMARY, alignment=TA_RIGHT, leading=9),
            'cell_bold_right': ParagraphStyle(
                'report-cell-bold-right', fontName=bold, fontSize=8,
                textColor=TEXT_PRIMARY, alignment=TA_RIGHT, leading=10),
            'cell_bold_center': ParagraphStyle(
                'report-cell-bold-center', fontName=bold, fontSize=8,
                textColor=TEXT_PRIMARY, alignment=TA_CENTER, leading=10),
            'empty': ParagraphStyle(
                'report-empty', fontName=base, fontSize=9,
                textColor=TEXT_MUTED, alignment=TA_CENTER, leading=12),
        }

    # ── Public API ────────────────────────────────────────────────────

    def generate_report_pdf(
        self,
        *,
        date_from: str,
        date_to: str,
        summary: Dict,
        rows: List[Dict],
        business_name: str,
        environment: Optional[str] = None,
        filter_note: Optional[str] = None,
        generated_at: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate the report PDF and return it as bytes.

        `summary` and `rows` come from
        automation_report_service.build_report_data, so the PDF totals
        always match the aggregation the other downloads use.

        `filter_note` describes the dashboard filters applied on top of the
        period (e.g. "Status: validated | Customer: Ali & Sons"), printed in
        the info block so a filtered report is never mistaken for a full one.
        """
        styles = self._styles()
        generated_at = generated_at or datetime.utcnow()
        generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Automation Invoice Report",
            author="Taxntec",
            canvasmaker=_NumberedCanvas,
        )

        story = []
        story.extend(self._title_block(styles, "Automation Invoice Report", generated_str))
        story.extend(self._info_block(
            styles,
            date_from=date_from,
            date_to=date_to,
            business_name=business_name,
            environment=environment,
            filter_note=filter_note,
        ))

        # ── Summary block ──
        story.append(Spacer(1, 12))
        story.append(Paragraph("Summary", styles['info']))
        story.append(Spacer(1, 4))
        summary_data = []
        for label, key, is_currency in SUMMARY_ROWS:
            value = summary.get(key, 0)
            display = fmt_num(value) if is_currency else str(value)
            summary_data.append([
                Paragraph(label, styles['summary_label']),
                Paragraph(display, styles['summary_value']),
            ])
        summary_table = Table(summary_data, colWidths=[220, 120], hAlign='LEFT')
        summary_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, len(summary_data) - 1), (-1, len(summary_data) - 1), 1, BRAND_GREEN),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # ── Invoice details table ──
        story.append(self._build_invoice_table(rows, summary, styles))

        try:
            doc.build(story)
        except Exception as e:
            logger.error(f"Failed to build automation report PDF: {e}")
            raise

        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(
            f"Generated automation report PDF: {len(pdf_bytes)} bytes, "
            f"{len(rows)} invoices, {date_from} to {date_to}"
        )
        return pdf_bytes

    def generate_party_wise_pdf(
        self,
        *,
        date_from: str,
        date_to: str,
        parties: List[Dict],
        totals: Dict,
        business_name: str,
        environment: Optional[str] = None,
        filter_note: Optional[str] = None,
        generated_at: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate the party-wise (per-customer) sales PDF and return it as bytes.

        One row per customer with its invoice count and tax totals, then a
        grand-total row. `parties` and `totals` come from
        automation_report_service.build_party_wise_report, so a customer's
        figures here always match the same figures in the invoice report.

        Shares the title/info header with generate_report_pdf, so both
        documents are styled identically and carry the same period, business
        and filter context.
        """
        styles = self._styles()
        generated_at = generated_at or datetime.utcnow()
        generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Automation Party-wise Sales Report",
            author="Taxntec",
            canvasmaker=_NumberedCanvas,
        )

        story = []
        story.extend(self._title_block(
            styles, "Automation Party-wise Sales Report", generated_str))
        story.extend(self._info_block(
            styles,
            date_from=date_from,
            date_to=date_to,
            business_name=business_name,
            environment=environment,
            filter_note=filter_note,
        ))
        story.append(Spacer(1, 14))

        # ── Party-wise totals table ──
        story.append(self._build_party_table(parties, totals, styles))

        try:
            doc.build(story)
        except Exception as e:
            logger.error(f"Failed to build party-wise automation report PDF: {e}")
            raise

        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(
            f"Generated party-wise automation report PDF: {len(pdf_bytes)} bytes, "
            f"{len(parties)} parties, {date_from} to {date_to}"
        )
        return pdf_bytes

    def generate_income_tax_pdf(
        self,
        *,
        date_from: str,
        date_to: str,
        sections: List[Dict],
        totals: Dict,
        business_name: str,
        environment: Optional[str] = None,
        filter_note: Optional[str] = None,
        generated_at: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate the income tax (236G / 236H) report PDF and return it as bytes.

        `sections` and `totals` come from
        automation_report_service.build_income_tax_report, so the sales value
        and withholding tax here reconcile with the invoice report's totals.

        Shares the title/info header with the other report documents, so the
        period, business, environment and any active filter read the same way
        on every download.
        """
        styles = self._styles()
        generated_at = generated_at or datetime.utcnow()
        generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Automation Income Tax Report",
            author="Taxntec",
            canvasmaker=_NumberedCanvas,
        )

        story = []
        story.extend(self._title_block(
            styles, "Automation Income Tax Report", generated_str))
        story.extend(self._info_block(
            styles,
            date_from=date_from,
            date_to=date_to,
            business_name=business_name,
            environment=environment,
            filter_note=filter_note,
        ))
        story.append(Spacer(1, 14))

        story.append(self._build_income_tax_table(sections, totals, styles))

        try:
            doc.build(story)
        except Exception as e:
            logger.error(f"Failed to build income tax automation report PDF: {e}")
            raise

        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(
            f"Generated income tax automation report PDF: {len(pdf_bytes)} bytes, "
            f"{len(sections)} sections, {date_from} to {date_to}"
        )
        return pdf_bytes

    def generate_party_wise_income_tax_pdf(
        self,
        *,
        date_from: str,
        date_to: str,
        parties: List[Dict],
        totals: Dict,
        business_name: str,
        environment: Optional[str] = None,
        filter_note: Optional[str] = None,
        generated_at: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate the party-wise income tax PDF and return it as bytes.

        One row per (customer, income tax section) with the sales value and
        withholding tax reported under that section, then a grand-total row.
        `parties` and `totals` come from
        automation_report_service.build_party_wise_income_tax_report.
        """
        styles = self._styles()
        generated_at = generated_at or datetime.utcnow()
        generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Automation Party-wise Income Tax Report",
            author="Taxntec",
            canvasmaker=_NumberedCanvas,
        )

        story = []
        story.extend(self._title_block(
            styles, "Automation Party-wise Income Tax Report", generated_str))
        story.extend(self._info_block(
            styles,
            date_from=date_from,
            date_to=date_to,
            business_name=business_name,
            environment=environment,
            filter_note=filter_note,
        ))
        story.append(Spacer(1, 14))

        story.append(self._build_party_income_tax_table(parties, totals, styles))

        try:
            doc.build(story)
        except Exception as e:
            logger.error(f"Failed to build party-wise income tax automation report PDF: {e}")
            raise

        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(
            f"Generated party-wise income tax automation report PDF: {len(pdf_bytes)} bytes, "
            f"{len(parties)} parties, {date_from} to {date_to}"
        )
        return pdf_bytes

    # ── Header blocks (shared by every report document) ───────────────

    def _title_block(self, styles, title: str, generated_str: str) -> List:
        """Document title with the generated-at stamp, over a brand rule."""
        title_row = Table(
            [[Paragraph(title, styles['title']),
              Paragraph(f"Generated: {generated_str}", styles['generated'])]],
            colWidths=[CONTENT_WIDTH - 160, 160],
            hAlign='LEFT',
        )
        title_row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        rule = Table(
            [['']],
            colWidths=[CONTENT_WIDTH],
            hAlign='LEFT',
            style=TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 1, BRAND_GREEN),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]),
        )

        return [title_row, Spacer(1, 4), rule]

    def _info_block(
        self,
        styles,
        *,
        date_from: str,
        date_to: str,
        business_name: str,
        environment: Optional[str],
        filter_note: Optional[str],
    ) -> List:
        """Period / business / environment lines, plus any active filter."""
        env_label = environment if environment else "All"
        info_lines = [
            f"Period: {date_from} to {date_to}",
            f"Business: {business_name}",
            f"Environment: {env_label}",
        ]
        if filter_note:
            # Paragraph parses a mini-XML subset, so a raw "&" in a customer
            # name ("Ali & Sons") would abort the build.
            info_lines.append(xml_escape(filter_note))

        return [Spacer(1, 10)] + [Paragraph(line, styles['info']) for line in info_lines]

    # ── Table construction ────────────────────────────────────────────

    def _table_style_cmds(self) -> List:
        """Style every report table shares: header band, grid, cell padding."""
        return [
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, GRID_GRAY),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND_GREEN_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]

    def _rows_and_total_style_cmds(
        self, data: List, total_row_idx: int, span_to: int
    ) -> List:
        """
        Alternating row shading plus the grand-total band: the label is
        merged across columns 0..span_to so the totals line up under the
        columns they belong to, and a brand rule closes the table off.
        """
        cmds = []
        for r in range(1, len(data) - 1):
            if r % 2 == 0:
                cmds.append(('BACKGROUND', (0, r), (-1, r), ROW_ALT))

        cmds += [
            ('SPAN', (0, total_row_idx), (span_to, total_row_idx)),
            ('BACKGROUND', (0, total_row_idx), (-1, total_row_idx), ROW_ALT),
            ('LINEABOVE', (0, total_row_idx), (-1, total_row_idx), 1, BRAND_GREEN),
        ]
        return cmds

    def _build_invoice_table(self, rows: List[Dict], summary: Dict, styles) -> Table:
        data = [[Paragraph(h, styles['header']) for h in COL_HEADERS]]

        if not rows:
            empty_style = ParagraphStyle('empty-row', parent=styles['empty'])
            data.append([Paragraph("No invoices found for the selected filters", empty_style)]
                        + [Paragraph('', styles['cell_center']) for _ in COL_HEADERS[1:]])
        else:
            for idx, row in enumerate(rows, 1):
                data.append([
                    Paragraph(str(idx), styles['cell_center']),
                    Paragraph(str(row.get('invoice_number', '')), styles['cell_left']),
                    Paragraph(str(row.get('fbr_reference_number') or ''), styles['cell_left']),
                    Paragraph(str(row.get('invoice_date', '')), styles['cell_center']),
                    Paragraph(str(row.get('invoice_type', '')), styles['cell_left']),
                    Paragraph(str(row.get('buyer_business_name', '')), styles['cell_left']),
                    Paragraph(fmt_num(row.get('sales_value_excluding_st', 0)), styles['cell_right']),
                    Paragraph(fmt_num(row.get('sales_tax', 0)), styles['cell_right']),
                    Paragraph(fmt_num(row.get('further_tax', 0)), styles['cell_right']),
                    Paragraph(fmt_num(row.get('value_including_tax', 0)), styles['cell_right']),
                ])

        total_row_idx = None
        if rows:
            total_row_idx = len(data)
            # SPAN merges columns 0-5; the top-left cell's content renders
            # across the merged region, so the label goes in cell (0, row).
            data.append(
                [Paragraph("Grand Total", styles['cell_bold_right'])]
                + [Paragraph('', styles['cell_center']) for _ in COL_HEADERS[1:6]]
                + [
                    Paragraph(fmt_num(summary.get('sales_value_excluding_st', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(summary.get('sales_tax', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(summary.get('further_tax', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(summary.get('value_including_tax', 0)), styles['cell_bold_right']),
                ]
            )

        table = Table(
            data,
            colWidths=COL_WIDTHS,
            repeatRows=1,
            hAlign='LEFT',
        )

        style_cmds = self._table_style_cmds()
        if rows:
            style_cmds += self._rows_and_total_style_cmds(data, total_row_idx, span_to=5)

        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_party_table(self, parties: List[Dict], totals: Dict, styles) -> Table:
        """
        Per-customer totals table: one row per party, then a grand-total row.

        The grand-total label spans Sr./Customer/NTN-CNIC so the customer's
        own name never sits next to a figure that isn't theirs; the invoice
        count keeps its own column, where it lines up with the party rows.
        """
        data = [[Paragraph(h, styles['header']) for h in PARTY_COL_HEADERS]]

        if not parties:
            data.append(
                [Paragraph("No invoices found for the selected filters", styles['empty'])]
                + [Paragraph('', styles['cell_center']) for _ in PARTY_COL_HEADERS[1:]]
            )
        else:
            for idx, party in enumerate(parties, 1):
                data.append([
                    Paragraph(str(idx), styles['cell_center']),
                    Paragraph(str(party.get('buyer_business_name', '')), styles['cell_left']),
                    Paragraph(str(party.get('buyer_ntn_cnic', '')), styles['cell_left']),
                    Paragraph(str(party.get('total_invoices', 0)), styles['cell_center']),
                    Paragraph(fmt_num(party.get('sales_value_excluding_st', 0)), styles['cell_right']),
                    Paragraph(fmt_num(party.get('sales_tax', 0)), styles['cell_right']),
                    Paragraph(fmt_num(party.get('further_tax', 0)), styles['cell_right']),
                    Paragraph(fmt_num(party.get('value_including_tax', 0)), styles['cell_right']),
                ])

        total_row_idx = None
        if parties:
            total_row_idx = len(data)
            data.append(
                [Paragraph("Grand Total", styles['cell_bold_right'])]
                + [Paragraph('', styles['cell_center']) for _ in PARTY_COL_HEADERS[1:3]]
                + [
                    Paragraph(str(totals.get('total_invoices', 0)), styles['cell_bold_center']),
                    Paragraph(fmt_num(totals.get('sales_value_excluding_st', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(totals.get('sales_tax', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(totals.get('further_tax', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(totals.get('value_including_tax', 0)), styles['cell_bold_right']),
                ]
            )

        table = Table(
            data,
            colWidths=PARTY_COL_WIDTHS,
            repeatRows=1,
            hAlign='LEFT',
        )

        style_cmds = self._table_style_cmds()
        if parties:
            style_cmds += self._rows_and_total_style_cmds(data, total_row_idx, span_to=2)

        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_income_tax_table(self, sections: List[Dict], totals: Dict, styles) -> Table:
        """
        Income tax summary: one row per section (236G / 236H / None), then the
        report-wide total.

        The grand-total label spans Sr./Type/Rate so the invoice count keeps
        its own column. Per-section counts count only the invoices that
        touched that section, so they can add up to more than the total when
        one invoice mixes sections; the total is the report's distinct count.
        """
        data = [[Paragraph(h, styles['header']) for h in INCOME_TAX_COL_HEADERS]]

        if not sections:
            data.append(
                [Paragraph("No invoices found for the selected filters", styles['empty'])]
                + [Paragraph('', styles['cell_center']) for _ in INCOME_TAX_COL_HEADERS[1:]]
            )
        else:
            for idx, section in enumerate(sections, 1):
                data.append([
                    Paragraph(str(idx), styles['cell_center']),
                    Paragraph(str(section.get('income_tax_type', '')), styles['cell_left']),
                    Paragraph(_fmt_rate(section.get('rate', 0)), styles['cell_center']),
                    Paragraph(str(section.get('total_invoices', 0)), styles['cell_center']),
                    Paragraph(fmt_num(section.get('sales_value_excluding_st', 0)), styles['cell_right']),
                    Paragraph(fmt_num(section.get('withholding_tax_amount', 0)), styles['cell_right']),
                ])

        total_row_idx = None
        if sections:
            total_row_idx = len(data)
            data.append(
                [Paragraph("Grand Total", styles['cell_bold_right'])]
                + [Paragraph('', styles['cell_center']) for _ in INCOME_TAX_COL_HEADERS[1:3]]
                + [
                    Paragraph(str(totals.get('total_invoices', 0)), styles['cell_bold_center']),
                    Paragraph(fmt_num(totals.get('sales_value_excluding_st', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(totals.get('withholding_tax_amount', 0)), styles['cell_bold_right']),
                ]
            )

        table = Table(
            data,
            colWidths=INCOME_TAX_COL_WIDTHS,
            repeatRows=1,
            hAlign='LEFT',
        )

        style_cmds = self._table_style_cmds()
        if sections:
            style_cmds += self._rows_and_total_style_cmds(data, total_row_idx, span_to=2)

        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_party_income_tax_table(
        self, parties: List[Dict], totals: Dict, styles
    ) -> Table:
        """
        Per-customer income tax table: one row per (customer, section), then a
        grand-total row.

        The grand-total label spans Sr./Customer/NTN-CNIC/Type so a customer's
        name never sits beside a figure that isn't theirs, and the invoice
        count keeps the column it lines up with in the party rows.
        """
        data = [[Paragraph(h, styles['header']) for h in PARTY_INCOME_TAX_COL_HEADERS]]

        if not parties:
            data.append(
                [Paragraph("No invoices found for the selected filters", styles['empty'])]
                + [Paragraph('', styles['cell_center']) for _ in PARTY_INCOME_TAX_COL_HEADERS[1:]]
            )
        else:
            for idx, party in enumerate(parties, 1):
                data.append([
                    Paragraph(str(idx), styles['cell_center']),
                    Paragraph(str(party.get('buyer_business_name', '')), styles['cell_left']),
                    Paragraph(str(party.get('buyer_ntn_cnic', '')), styles['cell_left']),
                    Paragraph(str(party.get('income_tax_type', '')), styles['cell_left']),
                    Paragraph(str(party.get('total_invoices', 0)), styles['cell_center']),
                    Paragraph(fmt_num(party.get('sales_value_excluding_st', 0)), styles['cell_right']),
                    Paragraph(fmt_num(party.get('withholding_tax_amount', 0)), styles['cell_right']),
                ])

        total_row_idx = None
        if parties:
            total_row_idx = len(data)
            data.append(
                [Paragraph("Grand Total", styles['cell_bold_right'])]
                + [Paragraph('', styles['cell_center']) for _ in PARTY_INCOME_TAX_COL_HEADERS[1:4]]
                + [
                    Paragraph(str(totals.get('total_invoices', 0)), styles['cell_bold_center']),
                    Paragraph(fmt_num(totals.get('sales_value_excluding_st', 0)), styles['cell_bold_right']),
                    Paragraph(fmt_num(totals.get('withholding_tax_amount', 0)), styles['cell_bold_right']),
                ]
            )

        table = Table(
            data,
            colWidths=PARTY_INCOME_TAX_COL_WIDTHS,
            repeatRows=1,
            hAlign='LEFT',
        )

        style_cmds = self._table_style_cmds()
        if parties:
            style_cmds += self._rows_and_total_style_cmds(data, total_row_idx, span_to=3)

        table.setStyle(TableStyle(style_cmds))
        return table
