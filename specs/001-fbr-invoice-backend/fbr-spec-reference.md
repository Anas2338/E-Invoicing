# FBR Technical Specification Reference

**Document**: Technical Specification for DI API v1.12
**Source**: PRAL (Pakistan Revenue Automation Limited)
**Last Updated**: 24-July-2025
**Feature**: Backend System for FBR Invoice Integration Portal

## Overview

This document consolidates key information from the official FBR Digital Invoicing API technical specification for implementation reference.

## API Endpoints

### Validation API

**Sandbox**:
```
POST https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb
```

**Production**:
```
POST https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata
```

### Posting API

**Sandbox**:
```
POST https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb
```

**Production**:
```
POST https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata
```

## Authentication

**Method**: Bearer Token in Authorization header

**Format**:
```
Authorization: Bearer <security-token>
```

**Token Validity**: 5 years (renewable upon expiry)

**Note**: Same API URLs for sandbox and production; routing determined by security token.

## Invoice Field Specifications

### Header Fields (Required)

| Field | Type | Required | Format/Values | Description |
|-------|------|----------|---------------|-------------|
| invoiceType | string | Yes | "Sale Invoice", "Debit Note" | Type of invoice |
| invoiceDate | date | Yes | YYYY-MM-DD | Invoice issuance date |
| sellerNTNCNIC | string | Yes | 7 or 13 digits | Seller NTN (7/9 digits) or CNIC (13 digits) |
| sellerBusinessName | string | Yes | - | Seller business name |
| sellerProvince | string | Yes | Province name | From reference API 5.1 |
| sellerAddress | string | Yes | - | Seller business address |
| buyerNTNCNIC | string | Yes* | 7 or 13 digits | Buyer NTN/CNIC (*Optional for unregistered) |
| buyerBusinessName | string | Yes | - | Buyer business name |
| buyerProvince | string | Yes | Province name | From reference API 5.1 |
| buyerAddress | string | Yes | - | Buyer address |
| buyerRegistrationType | string | Yes | "Registered", "Unregistered" | Buyer registration type |
| invoiceRefNo | string | Conditional | 22 or 28 digits | Required for debit note only |
| scenarioId | string | Sandbox only | SN001-SN028 | Scenario ID for sandbox testing |

### Item Fields (Required)

| Field | Type | Required | Format/Values | Description |
|-------|------|----------|---------------|-------------|
| hsCode | string | Yes | XXXX.XXXX | Harmonized System Code |
| productDescription | string | Yes | - | Product/service description |
| rate | string | Yes | XX% | Tax rate (from reference API 5.8) |
| uoM | string | Yes | - | Unit of Measurement (from reference API 5.6) |
| quantity | decimal | Yes | > 0 | Quantity of item sold |
| totalValues | decimal | Yes | >= 0 | Total sales value (including tax) |
| valueSalesExcludingST | decimal | Yes | >= 0 | Sales value excluding sales tax |
| fixedNotifiedValueOrRetailPrice | decimal | Yes | >= 0 | Notified fixed/retail price |
| salesTaxApplicable | decimal | Yes | >= 0 | Sales tax/FED amount (excluding further & extra tax) |
| salesTaxWithheldAtSource | decimal | Yes | >= 0 | Sales tax withheld at source |
| extraTax | decimal | Optional | >= 0 | Extra tax if applicable |
| furtherTax | decimal | Optional | >= 0 | Further tax if applicable |
| sroScheduleNo | string | Optional | - | SRO schedule number |
| fedPayable | decimal | Optional | >= 0 | Federal excise duty payable |
| discount | decimal | Optional | >= 0 | Discount if applicable |
| saleType | string | Yes | - | Type of sale (from scenarios) |
| sroItemSerialNo | string | Optional | - | Item serial number in SRO |

## Response Formats

### Validation/Posting Success Response

```json
{
  "invoiceNumber": "7000007DI1747119701593",
  "dated": "2025-05-13 12:01:41",
  "validationResponse": {
    "statusCode": "00",
    "status": "Valid",
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "00",
        "status": "Valid",
        "invoiceNo": "7000007DI1747119701593-1",
        "errorCode": "",
        "error": ""
      }
    ]
  }
}
```

**Invoice Number Format**:
- NTN-based: 22 digits
- CNIC-based: 28 digits

### Validation/Posting Failure Response (Header Level)

```json
{
  "dated": "2025-05-13 13:09:05",
  "validationResponse": {
    "statusCode": "01",
    "status": "Invalid",
    "errorCode": "0052",
    "error": "Provide proper HS Code with invoice no. null",
    "invoiceStatuses": null
  }
}
```

### Validation/Posting Failure Response (Item Level)

```json
{
  "dated": "2025-05-13 13:10:00",
  "validationResponse": {
    "statusCode": "00",
    "status": "invalid",
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "01",
        "status": "Invalid",
        "invoiceNo": null,
        "errorCode": "0046",
        "error": "Provide rate."
      }
    ]
  }
}
```

## Status Codes

### FBR Status Codes

- **00**: Valid
- **01**: Invalid

### HTTP Status Codes

- **200**: OK (Success)
- **401**: Unauthorized (Invalid/missing token)
- **500**: Internal Server Error (Contact administrator)

## Error Codes

### Sales Error Codes (Selected)

| Code | Message | Description |
|------|---------|-------------|
| 0001 | Seller not registered | Seller NTN/registration invalid |
| 0002 | Invalid Buyer Registration | Buyer NTN/CNIC format invalid |
| 0003 | Provide proper invoice type | Invoice type invalid/empty |
| 0005 | Invalid date format | Date not in YYYY-MM-DD format |
| 0011 | Provide Buyer registration No | Buyer registration number empty |
| 0012 | Provide Buyer Name | Buyer name empty |
| 0013 | Provide Buyer Registration Type | Buyer registration type empty |
| 0018 | Provide invoice type | Invoice type empty |
| 0019 | Provide valid Sale type | Sale type empty/null |
| 0020 | Provide Sales Tax/FED | Sales tax/FED empty |
| 0021 | Provide HSCode | HS Code empty |
| 0046 | Provide rate | Rate empty |
| 0052 | Provide proper HS Code | HS Code invalid |
| 0401 | Unauthorized seller token | Seller NTN/CNIC token invalid |
| 0402 | Unauthorized buyer token | Buyer NTN/CNIC token invalid |

### Purchase Error Codes (Selected)

| Code | Message | Description |
|------|---------|-------------|
| 0156 | Invalid NTN / Reg No | NTN/Reg No invalid/null |
| 0157 | Buyer not registered | Buyer registration invalid |
| 0158 | Mismatch Buyer Registration | Buyer Reg No doesn't match |
| 0159 | FTN holder as seller not allowed | FTN holder cannot be seller for purchases |
| 0160 | Provide Buyer Name | Buyer name empty |
| 0162 | Provide Sale Type | Sale type empty/invalid |
| 0165 | Provide UOM KG | UOM must be in KG |
| 0166 | Provide Quantity | Quantity/electricity units empty |
| 0167 | Provide Value of Sales Excl. ST | Sales value excluding ST empty |

**Note**: Full list of 100+ error codes available in TECHNICAL.txt lines 1139-1682.

## Validation Scenarios (Sandbox Testing)

| Scenario | Description | Sale Type |
|----------|-------------|-----------|
| SN001 | Goods at standard rate to registered buyers | Goods at Standard Rate (default) |
| SN002 | Goods at standard rate to unregistered buyers | Goods at Standard Rate (default) |
| SN003 | Sale of Steel (Melted and Re-Rolled) | Steel Melting and re-rolling |
| SN004 | Sale by Ship Breakers | Ship breaking |
| SN005 | Reduced rate sale | Goods at Reduced Rate |
| SN006 | Exempt goods sale | Exempt Goods |
| SN007 | Zero rated sale | Goods at zero-rate |
| SN008 | Sale of 3rd schedule goods | 3rd Schedule Goods |
| SN009 | Cotton Spinners purchase from Cotton Ginners | Cotton Ginners |
| SN010 | Telecom services rendered or provided | Telecommunication services |
| SN011 | Toll Manufacturing sale by Steel sector | Toll Manufacturing |
| SN012 | Sale of Petroleum products | Petroleum Products |
| SN013 | Electricity Supply to Retailers | Electricity Supply to Retailers |
| SN014 | Sale of Gas to CNG stations | Gas to CNG stations |
| SN015 | Sale of mobile phones | Mobile Phones |
| SN016 | Processing / Conversion of Goods | Processing/ Conversion of Goods |
| SN017 | Sale of Goods where FED is charged in ST mode | Goods (FED in ST Mode) |
| SN018 | Services where FED is charged in ST mode | Services (FED in ST Mode) |
| SN019 | Services rendered or provided | Services |
| SN020 | Sale of Electric Vehicles | Electric Vehicle |
| SN021 | Sale of Cement /Concrete Block | Cement /Concrete Block |
| SN022 | Sale of Potassium Chlorate | Potassium Chlorate |
| SN023 | Sale of CNG | CNG Sales |
| SN024 | Goods listed in SRO 297(1)/2023 | Goods as per SRO.297(|)/2023 |
| SN025 | Drugs at fixed ST rate (Eighth Schedule) | Non-Adjustable Supplies |
| SN026 | Sale to End Consumer by retailers | Goods at Standard Rate (default) |
| SN027 | Sale to End Consumer by retailers | 3rd Schedule Goods |
| SN028 | Sale to End Consumer by retailers | Goods at Reduced Rate |

**Note**: Scenarios 26, 27, 28 only applicable if registered as retailer.

## Reference APIs (12 APIs)

### 1. Province Code
**URL**: `https://gw.fbr.gov.pk/pdi/v1/stateprovincecode`
**Method**: GET
**Response**: List of provinces with codes

### 2. Document Type ID
**URL**: `https://gw.fbr.gov.pk/pdi/v1/doctypecode`
**Method**: GET
**Response**: Document types (Sale Invoice, Debit Note)

### 3. Item Code (HS Codes)
**URL**: `https://gw.fbr.gov.pk/pdi/v1/itemdesccode`
**Method**: GET
**Response**: HS codes with descriptions

### 4. SRO Item ID
**URL**: `https://gw.fbr.gov.pk/pdi/v1/sroitemcode`
**Method**: GET
**Response**: SRO item IDs and descriptions

### 5. Transaction Type ID
**URL**: `https://gw.fbr.gov.pk/pdi/v1/transtypecode`
**Method**: GET
**Response**: Transaction types

### 6. Unit of Measurement (UOM)
**URL**: `https://gw.fbr.gov.pk/pdi/v1/uomcode`
**Method**: GET
**Response**: UOM codes and descriptions

### 7. SRO Schedule
**URL**: `https://gw.fbr.gov.pk/pdi/v1/sroschedule`
**Method**: GET
**Response**: SRO schedule numbers

### 8. Rate ID
**URL**: `https://gw.fbr.gov.pk/pdi/v2/SaleTypeToRate?date=24-Feb-2024&transTypeId=18&originationSupplier=1`
**Method**: GET
**Query Params**: date, transTypeId, originationSupplier
**Response**: Rate IDs, descriptions, and values

### 9. HS Code with UOM
**URL**: `https://gw.fbr.gov.pk/pdi/v2/HS_UOM?hs_code=5904.9000&annexure_id=3`
**Method**: GET
**Query Params**: hs_code, annexure_id
**Response**: UOM for specific HS code

### 10. SRO Item
**URL**: `https://gw.fbr.gov.pk/pdi/v2/SROItem?date=2025-03-25&sro_id=389`
**Method**: GET
**Query Params**: date, sro_id
**Response**: SRO item IDs and descriptions

### 11. STATL (Status Check)
**URL**: `https://gw.fbr.gov.pk/dist/v1/statl`
**Method**: POST
**Request**: `{"regno":"0788762","date":"2025-05-18"}`
**Response**: Status code (01/02 = In-Active)

### 12. Registration Type
**URL**: `https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type`
**Method**: POST
**Request**: `{"Registration_No":"0788762"}`
**Response**: Registration type (Registered/Unregistered)

## QR Code & Logo Requirements

### QR Code Specifications
- **Version**: 2.0 (25×25)
- **Dimensions**: 1.0 x 1.0 inch
- **Requirement**: Must be printed on each invoice

### FBR Logo
- Use official FBR Digital Invoicing System logo
- Must be printed on receipts

## Business Activity Scenarios

### Manufacturer - All Other Sectors
Applicable scenarios: SN001, SN002, SN005, SN006, SN007, SN015, SN016, SN017, SN021, SN022, SN024

### Manufacturer - Steel
Applicable scenarios: SN003, SN004, SN011

### Manufacturer - Textile
Applicable scenarios: SN001, SN002, SN005, SN006, SN007, SN015, SN016, SN017, SN021, SN022, SN024, SN009

### Manufacturer - Telecom
Applicable scenarios: SN001, SN002, SN005, SN006, SN007, SN015, SN016, SN017, SN021, SN022, SN024, SN010

### Retailer - All Sectors
Applicable scenarios: SN001, SN002, SN005, SN006, SN007, SN015, SN016, SN017, SN021, SN022, SN024, SN026, SN027, SN028, SN008

**Note**: Full business activity mapping available in TECHNICAL.txt lines 1715-2024.

## Implementation Notes

### Field Validation Rules

1. **NTN/CNIC Format**:
   - NTN: 7 or 9 digits
   - CNIC: 13 digits
   - Validation: Must match registered format

2. **Date Format**:
   - Required format: YYYY-MM-DD
   - Example: 2025-05-25

3. **Invoice Number Format**:
   - Alphanumeric with hyphen allowed
   - Hyphen must be between alphanumeric strings
   - Example: Inv-001

4. **Decimal Values**:
   - All monetary fields must be valid decimals
   - Precision: 4 decimal places for quantity
   - Precision: 2 decimal places for monetary values

5. **HS Code Format**:
   - Format: XXXX.XXXX (8 digits with dot separator)
   - Example: 0101.2100

### Error Handling Strategy

1. **Header-Level Errors** (statusCode: "01" at root):
   - Invoice rejected entirely
   - No invoice number issued
   - Fix errors and resubmit

2. **Item-Level Errors** (statusCode: "01" in invoiceStatuses):
   - Specific items rejected
   - Other items may be valid
   - Fix item-specific errors and resubmit

3. **HTTP Errors**:
   - 401: Check Bearer token validity
   - 500: Contact FBR administrator

### Security Considerations

1. **Token Management**:
   - Store token securely (environment variable)
   - Monitor expiry (5-year validity)
   - Request renewal before expiry

2. **Sandbox vs Production**:
   - Use separate tokens for sandbox and production
   - Never use production token in sandbox
   - Validate environment before API calls

3. **Data Validation**:
   - Validate all fields before API call
   - Use reference APIs for dropdown values
   - Implement client-side validation to reduce API errors

## Testing Strategy

### Sandbox Testing

1. **Use Scenario IDs**: Required for sandbox (SN001-SN028)
2. **Test All Scenarios**: Cover all applicable business activities
3. **Validate Error Handling**: Test with invalid data to verify error codes
4. **Test State Transitions**: Validate → Post workflow

### Production Readiness

1. **Remove Scenario IDs**: Not used in production
2. **Verify Token**: Ensure production token is valid
3. **Test with Real Data**: Use actual NTN/CNIC numbers
4. **Monitor Error Rates**: Track validation/posting failures

## References

- **Official Document**: Technical Specification for DI API v1.12
- **Source File**: TECHNICAL.pdf (converted to TECHNICAL.txt)
- **PRAL Website**: https://pral.gov.pk
- **FBR Portal**: https://e.fbr.gov.pk

## Changelog

- **2026-02-22**: Initial extraction from FBR Technical Specification v1.12
- **Source**: TECHNICAL.pdf (27 pages, 51 pages in document)
- **Extracted By**: Planning phase of sp.plan workflow

---

**Note**: This is a reference document for development. Always refer to the official FBR technical specification for authoritative information.
