#!/bin/bash
# Test runner script for backend tests

set -e

echo "=========================================="
echo "FBR Invoice Portal - Backend Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Activate with: source .venv/bin/activate (Linux/Mac) or .venv\\Scripts\\activate (Windows)"
    echo ""
fi

# Install test dependencies if needed
echo "Checking test dependencies..."
pip install -q -r requirements-test.txt

echo ""
echo "=========================================="
echo "Running Test Suite"
echo "=========================================="
echo ""

# Parse command line arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-true}

case $TEST_TYPE in
    unit)
        echo "Running unit tests only..."
        pytest -m unit -v
        ;;
    integration)
        echo "Running integration tests only..."
        pytest -m integration -v
        ;;
    fast)
        echo "Running fast tests (excluding slow tests)..."
        pytest -m "not slow" -v
        ;;
    slow)
        echo "Running slow tests only..."
        pytest -m slow -v
        ;;
    coverage)
        echo "Running all tests with coverage report..."
        pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml -v
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    parallel)
        echo "Running tests in parallel..."
        pytest -n auto -v
        ;;
    specific)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify test file or path${NC}"
            echo "Usage: ./run_tests.sh specific tests/test_auth.py"
            exit 1
        fi
        echo "Running specific test: $2"
        pytest "$2" -v
        ;;
    all)
        echo "Running all tests with coverage..."
        pytest --cov=src --cov-report=html --cov-report=term-missing -v

        # Check coverage threshold
        COVERAGE_PERCENT=$(pytest --cov=src --cov-report=term | grep "TOTAL" | awk '{print $4}' | sed 's/%//')

        if [ ! -z "$COVERAGE_PERCENT" ]; then
            if (( $(echo "$COVERAGE_PERCENT >= 80" | bc -l) )); then
                echo ""
                echo -e "${GREEN}✓ Coverage threshold met: ${COVERAGE_PERCENT}%${NC}"
            else
                echo ""
                echo -e "${YELLOW}⚠ Coverage below threshold: ${COVERAGE_PERCENT}% (target: 80%)${NC}"
            fi
        fi
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [test_type]"
        echo ""
        echo "Available test types:"
        echo "  all         - Run all tests with coverage (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  fast        - Run fast tests (exclude slow tests)"
        echo "  slow        - Run slow tests only"
        echo "  coverage    - Run all tests with detailed coverage"
        echo "  parallel    - Run tests in parallel"
        echo "  specific    - Run specific test file (requires path)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh specific tests/test_auth.py"
        exit 1
        ;;
esac

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ All tests passed!"
    echo -e "==========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ Some tests failed"
    echo -e "==========================================${NC}"
    exit 1
fi
