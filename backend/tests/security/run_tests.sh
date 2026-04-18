#!/bin/bash
# Security Test Runner for Phase 1 Fixes
# Run this script to execute all Phase 1 security tests

set -e  # Exit on error

echo "================================================"
echo "Phase 1 Security Testing Suite"
echo "E-Invoicing System - FBR Portal"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must be run from backend directory${NC}"
    exit 1
fi

# Check if AUTH_JWT_SECRET is set
if [ -z "$AUTH_JWT_SECRET" ]; then
    echo -e "${YELLOW}Warning: AUTH_JWT_SECRET not set${NC}"
    echo "Generating temporary secret for testing..."
    export AUTH_JWT_SECRET=$(openssl rand -base64 32)
    echo -e "${GREEN}Temporary secret generated${NC}"
fi

echo "Step 1: Installing test dependencies..."
uv sync --dev
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo "Step 2: Running JWT Secret Validation Tests..."
pytest tests/security/test_phase1_fixes.py::TestJWTSecretValidation -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ JWT Secret tests passed${NC}"
else
    echo -e "${RED}✗ JWT Secret tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 3: Running Input Sanitization Tests..."
pytest tests/security/test_phase1_fixes.py::TestInputSanitization -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Input Sanitization tests passed${NC}"
else
    echo -e "${RED}✗ Input Sanitization tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 4: Running Sensitive Data Logging Tests..."
pytest tests/security/test_phase1_fixes.py::TestSensitiveDataLogging -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Sensitive Data Logging tests passed${NC}"
else
    echo -e "${RED}✗ Sensitive Data Logging tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 5: Running SSL/TLS Verification Tests..."
pytest tests/security/test_phase1_fixes.py::TestSSLVerification -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SSL/TLS Verification tests passed${NC}"
else
    echo -e "${RED}✗ SSL/TLS Verification tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 6: Running FBR Token Exposure Tests..."
pytest tests/security/test_phase1_fixes.py::TestFBRTokenExposure -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ FBR Token Exposure tests passed${NC}"
else
    echo -e "${RED}✗ FBR Token Exposure tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 7: Running Integration Tests..."
pytest tests/security/test_phase1_fixes.py::TestIntegrationScenarios -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    exit 1
fi
echo ""

echo "Step 8: Generating Coverage Report..."
pytest tests/security/test_phase1_fixes.py --cov=src --cov-report=html --cov-report=term
echo -e "${GREEN}✓ Coverage report generated in htmlcov/index.html${NC}"
echo ""

echo "================================================"
echo -e "${GREEN}All Phase 1 Security Tests Passed!${NC}"
echo "================================================"
echo ""
echo "Next Steps:"
echo "1. Review coverage report: open htmlcov/index.html"
echo "2. Run manual tests from TESTING_GUIDE.md"
echo "3. Deploy to staging environment"
echo "4. Proceed to Phase 2 implementation"
echo ""
