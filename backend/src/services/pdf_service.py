"""
PDF generation service for FBR-compliant invoice printing.

This service generates PDF documents for transferred invoices with:
- Complete invoice data (header, line items, totals)
- FBR Digital Invoicing System logo
- QR code containing FBR-issued USIN for verification

All PDFs are generated on-demand (no storage) and support Unicode characters.
"""
from io import BytesIO
from pathlib import Path
from typing import Optional, Union
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from PIL import Image
import qrcode

from ..models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)

# Asset paths
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "NotoSansArabic-Regular.ttf"
LOGO_PATH = ASSETS_DIR / "fbr_logo.png"


class PDFService:
    """Service for generating FBR-compliant invoice PDFs."""

    def __init__(self):
        """Initialize PDF service and register fonts."""
        self._fonts_registered = False
        self._logo_cache: Optional[Image.Image] = None

    def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """
        Generate PDF for a single invoice.

        Args:
            invoice: Invoice object

        Returns:
            PDF bytes

        Raises:
            FileNotFoundError: If FBR logo or font file is missing
            ValueError: If invoice data is invalid or USIN is missing
        """
        # Validate invoice has required data
        if not invoice.items:
            raise ValueError("Invoice must have at least one item")

        # Extract invoice data from Invoice model
        invoice_data = {
            'invoiceRefNo': invoice.invoice_ref_no or invoice.external_id,
            'invoiceDate': invoice.invoice_date if invoice.invoice_date else '',
            'sellerBusinessName': invoice.seller_business_name or '',
            'sellerNTNCNIC': invoice.seller_ntn_cnic or '',
            'sellerProvince': invoice.seller_province or '',
            'sellerAddress': invoice.seller_address or '',
            'buyerBusinessName': invoice.buyer_business_name or '',
            'buyerNTNCNIC': invoice.buyer_ntn_cnic or '',
            'buyerProvince': invoice.buyer_province or '',
            'buyerAddress': invoice.buyer_address or '',
            'items': invoice.items,
            'invoiceType': invoice.invoice_type or '',
            'transactionTypeId': invoice.transaction_type_id or ''
        }

        # Extract USIN from fbr_reference_number (optional for non-posted invoices)
        usin = invoice.fbr_reference_number  # Will be None for non-posted invoices
        invoice_number = invoice.external_id

        # Validate items array
        items = invoice.items
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Invoice must have at least one line item")

        logger.info(
            f"Generating PDF for invoice {invoice_number}"
            f"{f' (USIN: {usin})' if usin else ' (no FBR data)'}"
        )

        try:
            # Create PDF buffer
            buffer = BytesIO()

            # Create canvas (A4 size)
            c = canvas.Canvas(buffer, pagesize=A4)
            page_width, page_height = A4

            # Define margins and working area
            margin = 0.75 * inch
            x = margin
            y = page_height - margin
            content_width = page_width - (2 * margin)

            # Register fonts
            self._register_fonts()

            # Add FBR compliance elements (logo at top right, QR code at bottom right)
            self._add_fbr_compliance_elements(c, usin, x, y)

            # Render invoice header
            y = self._render_invoice_header(c, invoice_data, x, y)

            # Render line items table
            y = self._render_line_items_table(c, items, x, y, content_width)

            # Render totals
            y = self._render_totals(c, invoice_data, x, y)

            # Finalize PDF
            c.showPage()
            c.save()

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(
                f"Successfully generated PDF for {invoice.source} "
                f"invoice {invoice_number} ({len(pdf_bytes)} bytes)"
            )

            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate PDF for invoice {invoice_number}: {e}")
            raise

    def generate_batch_pdf(self, invoices: list[Invoice]) -> bytes:
        """
        Generate PDF for multiple invoices with page breaks.

        Args:
            invoices: List of Invoice objects in selection order

        Returns:
            PDF bytes containing all invoices

        Raises:
            FileNotFoundError: If FBR logo or font file is missing
            ValueError: If any invoice data is invalid
        """
        if not invoices:
            raise ValueError("No invoices provided for batch PDF generation")

        if len(invoices) > 50:
            raise ValueError(f"Batch size exceeds maximum limit of 50 invoices (got {len(invoices)})")

        logger.info(f"Generating batch PDF for {len(invoices)} invoices")

        try:
            # Create PDF buffer
            buffer = BytesIO()

            # Create canvas (A4 size)
            c = canvas.Canvas(buffer, pagesize=A4)
            page_width, page_height = A4

            # Define margins and working area
            margin = 0.75 * inch
            x = margin
            content_width = page_width - (2 * margin)

            # Register fonts once for all invoices
            self._register_fonts()

            # Generate each invoice on a separate page
            for idx, invoice in enumerate(invoices):
                # Extract invoice data
                invoice_data = {
                    'invoiceRefNo': invoice.invoice_ref_no or invoice.external_id,
                    'invoiceDate': invoice.invoice_date if invoice.invoice_date else '',
                    'sellerBusinessName': invoice.seller_business_name or '',
                    'sellerNTNCNIC': invoice.seller_ntn_cnic or '',
                    'sellerProvince': invoice.seller_province or '',
                    'sellerAddress': invoice.seller_address or '',
                    'buyerBusinessName': invoice.buyer_business_name or '',
                    'buyerNTNCNIC': invoice.buyer_ntn_cnic or '',
                    'buyerProvince': invoice.buyer_province or '',
                    'buyerAddress': invoice.buyer_address or '',
                    'items': invoice.items,
                    'invoiceType': invoice.invoice_type or '',
                    'transactionTypeId': invoice.transaction_type_id or ''
                }

                items = invoice.items

                # Extract USIN from fbr_reference_number (optional for non-posted invoices)
                usin = invoice.fbr_reference_number  # Will be None for non-posted invoices
                invoice_number = invoice.external_id

                if not items:
                    raise ValueError(f"Invoice {invoice_number} has no line items")

                logger.debug(
                    f"Rendering invoice {idx + 1}/{len(invoices)}: "
                    f"{invoice_number}{f' (USIN: {usin})' if usin else ' (no FBR data)'}"
                )

                # Reset Y coordinate for new page
                y = page_height - margin

                # Add FBR compliance elements (logo at top right, QR code at bottom right)
                # Only add if USIN is available
                if usin:
                    self._add_fbr_compliance_elements(c, usin, x, y)

                # Render invoice header
                y = self._render_invoice_header(c, invoice_data, x, y)

                # Render line items table
                y = self._render_line_items_table(c, items, x, y, content_width)

                # Render totals
                y = self._render_totals(c, invoice_data, x, y)

                # Add page break (except for last invoice)
                if idx < len(invoices) - 1:
                    c.showPage()

            # Finalize PDF
            c.save()

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(
                f"Successfully generated batch PDF for {len(invoices)} invoices "
                f"({len(pdf_bytes)} bytes)"
            )

            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate batch PDF: {e}")
            raise

    def _register_fonts(self) -> None:
        """
        Register Unicode fonts for PDF generation.

        Registers Noto Sans Arabic for Urdu/Arabic character support.
        Falls back to Helvetica if font file is missing.
        """
        if self._fonts_registered:
            return

        if FONT_PATH.exists():
            try:
                pdfmetrics.registerFont(TTFont('NotoSansArabic', str(FONT_PATH)))
                self._fonts_registered = True
                logger.info(f"Registered Unicode font: {FONT_PATH}")
            except Exception as e:
                logger.warning(f"Failed to register font {FONT_PATH}: {e}. Falling back to Helvetica.")
                self._fonts_registered = True  # Mark as registered to avoid retry
        else:
            logger.warning(f"Font file not found at {FONT_PATH}. Using Helvetica (limited Unicode support).")
            self._fonts_registered = True

    def _load_fbr_logo(self) -> Image.Image:
        """
        Load FBR Digital Invoicing System logo.

        Returns:
            PIL Image object

        Raises:
            FileNotFoundError: If logo file not found at expected path
        """
        # Return cached logo if already loaded
        if self._logo_cache is not None:
            return self._logo_cache

        if not LOGO_PATH.exists():
            error_msg = (
                f"FBR logo not found at {LOGO_PATH}. "
                "Please add fbr_logo.png to backend/src/assets/ directory. "
                "See fbr_logo_README.md for instructions."
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            self._logo_cache = Image.open(LOGO_PATH)
            logger.info(f"Loaded FBR logo from {LOGO_PATH}")
            return self._logo_cache
        except Exception as e:
            error_msg = f"Failed to load FBR logo from {LOGO_PATH}: {e}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

    def _generate_qr_code(self, usin: str) -> Image.Image:
        """
        Generate QR code for FBR USIN.

        Generates QR Code Version 2.0 (25x25 modules) at 1.0x1.0 inch.

        Args:
            usin: FBR-issued Unique Sales Invoice Number

        Returns:
            PIL Image object containing QR code
        """
        if not usin:
            raise ValueError("USIN is required for QR code generation")

        # Create QR code with exact FBR specifications
        qr = qrcode.QRCode(
            version=2,  # Version 2.0 = 25x25 modules (FBR requirement)
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=12,  # 12 pixels per module = 300 DPI quality (25 * 12 = 300 pixels = 1 inch at 300 DPI)
            border=0,  # No border (we'll add spacing in layout)
        )

        qr.add_data(usin)
        qr.make(fit=False)  # Don't auto-adjust version - keep Version 2.0

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        logger.debug(f"Generated QR code for USIN: {usin}")
        return img

    def _render_invoice_header(
        self,
        c: canvas.Canvas,
        invoice_data: dict,
        x: float,
        y: float
    ) -> float:
        """
        Render invoice header section.

        Args:
            c: ReportLab canvas
            invoice_data: Invoice data dictionary
            x: X coordinate
            y: Y coordinate (top of header)

        Returns:
            Y coordinate after header (for next section)
        """
        # Ensure fonts are registered
        self._register_fonts()

        # Use Unicode font if available, otherwise Helvetica
        font_name = 'NotoSansArabic' if self._fonts_registered and FONT_PATH.exists() else 'Helvetica'

        # Title
        c.setFont(font_name + '-Bold' if font_name == 'Helvetica' else font_name, 16)
        c.drawString(x, y, "INVOICE")
        y -= 25

        # Invoice number and date
        c.setFont(font_name, 10)
        invoice_number = invoice_data.get('invoiceRefNo', 'N/A')
        invoice_date = invoice_data.get('invoiceDate', 'N/A')
        c.drawString(x, y, f"Invoice #: {invoice_number}")
        c.drawString(x + 250, y, f"Date: {invoice_date}")
        y -= 30

        # Seller details
        c.setFont(font_name + '-Bold' if font_name == 'Helvetica' else font_name, 12)
        c.drawString(x, y, "SELLER DETAILS")
        y -= 15

        c.setFont(font_name, 10)
        seller_name = invoice_data.get('sellerBusinessName', 'N/A')
        seller_ntn = invoice_data.get('sellerNTNCNIC', 'N/A')
        seller_address = invoice_data.get('sellerAddress', 'N/A')
        seller_province = invoice_data.get('sellerProvince', 'N/A')

        c.drawString(x, y, f"Name: {seller_name}")
        y -= 15
        c.drawString(x, y, f"NTN/CNIC: {seller_ntn}")
        y -= 15
        c.drawString(x, y, f"Address: {seller_address}, {seller_province}")
        y -= 30

        # Buyer details
        c.setFont(font_name + '-Bold' if font_name == 'Helvetica' else font_name, 12)
        c.drawString(x, y, "BUYER DETAILS")
        y -= 15

        c.setFont(font_name, 10)
        buyer_name = invoice_data.get('buyerBusinessName', 'N/A')
        buyer_ntn = invoice_data.get('buyerNTNCNIC', 'N/A')
        buyer_address = invoice_data.get('buyerAddress', 'N/A')
        buyer_province = invoice_data.get('buyerProvince', 'N/A')
        buyer_type = invoice_data.get('buyerRegistrationType', 'N/A')

        c.drawString(x, y, f"Name: {buyer_name}")
        y -= 15
        c.drawString(x, y, f"NTN/CNIC: {buyer_ntn}")
        y -= 15
        c.drawString(x, y, f"Address: {buyer_address}, {buyer_province}")
        y -= 15
        c.drawString(x, y, f"Type: {buyer_type}")
        y -= 30

        return y

    def _render_line_items_table(
        self,
        c: canvas.Canvas,
        items: list[dict],
        x: float,
        y: float,
        width: float
    ) -> float:
        """
        Render line items table.

        Args:
            c: ReportLab canvas
            items: List of invoice line items
            x: X coordinate
            y: Y coordinate (top of table)
            width: Table width

        Returns:
            Y coordinate after table (for next section)
        """
        # Ensure fonts are registered
        self._register_fonts()

        # Use Unicode font if available, otherwise Helvetica
        font_name = 'NotoSansArabic' if self._fonts_registered and FONT_PATH.exists() else 'Helvetica'

        # Define table headers
        headers = [
            'HS Code',
            'Product Description',
            'Qty',
            'UOM',
            'Rate',
            'Sales Tax',
            'Total'
        ]

        # Build table data starting with headers
        table_data = [headers]

        # Add item rows with error handling for missing/invalid fields
        for idx, item in enumerate(items):
            try:
                # Truncate long product descriptions to prevent layout issues
                product_desc = str(item.get('product_description', 'N/A'))
                if len(product_desc) > 100:
                    product_desc = product_desc[:97] + '...'
                    logger.debug(f"Truncated long product description in item {idx + 1}")

                row = [
                    str(item.get('hs_code', 'N/A'))[:20],  # Limit HS code length
                    product_desc,
                    str(item.get('quantity', 0)),
                    str(item.get('uom', 'N/A'))[:10],  # Limit UOM length
                    str(item.get('rate', 'N/A')),
                    f"{float(item.get('sales_tax_applicable', 0)):.2f}",
                    f"{float(item.get('total_values', 0)):.2f}"
                ]
                table_data.append(row)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing item {idx + 1}: {e}. Using default values.")
                # Add row with safe defaults
                table_data.append([
                    'N/A', 'Error processing item', '0', 'N/A', 'N/A', '0.00', '0.00'
                ])

        # Define column widths (proportional to content)
        col_widths = [
            width * 0.12,  # HS Code
            width * 0.30,  # Product Description (wider for text)
            width * 0.08,  # Qty
            width * 0.10,  # UOM
            width * 0.12,  # Rate
            width * 0.13,  # Sales Tax
            width * 0.15   # Total
        ]

        # Create table
        table = Table(table_data, colWidths=col_widths)

        # Apply table styling
        table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # HS Code - center
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Product Description - left
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Qty - center
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # UOM - center
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Rate - right
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),   # Sales Tax - right
            ('ALIGN', (6, 1), (6, -1), 'RIGHT'),   # Total - right
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 1), (-1, -1), 4),
            ('RIGHTPADDING', (0, 1), (-1, -1), 4),

            # Grid and borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # Alternating row colors for readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)])
        ]))

        # Calculate table height
        table.wrapOn(c, width, 1000)  # Wrap to calculate dimensions
        table_width, table_height = table.wrap(width, 1000)

        # Draw table at position
        table.drawOn(c, x, y - table_height)

        # Return Y coordinate after table (with some spacing)
        return y - table_height - 20

    def _render_totals(
        self,
        c: canvas.Canvas,
        invoice_data: dict,
        x: float,
        y: float
    ) -> float:
        """
        Render invoice totals section.

        Args:
            c: ReportLab canvas
            invoice_data: Invoice data dictionary
            x: X coordinate
            y: Y coordinate (top of totals)

        Returns:
            Y coordinate after totals (for next section)
        """
        # Ensure fonts are registered
        self._register_fonts()

        # Use Unicode font if available, otherwise Helvetica
        font_name = 'NotoSansArabic' if self._fonts_registered and FONT_PATH.exists() else 'Helvetica'

        # Calculate totals from items
        items = invoice_data.get('items', [])

        subtotal = sum(item.get('value_sales_excluding_st', 0) for item in items)
        total_sales_tax = sum(item.get('sales_tax_applicable', 0) for item in items)
        total_withheld = sum(item.get('sales_tax_withheld_at_source', 0) for item in items)
        total_extra_tax = sum(item.get('extra_tax', 0) for item in items)
        total_further_tax = sum(item.get('further_tax', 0) for item in items)
        total_fed = sum(item.get('fed_payable', 0) for item in items)
        total_discount = sum(item.get('discount', 0) for item in items)
        grand_total = sum(item.get('total_values', 0) for item in items)

        # Position totals on right side of page
        label_x = x + 350
        value_x = x + 500

        # Draw totals section header
        c.setFont(font_name + '-Bold' if font_name == 'Helvetica' else font_name, 12)
        c.drawString(label_x, y, "TOTALS")
        y -= 20

        # Draw separator line
        c.setLineWidth(0.5)
        c.line(label_x, y, value_x + 50, y)
        y -= 15

        # Set font for totals
        c.setFont(font_name, 10)

        # Render each total line
        totals_lines = [
            ("Subtotal (excl. tax):", f"{subtotal:.2f}"),
            ("Sales Tax:", f"{total_sales_tax:.2f}"),
        ]

        # Add optional totals only if non-zero
        if total_withheld > 0:
            totals_lines.append(("Tax Withheld:", f"{total_withheld:.2f}"))
        if total_extra_tax > 0:
            totals_lines.append(("Extra Tax:", f"{total_extra_tax:.2f}"))
        if total_further_tax > 0:
            totals_lines.append(("Further Tax:", f"{total_further_tax:.2f}"))
        if total_fed > 0:
            totals_lines.append(("FED Payable:", f"{total_fed:.2f}"))
        if total_discount > 0:
            totals_lines.append(("Discount:", f"-{total_discount:.2f}"))

        # Draw each total line
        for label, value in totals_lines:
            c.drawString(label_x, y, label)
            c.drawRightString(value_x + 50, y, value)
            y -= 15

        # Draw separator line before grand total
        y -= 5
        c.setLineWidth(1)
        c.line(label_x, y, value_x + 50, y)
        y -= 15

        # Draw grand total (bold/larger)
        c.setFont(font_name + '-Bold' if font_name == 'Helvetica' else font_name, 12)
        c.drawString(label_x, y, "GRAND TOTAL:")
        c.drawRightString(value_x + 50, y, f"{grand_total:.2f}")
        y -= 20

        return y

    def _add_fbr_compliance_elements(
        self,
        c: canvas.Canvas,
        usin: str,
        x: float,
        y: float
    ) -> None:
        """
        Add FBR compliance elements (logo and QR code) to invoice.

        Args:
            c: ReportLab canvas
            usin: FBR-issued USIN for QR code
            x: X coordinate for compliance elements
            y: Y coordinate for compliance elements
        """
        if not usin:
            logger.warning("USIN not provided - skipping QR code generation")
            return

        # Load FBR logo
        try:
            logo_img = self._load_fbr_logo()

            # Calculate logo dimensions (maintain aspect ratio, max width 2 inches)
            logo_max_width = 2 * inch
            logo_max_height = 0.8 * inch

            # Get original logo dimensions
            logo_width, logo_height = logo_img.size
            aspect_ratio = logo_width / logo_height

            # Scale to fit within max dimensions
            if logo_width > logo_max_width:
                display_width = logo_max_width
                display_height = display_width / aspect_ratio
            else:
                display_width = logo_width
                display_height = logo_height

            # Ensure height doesn't exceed max
            if display_height > logo_max_height:
                display_height = logo_max_height
                display_width = display_height * aspect_ratio

            # Position logo at top right of page
            logo_x = x + 400
            logo_y = y

            # Draw logo
            c.drawInlineImage(
                logo_img,
                logo_x,
                logo_y,
                width=display_width,
                height=display_height,
                preserveAspectRatio=True
            )

            logger.debug(f"Drew FBR logo at ({logo_x}, {logo_y})")

        except FileNotFoundError as e:
            logger.warning(f"FBR logo not found - skipping logo: {e}")
        except Exception as e:
            logger.error(f"Failed to draw FBR logo: {e}")

        # Generate and draw QR code
        try:
            qr_img = self._generate_qr_code(usin)

            # QR code dimensions: exactly 1.0 x 1.0 inch (FBR requirement)
            qr_size = 1.0 * inch

            # Position QR code at bottom right
            qr_x = x + 450
            qr_y = 50  # Fixed position near bottom of page

            # Draw QR code
            c.drawInlineImage(
                qr_img,
                qr_x,
                qr_y,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True
            )

            # Add label below QR code
            self._register_fonts()
            font_name = 'NotoSansArabic' if self._fonts_registered and FONT_PATH.exists() else 'Helvetica'
            c.setFont(font_name, 8)
            c.drawCentredString(qr_x + qr_size / 2, qr_y - 12, "Scan to verify")
            c.setFont(font_name, 7)
            c.drawCentredString(qr_x + qr_size / 2, qr_y - 22, f"USIN: {usin[:20]}...")

            logger.debug(f"Drew QR code at ({qr_x}, {qr_y}) with USIN: {usin}")

        except Exception as e:
            logger.error(f"Failed to generate/draw QR code: {e}")
            raise ValueError(f"QR code generation failed: {e}")
