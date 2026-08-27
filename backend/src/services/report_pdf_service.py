"""
Report PDF generation service (platypus).

Generates a professional A4 portrait summary report for a date range:
- Title / generated-at header block
- Period, business, environment info block
- Full summary table (all tax totals, reusing the exact numbers the JSON endpoint returns)
- Multi-page invoice details table with a repeating header row
- Grand-total row
- "Page X of Y" footers via a two-pass numbered canvas

Uses the installed reportlab platypus engine (part of reportlab>=4.0.0,
no new dependency). Font and number formatting are shared with the
existing FBR invoice PDFService (FONT_PATH, fmt_num) so both documents
render identically.
"""
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional

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

from .pdf_service import FONT_PATH, fmt_num

logger = logging.getLogger(__name__)

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
# full tax picture. Keys must exist in ReportSummary.
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


class ReportPDFService:
    """Service for generating date-range invoice report PDFs."""

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
        generated_at: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate the report PDF and return it as bytes.

        `summary` and `rows` come from report_service.build_report_data,
        so the PDF totals always match the JSON endpoint's totals.
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
            title="Tax Invoice Report",
            author="Taxntec",
            canvasmaker=_NumberedCanvas,
        )

        story = []

        # ── Title + generated-at (same line) ──
        title_row = Table(
            [[Paragraph("Tax Invoice Report", styles['title']),
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
        story.append(title_row)
        story.append(Spacer(1, 4))
        story.append(Table(
            [['']],
            colWidths=[CONTENT_WIDTH],
            hAlign='LEFT',
            style=TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 1, BRAND_GREEN),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]),
        ))

        # ── Info block ──
        env_label = environment if environment else "All"
        story.append(Spacer(1, 10))
        for line in (
            f"Period: {date_from} to {date_to}",
            f"Business: {business_name}",
            f"Environment: {env_label}",
        ):
            story.append(Paragraph(line, styles['info']))

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
            logger.error(f"Failed to build report PDF: {e}")
            raise

        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(
            f"Generated report PDF: {len(pdf_bytes)} bytes, "
            f"{len(rows)} invoices, {date_from} to {date_to}"
        )
        return pdf_bytes

    # ── Table construction ────────────────────────────────────────────

    def _build_invoice_table(self, rows: List[Dict], summary: Dict, styles) -> Table:
        data = [[Paragraph(h, styles['header']) for h in COL_HEADERS]]

        if not rows:
            empty_style = ParagraphStyle('empty-row', parent=styles['empty'])
            data.append([Paragraph("No invoices found for the selected period", empty_style)]
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

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, GRID_GRAY),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND_GREEN_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]

        if rows:
            # Alternating row shading (skip header + grand total row)
            for r in range(1, len(data) - 1):
                if r % 2 == 0:
                    style_cmds.append(('BACKGROUND', (0, r), (-1, r), ROW_ALT))

            # Grand total row
            style_cmds += [
                ('SPAN', (0, total_row_idx), (5, total_row_idx)),
                ('BACKGROUND', (0, total_row_idx), (-1, total_row_idx), ROW_ALT),
                ('LINEABOVE', (0, total_row_idx), (-1, total_row_idx), 1, BRAND_GREEN),
            ]

        table.setStyle(TableStyle(style_cmds))
        return table
