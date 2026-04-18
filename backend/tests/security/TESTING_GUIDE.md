# Phase 1 Security Testing Guide

This guide provides comprehensive testing procedures for all Phase 1 security fixes.

## Prerequisites

```bash
# Install test dependencies
cd backend
uv sync --dev

# Ensure pytest is installed
uv add --dev pytest pytest-asyncio pytest-mock pytest-cov
```

## Running Automated Tests

### Run All Security Tests
```bash
cd backend
pytest tests/security/test_phase1_fixes.py -v
```

### Run Specific Test Classes
```bash
# Test JWT secret validation only
pytest tests/security/test_phase1_fixes.py::TestJWTSecretValidation -v

# Test input sanitization only
pytest tests/security/test_phase1_fixes.py::TestInputSanitization -v

# Test SSL verification only
pytest tests/security/test_phase1_fixes.py::TestSSLVerification -v
```

### Run with Coverage Report
```bash
pytest tests/security/test_phase1_fixes.py --cov=src --cov-report=html
# Open htmlcov/index.html to view coverage report
```

---

## Manual Testing Procedures

### 1. JWT Secret Configuration Testing

#### Test 1.1: Verify Default Secret is Rejected
```bash
# Set the old insecure default
export AUTH_JWT_SECRET="dev-secret-key-change-in-production"

# Try to start the application
cd backend
uv run uvicorn src.main:app --reload

# Expected: Application should FAIL to start with error:
# "Default JWT secret detected. Generate a secure secret with: openssl rand -base64 32"
```

#### Test 1.2: Verify Short Secret is Rejected (Production)
```bash
# Set a short secret in production mode
export AUTH_JWT_SECRET="short"
export APP_ENV="production"

# Try to start the application
uv run uvicorn src.main:app --reload

# Expected: Application should FAIL with error:
# "AUTH_JWT_SECRET must be at least 32 characters in production"
```

#### Test 1.3: Verify Strong Secret is Accepted
```bash
# Generate and set a strong secret
export AUTH_JWT_SECRET=$(openssl rand -base64 32)
export APP_ENV="production"

# Start the application
uv run uvicorn src.main:app --reload

# Expected: Application should START successfully
```

---

### 2. Input Sanitization Testing

#### Test 2.1: Test XSS Prevention via API

**Setup:**
```bash
# Start the application
cd backend
uv run uvicorn src.main:app --reload
```

**Test Script Tag Injection:**
```bash
# Register a user with XSS payload in name
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecureP@ssw0rd123",
    "name": "<script>alert(\"XSS\")</script>"
  }'

# Expected Response: Name should be escaped
# "name": "&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;"
```

**Test IMG Tag with onerror:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test2@example.com",
    "password": "SecureP@ssw0rd123",
    "name": "<img src=x onerror=\"alert(1)\">"
  }'

# Expected: All HTML entities should be escaped
# "name": "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
```

**Test SVG with onload:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test3@example.com",
    "password": "SecureP@ssw0rd123",
    "name": "<svg onload=\"alert(1)\">"
  }'

# Expected: SVG tag should be escaped
```

#### Test 2.2: Test via Frontend
1. Open the registration page in browser
2. Enter XSS payloads in the name field:
   - `<script>alert('XSS')</script>`
   - `<img src=x onerror="alert(1)">`
   - `<svg onload="alert(1)">`
3. Submit the form
4. Check the profile page - name should display as text, not execute

**Verification:**
- Open browser DevTools Console
- No JavaScript alerts should appear
- Inspect the DOM - HTML should be escaped entities

---

### 3. Sensitive Data Logging Testing

#### Test 3.1: Check Application Logs

**Setup:**
```bash
# Enable INFO level logging
export LOG_LEVEL="INFO"

# Start application with log output
cd backend
uv run uvicorn src.main:app --reload 2>&1 | tee app.log
```

**Trigger Invoice Processing:**
```bash
# Login and get token
TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Upload an invoice (if automation endpoint exists)
# Or trigger any FBR validation
```

**Verify Logs:**
```bash
# Check that logs DO NOT contain:
grep -i "ntn" app.log          # Should not find NTN numbers
grep -i "cnic" app.log         # Should not find CNIC numbers
grep -i "address" app.log      # Should not find addresses
grep -i "Original items" app.log  # Should not find this pattern

# Check that logs DO contain metadata:
grep -i "Transformed.*items" app.log  # Should find: "Transformed 5 invoice items"
grep -i "UoM mapping contains" app.log  # Should find metadata
```

**Expected Results:**
- ✅ Logs show: "Transformed 5 invoice items for FBR validation"
- ❌ Logs should NOT show: Full item details, NTN/CNIC, addresses, amounts

---

### 4. SSL/TLS Verification Testing

#### Test 4.1: Verify SSL is Enabled

**Check Code:**
```bash
cd backend
grep -A 5 "def __init__" src/services/fbr_client.py | grep "verify"

# Expected output should include: verify=True
```

#### Test 4.2: Test with Invalid Certificate (Advanced)

**Setup a test server with self-signed certificate:**
```bash
# This test requires a test FBR endpoint with invalid cert
# In production, the real FBR API should work fine
```

**Expected Behavior:**
- With `verify=True`: Connection should fail with SSL error
- With `verify=False`: Connection would succeed (insecure)

#### Test 4.3: Monitor Network Traffic

**Using Browser DevTools:**
1. Open Network tab
2. Trigger FBR API call
3. Check the request details
4. Verify HTTPS is used (not HTTP)
5. Check certificate is valid

---

### 5. FBR Token Exposure Testing

#### Test 5.1: Check Profile Endpoint Response

**Get User Profile:**
```bash
# Login first
TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Get profile
curl -X GET http://localhost:8001/api/v1/auth/profile \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

**Expected Response:**
```json
{
  "id": "...",
  "email": "user@example.com",
  "name": "User Name",
  "fbr_environment": "SANDBOX",
  "fbr_seller_ntn": "1234567890",
  "fbr_business_name": "Business Name",
  "has_sandbox_token": true,
  "has_production_token": false
}
```

**Verify:**
- ✅ Response includes `has_sandbox_token` (boolean)
- ✅ Response includes `has_production_token` (boolean)
- ❌ Response should NOT include `fbr_sandbox_token` (actual token)
- ❌ Response should NOT include `fbr_production_token` (actual token)

#### Test 5.2: Check FBR Credentials Endpoint

```bash
# Get FBR credentials
curl -X GET http://localhost:8001/api/v1/auth/profile/fbr-credentials \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

**Expected Response:**
```json
{
  "fbr_environment": "SANDBOX",
  "fbr_seller_ntn": "1234567890",
  "fbr_business_name": "Business Name",
  "fbr_seller_province": "Punjab",
  "fbr_seller_address": "Address",
  "has_sandbox_token": true,
  "has_production_token": false
}
```

**Verify:**
- ❌ Actual token values should NOT be present
- ✅ Only boolean flags indicating token presence

#### Test 5.3: Check All API Endpoints

**Search for token exposure:**
```bash
# Test all endpoints that might return user data
# Login response
# Profile response
# Settings response
# Any user-related endpoints

# For each response, verify no actual token values are returned
```

---

## Integration Testing Scenarios

### Scenario 1: Complete User Registration Flow

1. **Register with XSS payload in name**
   ```bash
   curl -X POST http://localhost:8001/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "xsstest@example.com",
       "password": "SecureP@ssw0rd123",
       "name": "<script>alert(\"XSS\")</script>"
     }'
   ```

2. **Login**
   ```bash
   TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "xsstest@example.com", "password": "SecureP@ssw0rd123"}' \
     | jq -r '.access_token')
   ```

3. **Get Profile**
   ```bash
   curl -X GET http://localhost:8001/api/v1/auth/profile \
     -H "Authorization: Bearer $TOKEN" \
     | jq .
   ```

4. **Verify:**
   - Name is escaped in response
   - No XSS execution in frontend
   - Token is valid JWT
   - No FBR tokens in response

### Scenario 2: FBR Integration Flow

1. **Setup FBR credentials**
2. **Validate an invoice**
3. **Check logs** - should only show metadata
4. **Verify SSL** - connection should be secure
5. **Check response** - no tokens exposed

---

## Security Checklist

### ✅ Phase 1 Verification Checklist

- [ ] **JWT Secret**
  - [ ] Application rejects default secret
  - [ ] Application rejects short secrets in production
  - [ ] Application accepts strong secrets (32+ chars)
  - [ ] Cannot start without valid JWT secret

- [ ] **Input Sanitization**
  - [ ] `<script>` tags are escaped
  - [ ] `<img>` with onerror is escaped
  - [ ] `<svg>` with onload is escaped
  - [ ] `<iframe>` tags are escaped
  - [ ] Event handlers (onclick, etc.) are escaped
  - [ ] Quotes and ampersands are escaped
  - [ ] Normal text is preserved

- [ ] **Sensitive Data Logging**
  - [ ] Logs do not contain NTN/CNIC numbers
  - [ ] Logs do not contain addresses
  - [ ] Logs do not contain full invoice data
  - [ ] Logs do not contain item details with pricing
  - [ ] Logs contain only metadata (counts, types)

- [ ] **SSL/TLS Verification**
  - [ ] FBR client has `verify=True`
  - [ ] HTTP/2 is enabled
  - [ ] Connections to FBR use HTTPS
  - [ ] Invalid certificates are rejected

- [ ] **FBR Token Exposure**
  - [ ] Profile endpoint returns only boolean flags
  - [ ] Credentials endpoint returns only boolean flags
  - [ ] No actual token values in any API response
  - [ ] Tokens are stored securely in database

---

## Troubleshooting

### Issue: Tests fail with ModuleNotFoundError

**Solution:**
```bash
cd backend
uv sync --dev
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/security/test_phase1_fixes.py -v
```

### Issue: Application won't start - JWT secret error

**Solution:**
```bash
# Generate a strong secret
export AUTH_JWT_SECRET=$(openssl rand -base64 32)

# Or add to .env file
echo "AUTH_JWT_SECRET=$(openssl rand -base64 32)" >> .env
```

### Issue: Cannot connect to FBR API

**Solution:**
- Check internet connection
- Verify FBR API is accessible
- Check firewall settings
- Verify SSL certificates are valid

---

## Reporting Issues

If any test fails:

1. **Document the failure:**
   - Which test failed
   - Error message
   - Steps to reproduce

2. **Check logs:**
   ```bash
   tail -f backend/logs/app.log
   ```

3. **Verify environment:**
   ```bash
   env | grep -E "AUTH_JWT_SECRET|APP_ENV|DATABASE_URL"
   ```

4. **Create issue with:**
   - Test name
   - Expected behavior
   - Actual behavior
   - Environment details
   - Log excerpts

---

## Next Steps

After all Phase 1 tests pass:

1. **Deploy to staging environment**
2. **Run full regression tests**
3. **Perform manual security testing**
4. **Get security team approval**
5. **Proceed to Phase 2 implementation**

---

## Additional Resources

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
