# FBR Digital Invoicing Integration

## Overview

This document describes the implementation of FBR (Federal Board of Revenue) Digital Invoicing System integration for validation and posting of invoices.

## Architecture

### Backend Components

#### 1. FBR Service (`backend/src/services/fbr_service.py`)

The `FBRService` class handles all interactions with FBR APIs:

**Key Features:**
- Async HTTP client using `httpx` for non-blocking API calls
- Separate sandbox and production URLs
- Invoice data transformation from internal format to FBR format
- Response parsing for validation and posting results
- Comprehensive error handling and logging

**Methods:**
- `validate_invoice(invoice, access_token)` - Validates invoice with FBR
- `post_invoice(invoice, access_token)` - Posts validated invoice to FBR
- `parse_validation_response(fbr_response)` - Parses validation results
- `parse_posting_response(fbr_response)` - Parses posting results

**API Endpoints:**
- **Sandbox Validation**: `https://esp.fbr.gov.pk:8244/FBR/Production/di_data/v1/di/validateinvoicedata`
- **Production Validation**: `https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata`
- **Sandbox Posting**: `https://esp.fbr.gov.pk:8244/FBR/Production/di_data/v1/di/postinvoicedata`
- **Production Posting**: `https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata`

#### 2. API Routes (`backend/src/api/v1/invoices.py`)

Two new endpoints added:

**POST `/invoices/{invoice_id}/validate`**
- Validates invoice with FBR
- Requires invoice to be in DRAFT status
- Updates status to VALIDATED on success
- Stores validation errors on failure

**POST `/invoices/{invoice_id}/post`**
- Posts validated invoice to FBR
- Requires invoice to be in VALIDATED status
- Updates status to POSTED on success
- Stores FBR reference number
- Updates status to FAILED on error

### Frontend Components

#### 1. API Client (`frontend/src/lib/api.ts`)

Added two new methods to the invoices API:

```typescript
validate: async (id: string) => {
  return fetchWithAuth(`/invoices/${id}/validate`, {
    method: 'POST',
  });
}

post: async (id: string) => {
  return fetchWithAuth(`/invoices/${id}/post`, {
    method: 'POST',
  });
}
```

#### 2. Validation Result Dialog (`frontend/src/components/invoices/validation-result-dialog.tsx`)

A reusable dialog component for displaying validation and posting results:

**Features:**
- Success/failure visual indicators
- Invoice number display
- FBR reference number display (for successful posting)
- Detailed error messages with item-level errors
- Responsive design with scrollable content
- Color-coded UI (green for success, red for failure)

#### 3. Invoice History Page (`frontend/src/app/(protected)/invoices/history/page.tsx`)

Updated to implement actual validation and posting:

**Changes:**
- Replaced placeholder alerts with API calls
- Integrated ValidationResultDialog for better UX
- Added confirmation dialogs before validation/posting
- Automatic invoice list refresh after successful operations
- Comprehensive error handling

## Data Flow

### Validation Flow

1. User clicks "Validate" button on DRAFT invoice
2. Frontend shows confirmation dialog
3. Frontend calls `POST /api/v1/invoices/{id}/validate`
4. Backend retrieves invoice from database
5. Backend transforms invoice to FBR format
6. Backend calls FBR validation API
7. Backend parses FBR response
8. If valid:
   - Update invoice status to VALIDATED
   - Return success response
9. If invalid:
   - Store validation errors in database
   - Return error response with details
10. Frontend displays result in ValidationResultDialog
11. Frontend refreshes invoice list

### Posting Flow

1. User clicks "Post" button on VALIDATED invoice
2. Frontend shows confirmation dialog
3. Frontend calls `POST /api/v1/invoices/{id}/post`
4. Backend retrieves invoice from database
5. Backend transforms invoice to FBR format
6. Backend calls FBR posting API
7. Backend parses FBR response
8. If successful:
   - Update invoice status to POSTED
   - Store FBR reference number
   - Return success response
9. If failed:
   - Update invoice status to FAILED
   - Store error details
   - Return error response
10. Frontend displays result in ValidationResultDialog
11. Frontend refreshes invoice list

## Invoice Status State Machine

```
DRAFT → VALIDATED → POSTED
  ↓         ↓
FAILED ← FAILED
```

**Status Transitions:**
- DRAFT → VALIDATED (via validation)
- DRAFT → FAILED (validation error)
- VALIDATED → POSTED (via posting)
- VALIDATED → FAILED (posting error)

## FBR API Request Format

### Validation/Posting Request

```json
{
  "invoiceType": "Sale Invoice",
  "invoiceDate": "2025-04-21",
  "sellerNTNCNIC": "0786909",
  "sellerBusinessName": "Company 8",
  "sellerProvince": "Sindh",
  "sellerAddress": "Karachi",
  "buyerNTNCNIC": "1000000000000",
  "buyerBusinessName": "FERTILIZER MANUFAC IRS NEW",
  "buyerProvince": "Sindh",
  "buyerAddress": "Karachi",
  "buyerRegistrationType": "Registered",
  "invoiceRefNo": "",
  "scenarioId": "SN001",
  "items": [
    {
      "hsCode": "0101.2100",
      "productDescription": "product Description",
      "rate": "18%",
      "uoM": "Numbers, pieces, units",
      "quantity": 1.0000,
      "totalValues": 0.00,
      "valueSalesExcludingST": 1000.00,
      "fixedNotifiedValueOrRetailPrice": 0.00,
      "salesTaxApplicable": 180.00,
      "salesTaxWithheldAtSource": 0.00,
      "extraTax": 0.00,
      "furtherTax": 120.00,
      "sroScheduleNo": "",
      "fedPayable": 0.00,
      "discount": 0.00,
      "saleType": "Goods at standard rate (default)",
      "sroItemSerialNo": ""
    }
  ]
}
```

### Validation Response (Success)

```json
{
  "dated": "2025-05-13 13:13:07",
  "validationResponse": {
    "statusCode": "00",
    "status": "Valid",
    "errorCode": null,
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "00",
        "status": "Valid",
        "errorCode": null,
        "error": ""
      }
    ]
  }
}
```

### Validation Response (Failure)

```json
{
  "dated": "2025-05-13 13:13:54",
  "validationResponse": {
    "statusCode": "01",
    "status": "Invalid",
    "errorCode": null,
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "01",
        "status": "Invalid",
        "errorCode": "0046",
        "error": "Provide rate."
      }
    ]
  }
}
```

## Error Handling

### Backend Error Handling

1. **HTTP Errors**: Caught and returned with status code and message
2. **Request Errors**: Network/connection errors caught and logged
3. **Validation Errors**: Stored in database for user reference
4. **Status Transition Errors**: Prevented by checking current status

### Frontend Error Handling

1. **API Errors**: Displayed in ValidationResultDialog
2. **Network Errors**: User-friendly error messages
3. **Confirmation Dialogs**: Prevent accidental operations
4. **Automatic Refresh**: Updates invoice list after operations

## Security Considerations

### Current Implementation

- Bearer token authentication required for all endpoints
- User ID validation ensures users can only access their own invoices
- Status checks prevent invalid state transitions
- SSL/TLS for FBR API communication (verify=False for development)

### TODO: Authentication Token Management

The current implementation uses a placeholder for FBR access tokens:

```python
access_token = "YOUR_FBR_ACCESS_TOKEN"
```

**Required Implementation:**
1. Store FBR credentials securely (encrypted in database)
2. Implement FBR OAuth/token refresh mechanism
3. Associate FBR credentials with user accounts
4. Retrieve user's FBR token before API calls

## Testing

### Manual Testing Steps

1. **Create Invoice**
   - Navigate to Create Invoice page
   - Fill in all required fields
   - Submit to create DRAFT invoice

2. **Validate Invoice**
   - Go to Invoice History
   - Find DRAFT invoice
   - Click "Validate" button
   - Confirm validation
   - Verify result dialog shows success/failure
   - Check invoice status updated to VALIDATED

3. **Post Invoice**
   - Find VALIDATED invoice
   - Click "Post" button
   - Confirm posting
   - Verify result dialog shows FBR number
   - Check invoice status updated to POSTED

4. **Error Scenarios**
   - Try validating non-DRAFT invoice (should fail)
   - Try posting non-VALIDATED invoice (should fail)
   - Test with invalid invoice data (should show validation errors)

### Sandbox Testing

Use scenario IDs from FBR documentation:
- SN001: Goods at standard rate to registered buyers
- SN002: Goods at standard rate to unregistered buyers
- SN003-SN028: Various sector-specific scenarios

## Dependencies

### Backend
- `httpx>=0.28.0` - Async HTTP client for FBR API calls

### Frontend
- No new dependencies (uses existing React/Next.js components)

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# FBR API Configuration
FBR_SANDBOX_MODE=true
FBR_ACCESS_TOKEN=your_fbr_access_token_here
```

## Known Limitations

1. **FBR Access Token**: Currently hardcoded, needs proper credential management
2. **SSL Verification**: Disabled for development (`verify=False`)
3. **Rate Limiting**: No rate limiting implemented for FBR API calls
4. **Retry Logic**: No automatic retry on transient failures
5. **Webhook Support**: No webhook handling for async FBR responses

## Future Enhancements

1. **FBR Credential Management**
   - User profile page for FBR credentials
   - Secure credential storage
   - Token refresh mechanism

2. **QR Code Generation**
   - Generate QR codes for posted invoices
   - Display QR code on invoice view page
   - Print-ready invoice format with QR code

3. **Batch Operations**
   - Validate multiple invoices at once
   - Bulk posting of validated invoices

4. **Enhanced Error Reporting**
   - Detailed error code lookup
   - Suggested fixes for common errors
   - Error history tracking

5. **FBR Reference APIs**
   - Integrate 12 reference APIs for dropdowns
   - Cache reference data locally
   - Auto-refresh reference data periodically

6. **Audit Trail**
   - Log all FBR API interactions
   - Store request/response payloads
   - Track status change history

## References

- FBR Technical Specification v1.12
- FBR Digital Invoicing Portal: https://e.fbr.gov.pk
- PRAL Documentation: https://pral.gov.pk
