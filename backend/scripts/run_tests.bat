@echo off
REM Test runner script for backend tests (Windows)

echo ==========================================
echo FBR Invoice Portal - Backend Test Suite
echo ==========================================
echo.

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo Warning: Virtual environment not activated
    echo Activate with: .venv\Scripts\activate
    echo.
)

REM Install test dependencies
echo Checking test dependencies...
pip install -q -r requirements-test.txt

echo.
echo ==========================================
echo Running Test Suite
echo ==========================================
echo.

REM Parse command line arguments
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

if "%TEST_TYPE%"=="unit" (
    echo Running unit tests only...
    pytest -m unit -v
    goto :check_result
)

if "%TEST_TYPE%"=="integration" (
    echo Running integration tests only...
    pytest -m integration -v
    goto :check_result
)

if "%TEST_TYPE%"=="fast" (
    echo Running fast tests excluding slow tests...
    pytest -m "not slow" -v
    goto :check_result
)

if "%TEST_TYPE%"=="slow" (
    echo Running slow tests only...
    pytest -m slow -v
    goto :check_result
)

if "%TEST_TYPE%"=="coverage" (
    echo Running all tests with coverage report...
    pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml -v
    echo.
    echo Coverage report generated in htmlcov\index.html
    goto :check_result
)

if "%TEST_TYPE%"=="parallel" (
    echo Running tests in parallel...
    pytest -n auto -v
    goto :check_result
)

if "%TEST_TYPE%"=="specific" (
    if "%2"=="" (
        echo Error: Please specify test file or path
        echo Usage: run_tests.bat specific tests\test_auth.py
        exit /b 1
    )
    echo Running specific test: %2
    pytest %2 -v
    goto :check_result
)

if "%TEST_TYPE%"=="all" (
    echo Running all tests with coverage...
    pytest --cov=src --cov-report=html --cov-report=term-missing -v
    goto :check_result
)

echo Unknown test type: %TEST_TYPE%
echo.
echo Usage: run_tests.bat [test_type]
echo.
echo Available test types:
echo   all         - Run all tests with coverage (default)
echo   unit        - Run unit tests only
echo   integration - Run integration tests only
echo   fast        - Run fast tests (exclude slow tests)
echo   slow        - Run slow tests only
echo   coverage    - Run all tests with detailed coverage
echo   parallel    - Run tests in parallel
echo   specific    - Run specific test file (requires path)
echo.
echo Examples:
echo   run_tests.bat
echo   run_tests.bat unit
echo   run_tests.bat specific tests\test_auth.py
exit /b 1

:check_result
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo All tests passed!
    echo ==========================================
    exit /b 0
) else (
    echo.
    echo ==========================================
    echo Some tests failed
    echo ==========================================
    exit /b 1
)
