#!/usr/bin/env python3
"""
Test script to generate a sample invoice PDF.

This script creates a test invoice with sample data and generates a PDF
to preview how invoices look when printed.
"""

import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.pdf_service import PDFService
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from uuid import uuid4


def create_sample_invoice():
    """Create a sample invoice with test data."""

    # Sample invoice data
    invoice_data = {
        'invoiceRefNo': 'INV-2024-TEST-001',
        'invoiceDate': '2024-04-28',
        'sellerBusinessName': 'ABC Trading Company (Pvt) Ltd',
        'sellerNTNCNIC': '1234567-8',
        'sellerAddress': '123 Main Street, Clifton',
        'sellerProvince': 'Sindh',
        'buyerBusinessName': 'XYZ Corporation',
        'buyerNTNCNIC': '9876543-2',
        'buyerAddress': '456 Business Avenue, Gulberg',
        'buyerProvince': 'Punjab',
        'buyerRegistrationType': 'Registered',
        'items': [
            {
                'hs_code': '8471.30.00',
                'product_description': 'Laptop Computer - Dell Latitude 5420, Intel Core i5, 8GB RAM, 256GB SSD',
                'quantity': 5,
                'uom': 'PCS',
                'rate': 50000.00,
                'value_sales_excluding_st': 250000.00,
                'sales_tax_applicable': 45000.00,
                'sales_tax_withheld_at_source': 0.00,
                'extra_tax': 0.00,
                'further_tax': 0.00,
                'fed_payable': 0.00,
                'discount': 0.00,
                'total_values': 295000.00
            },
            {
                'hs_code': '8528.72.00',
                'product_description': 'LED Monitor - 24 inch Full HD Display',
                'quantity': 10,
                'uom': 'PCS',
                'rate': 15000.00,
                'value_sales_excluding_st': 150000.00,
                'sales_tax_applicable': 27000.00,
                'sales_tax_withheld_at_source': 0.00,
                'extra_tax': 0.00,
                'further_tax': 0.00,
                'fed_payable': 0.00,
                'discount': 0.00,
                'total_values': 177000.00
            },
            {
                'hs_code': '8473.30.00',
                'product_description': 'Wireless Keyboard and Mouse Combo',
                'quantity': 20,
                'uom': 'PCS',
                'rate': 1500.00,
                'value_sales_excluding_st': 30000.00,
                'sales_tax_applicable': 5400.00,
                'sales_tax_withheld_at_source': 0.00,
                'extra_tax': 0.00,
                'further_tax': 0.00,
                'fed_payable': 0.00,
                'discount': 0.00,
                'total_values': 35400.00
            }
        ]
    }

    # Create mock AutomationInvoice object
    invoice = AutomationInvoice(
        id=uuid4(),
        user_id=uuid4(),
        session_id=uuid4(),
        invoice_number='INV-2024-TEST-001',
        invoice_data=invoice_data,
        scheduled_date=datetime.now().date(),
        scheduled_time=datetime.now().time(),
        status=AutomationInvoiceStatus.SUBMITTED,
        fbr_response={
            'USIN': 'TEST-USIN-123456789012345',
            'dated': '2024-04-28 10:30:00',
            'validationResponse': {
                'statusCode': '00',
                'status': 'Valid'
            }
        },
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    return invoice


def main():
    """Generate sample invoice PDF."""
    print("=" * 60)
    print("FBR E-Invoice PDF Generator - Test Script")
    print("=" * 60)
    print()

    # Check if assets exist
    assets_dir = Path(__file__).parent / 'src' / 'assets'
    logo_path = assets_dir / 'fbr_logo.png'
    font_path = assets_dir / 'NotoSansArabic-Regular.ttf'

    print("Checking required assets...")
    if logo_path.exists():
        print(f"[OK] FBR Logo found: {logo_path}")
    else:
        print(f"[WARN] FBR Logo not found: {logo_path}")
        print("       PDF will be generated without logo")

    if font_path.exists():
        print(f"[OK] Unicode Font found: {font_path}")
    else:
        print(f"[WARN] Unicode Font not found: {font_path}")
        print("       PDF will use Helvetica (limited Unicode support)")

    print()

    # Create sample invoice
    print("Creating sample invoice with test data...")
    invoice = create_sample_invoice()
    print(f"[OK] Invoice created: {invoice.invoice_number}")
    print(f"     - Seller: {invoice.invoice_data['sellerBusinessName']}")
    print(f"     - Buyer: {invoice.invoice_data['buyerBusinessName']}")
    print(f"     - Items: {len(invoice.invoice_data['items'])}")
    print(f"     - USIN: {invoice.fbr_response['USIN']}")
    print()

    # Generate PDF
    print("Generating PDF...")
    try:
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_invoice_pdf(invoice)

        # Save to file
        output_path = Path(__file__).parent / 'sample_invoice.pdf'
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

        print(f"[SUCCESS] PDF generated successfully!")
        print(f"          - Size: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
        print(f"          - Saved to: {output_path}")
        print()
        print("=" * 60)
        print("You can now open the PDF to see how invoices look:")
        print(f"   {output_path}")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print()
        print("Missing required assets. Please add:")
        print("  1. FBR logo: backend/src/assets/fbr_logo.png")
        print("  2. Font file: backend/src/assets/NotoSansArabic-Regular.ttf")

    except Exception as e:
        print(f"[ERROR] Error generating PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
