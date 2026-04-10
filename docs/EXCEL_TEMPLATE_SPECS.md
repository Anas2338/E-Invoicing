# Excel Template Column Specifications

## Overview

The Excel template is used for bulk invoice upload and scheduling. Users download the template, fill it with invoice data, and upload it for automated processing by the FTE worker.

**Template File**: `invoice_template.xlsx`  
**Download Endpoint**: `GET /api/v1/automation/template/download`  
**Total Columns**: 35

## Column Categories

### 1. Invoice Identification (3 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `invoice_number` | Yes | String (max 100 chars) | Unique invoice identifier per user | INV-001 |
| `invoice_type` | Yes | String | Type of invoice | Sale Invoice |
| `invoice_date` | Yes | Date (YYYY-MM-DD) | Date when invoice was issued | 2026-04-10 |

**Validation Rules**:
- `invoice_number` must be unique per user
- `invoice_date` must be valid date format

### 2. Seller Information (4 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `seller_ntn_cnic` | Yes | String | Seller's NTN or CNIC number | 1234567 |
| `seller_business_name` | Yes | String | Registered business name | ABC Company |
| `seller_province` | Yes | String | Province where seller is located | Punjab |
| `seller_address` | Yes | String | Complete business address | 123 Main Street, Lahore |

**Valid Provinces**: Punjab, Sindh, KPK, Balochistan, Islamabad, Gilgit-Baltistan, AJK

### 3. Buyer Information (5 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `buyer_ntn_cnic` | Yes | String | Buyer's NTN or CNIC number | 7654321 |
| `buyer_business_name` | Yes | String | Buyer's business name | XYZ Corporation |
| `buyer_province` | Yes | String | Province where buyer is located | Sindh |
| `buyer_address` | Yes | String | Complete buyer address | 456 Business Ave, Karachi |
| `buyer_registration_type` | Yes | String | Registration status | Registered |

**Valid Registration Types**: Registered, Unregistered

### 4. Item Details (16 columns)

These columns match the FBR manual sale invoice form exactly.

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `hs_code` | Yes | String | Harmonized System code | 8471.30.00 |
| `product_description` | Yes | String | Detailed product description | Laptop Computer |
| `tax_rate` | Yes | Number | Sales tax rate percentage | 18 |
| `uom` | Yes | String | Unit of measurement | NOS |
| `quantity` | Yes | Number | Quantity of items | 1 |
| `total_values` | Yes | Number | Total invoice value (including tax) | 118000 |
| `value_sales_excluding_st` | Yes | Number | Value excluding sales tax | 100000 |
| `fixed_notified_value_or_retail_price` | No | Number | Fixed/notified value if applicable | 0 |
| `sales_tax_applicable` | Yes | Number | Calculated sales tax amount | 18000 |
| `sales_tax_withheld_at_source` | No | Number | Tax withheld at source | 0 |
| `extra_tax` | No | Number | Additional tax if applicable | 0 |
| `further_tax` | No | Number | Further tax if applicable | 0 |
| `sro_schedule_no` | No | String | SRO schedule number if exempt | |
| `fed_payable` | No | Number | Federal excise duty | 0 |
| `discount` | No | Number | Discount amount | 0 |
| `sale_type` | Yes | String | Type of sale (FBR code) | 01 |
| `sro_item_serial_no` | No | String | SRO item serial number | |

**Common UOM Values**: NOS (Numbers), KGS (Kilograms), LTR (Liters), MTR (Meters), PCS (Pieces)

**Sale Type Codes**:
- `01`: Local Sale
- `02`: Export
- `03`: Zero-rated
- `04`: Exempt

**Tax Calculation**:
```
sales_tax_applicable = value_sales_excluding_st × (tax_rate / 100)
total_values = value_sales_excluding_st + sales_tax_applicable - discount
```

### 5. Optional Fields (2 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `invoice_ref_no` | No | String | Reference to another invoice | |
| `scenario_id` | No | String | FBR scenario identifier | SN001 |

### 6. Scheduling (2 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `scheduled_date` | Yes | Date (YYYY-MM-DD) | Date when invoice should be processed | 2026-04-10 |
| `scheduled_time` | Yes | Time (HH:MM) | Hour when invoice should be processed | 10:00 |

**Important Notes**:
- FTE worker runs every hour at minute 0 (e.g., 10:00, 11:00, 12:00)
- Invoices are processed during the hour matching `scheduled_time`
- Example: `scheduled_time: 10:00` → processed between 10:00-10:59
- Past scheduled times are automatically marked as "expired"
- Use 24-hour format (00:00 to 23:00)

### 7. Environment (1 column)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `environment` | Yes | String | FBR environment to use | SANDBOX |

**Valid Values**:
- `SANDBOX`: Testing environment (recommended for initial testing)
- `PRODUCTION`: Live FBR environment (use only for real invoices)

### 8. Status Fields (2 columns)

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `status` | No | String | Processing status (auto-filled by system) | |
| `reason` | No | String | Error/success reason (auto-filled by system) | |

**Note**: Leave these columns empty when uploading. The system fills them after processing.

**Status Values After Processing**:
- `pending`: Waiting for scheduled time
- `expired`: Scheduled time has passed
- `validated`: Passed validation checks
- `submitted`: Successfully submitted to FBR
- `failed`: Validation or submission failed

## File Requirements

### File Format
- **Extension**: `.xlsx` (Excel 2007+)
- **Max File Size**: 10 MB
- **Max Rows**: 1,000 invoices per upload
- **Sheet Name**: Any (first sheet is used)

### Data Validation

**Before Upload**:
1. All required columns must be present
2. Column names must match exactly (case-sensitive)
3. No duplicate invoice numbers within the file
4. Dates must be in YYYY-MM-DD format
5. Times must be in HH:MM format (24-hour)
6. Numeric fields must contain valid numbers

**During Processing**:
1. Invoice number uniqueness checked against database
2. Scheduled times validated (not in the past)
3. Invoice data validated against FBR schema
4. Concurrent upload check (one upload per user at a time)

## Sample Data

The template includes one sample row with example data:

```
invoice_number: INV-001
invoice_type: Sale Invoice
invoice_date: 2026-04-10
seller_ntn_cnic: 1234567
seller_business_name: ABC Company
seller_province: Punjab
seller_address: 123 Main Street, Lahore
buyer_ntn_cnic: 7654321
buyer_business_name: XYZ Corporation
buyer_province: Sindh
buyer_address: 456 Business Ave, Karachi
buyer_registration_type: Registered
hs_code: 8471.30.00
product_description: Laptop Computer
tax_rate: 18
uom: NOS
quantity: 1
total_values: 118000
value_sales_excluding_st: 100000
fixed_notified_value_or_retail_price: 0
sales_tax_applicable: 18000
sales_tax_withheld_at_source: 0
extra_tax: 0
further_tax: 0
sro_schedule_no: 
fed_payable: 0
discount: 0
sale_type: 01
sro_item_serial_no: 
invoice_ref_no: 
scenario_id: SN001
scheduled_date: 2026-04-10
scheduled_time: 10:00
environment: SANDBOX
status: 
reason: 
```

## Usage Workflow

1. **Download Template**
   ```bash
   GET /api/v1/automation/template/download
   ```

2. **Fill Invoice Data**
   - Delete the sample row
   - Add your invoice data (up to 1,000 rows)
   - Ensure all required fields are filled
   - Set appropriate scheduled dates/times

3. **Upload File**
   ```bash
   POST /api/v1/automation/excel/upload
   Content-Type: multipart/form-data
   Authorization: Bearer <token>
   ```

4. **Monitor Processing**
   - Check upload status: `GET /api/v1/automation/excel/status/{session_id}`
   - View dashboard: `GET /api/v1/automation/dashboard/invoices`
   - Download results: `GET /api/v1/automation/dashboard/download/{session_id}`

## Common Errors

### Upload Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid file type | Wrong file extension | Use .xlsx files only |
| Missing columns | Required columns not present | Ensure all required columns exist |
| Duplicate invoice numbers | Same invoice_number appears twice | Use unique invoice numbers |
| Concurrent upload | Previous upload still processing | Wait for previous upload to complete |
| File too large | Exceeds 10 MB limit | Split into multiple files |
| Too many rows | Exceeds 1,000 row limit | Split into multiple uploads |

### Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid date format | Date not in YYYY-MM-DD | Use correct date format |
| Invalid time format | Time not in HH:MM | Use 24-hour format (00:00-23:00) |
| Past scheduled time | Time is in the past | Use future date/time |
| Invalid province | Province name not recognized | Use valid province names |
| Invalid environment | Not SANDBOX or PRODUCTION | Use valid environment value |
| Tax calculation mismatch | Numbers don't add up | Verify tax calculations |

## Best Practices

1. **Testing**: Always test with SANDBOX environment first
2. **Scheduling**: Schedule invoices at least 1 hour in advance
3. **Batch Size**: Upload 100-500 invoices per batch for optimal performance
4. **Validation**: Validate data in Excel before uploading
5. **Backup**: Keep a copy of your Excel file before uploading
6. **Monitoring**: Check dashboard regularly for processing status
7. **Error Handling**: Download results file to see detailed error messages

## Support

For issues with the Excel template:
- Check column names match exactly (case-sensitive)
- Verify data formats (dates, times, numbers)
- Review validation error messages in dashboard
- Download processed file to see status and reasons
- Contact support with session_id for troubleshooting
