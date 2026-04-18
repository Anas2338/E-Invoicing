#!/bin/bash

# Integration tests for automation API endpoints
# Tests User Stories 1, 3, and 4

set -e

BASE_URL="http://localhost:8001/api/v1/automation"
TEST_USER_ID="550e8400-e29b-41d4-a716-446655440000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "AUTOMATION API INTEGRATION TESTS"
echo "============================================================"

# Create test JWT token
echo -e "\nCreating test JWT token..."
cd "D:\GIAIC\Agentic-AI\E-Invoicing\backend"
TOKEN=$(uv run python -c "
import sys
sys.path.insert(0, 'src')
from src.utils.jwt_utils import create_access_token
from datetime import timedelta
token = create_access_token(data={'sub': '$TEST_USER_ID'}, expires_delta=timedelta(hours=1))
print(token)
")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to create token${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Token created${NC}"

# Test counters
PASSED=0
FAILED=0

# Helper function to run test
run_test() {
    local test_id=$1
    local test_name=$2
    local command=$3

    echo -e "\n[$test_id] $test_name..."
    if eval "$command"; then
        echo -e "${GREEN}✓ $test_id PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ $test_id FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

echo -e "\n============================================================"
echo "USER STORY 1: Excel Template and Upload"
echo "============================================================"

# T020: Test template download
run_test "T020" "Test Excel template download" '
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/template/download" -o /tmp/test_template.xlsx)
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] && [ -f /tmp/test_template.xlsx ]; then
        file_type=$(file /tmp/test_template.xlsx | grep -o "Microsoft Excel")
        [ ! -z "$file_type" ]
    else
        false
    fi
'

# T021: Test valid Excel upload
echo -e "\n[T021] Test Excel upload with valid data..."
echo "Creating test Excel file..."
uv run python -c "
import pandas as pd
from datetime import datetime, timedelta
data = {
    'Invoice Number': [f'INV-TEST-{i:04d}' for i in range(1, 11)],
    'Buyer Name': [f'Test Buyer {i}' for i in range(1, 11)],
    'Buyer NTN': [f'1234567{i:02d}' for i in range(1, 11)],
    'Total Amount': [1000.00 + i * 100 for i in range(1, 11)],
    'Tax Amount': [150.00 + i * 15 for i in range(1, 11)],
    'Scheduled Time': [(datetime.now() + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(1, 11)],
}
df = pd.DataFrame(data)
df.to_excel('/tmp/test_valid.xlsx', index=False, engine='openpyxl')
print('Test file created')
"

response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/excel/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_valid.xlsx")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "200" ]; then
    echo "$body" | python -m json.tool
    echo -e "${GREEN}✓ T021 PASS${NC}"
    ((PASSED++))
    SESSION_ID=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
else
    echo "Status: $status_code"
    echo "$body"
    echo -e "${RED}✗ T021 FAIL${NC}"
    ((FAILED++))
fi

# T023: Test missing columns
echo -e "\n[T023] Test Excel upload rejection for missing columns..."
uv run python -c "
import pandas as pd
data = {
    'Invoice Number': ['INV-BAD-001'],
    'Buyer Name': ['Bad Buyer'],
    # Missing Buyer NTN
    'Total Amount': [1000.00],
}
df = pd.DataFrame(data)
df.to_excel('/tmp/test_invalid.xlsx', index=False, engine='openpyxl')
"

response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/excel/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_invalid.xlsx")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "400" ]; then
    echo "Rejected as expected: $body"
    echo -e "${GREEN}✓ T023 PASS${NC}"
    ((PASSED++))
else
    echo "Expected 400, got $status_code"
    echo -e "${RED}✗ T023 FAIL${NC}"
    ((FAILED++))
fi

echo -e "\n============================================================"
echo "USER STORY 3: Dashboard and Monitoring"
echo "============================================================"

# T035: Test dashboard stats
run_test "T035" "Test dashboard statistics" '
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/dashboard/stats" \
        -H "Authorization: Bearer $TOKEN")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "200" ]; then
        echo "$body" | python -m json.tool
        echo "$body" | grep -q "total_invoices"
    else
        echo "Status: $status_code"
        echo "$body"
        false
    fi
'

# T036: Test invoice list
run_test "T036" "Test invoice list with filtering" '
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/dashboard/invoices" \
        -H "Authorization: Bearer $TOKEN")
    status_code=$(echo "$response" | tail -n1)

    if [ "$status_code" = "200" ]; then
        # Test with status filter
        response2=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/dashboard/invoices?status=pending" \
            -H "Authorization: Bearer $TOKEN")
        status_code2=$(echo "$response2" | tail -n1)
        [ "$status_code2" = "200" ]
    else
        false
    fi
'

echo -e "\n============================================================"
echo "USER STORY 5: AI Agent Status"
echo "============================================================"

# T083: Test agent health
echo -e "\n[T083] Test AI Agent health endpoint..."
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/agent/health" \
    -H "Authorization: Bearer $TOKEN")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "200" ]; then
    echo "$body" | python -m json.tool
    echo -e "${GREEN}✓ T083 PASS${NC}"
    ((PASSED++))
elif [ "$status_code" = "404" ]; then
    echo -e "${YELLOW}⚠ No health check data yet (agent may not have run)${NC}"
    echo -e "${GREEN}✓ T083 PASS (endpoint working)${NC}"
    ((PASSED++))
else
    echo "Status: $status_code"
    echo "$body"
    echo -e "${RED}✗ T083 FAIL${NC}"
    ((FAILED++))
fi

# T084: Test agent decisions
run_test "T084" "Test AI Agent decisions endpoint" '
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/agent/decisions" \
        -H "Authorization: Bearer $TOKEN")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "200" ]; then
        echo "$body" | python -m json.tool | head -20
        true
    else
        echo "Status: $status_code"
        echo "$body"
        false
    fi
'

# Summary
echo -e "\n============================================================"
echo "TEST SUMMARY"
echo "============================================================"

TOTAL=$((PASSED + FAILED))
PERCENTAGE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")

echo -e "\nTotal: ${GREEN}$PASSED${NC}/${TOTAL} tests passed (${PERCENTAGE}%)"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}$FAILED tests failed${NC}"
    exit 1
fi
