"""
Integration tests for automation API endpoints.
Tests User Stories 1, 3, and 4.
"""
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from uuid import uuid4
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.jwt_utils import create_access_token

BASE_URL = "http://localhost:8001/api/v1/automation"
TEST_USER_ID = str(uuid4())


def create_test_token(user_id: str = TEST_USER_ID) -> str:
    """Create a test JWT token."""
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(hours=1)
    )
    return token


def create_test_excel(num_rows: int = 10, valid: bool = True) -> BytesIO:
    """Create a test Excel file with invoice data."""
    if valid:
        data = {
            "Invoice Number": [f"INV-{i:04d}" for i in range(1, num_rows + 1)],
            "Buyer Name": [f"Buyer {i}" for i in range(1, num_rows + 1)],
            "Buyer NTN": [f"1234567{i:02d}" for i in range(1, num_rows + 1)],
            "Total Amount": [1000.00 + i * 100 for i in range(1, num_rows + 1)],
            "Tax Amount": [150.00 + i * 15 for i in range(1, num_rows + 1)],
            "Scheduled Time": [(datetime.now() + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
                               for i in range(1, num_rows + 1)],
        }
    else:
        # Missing required column
        data = {
            "Invoice Number": [f"INV-{i:04d}" for i in range(1, num_rows + 1)],
            "Buyer Name": [f"Buyer {i}" for i in range(1, num_rows + 1)],
            # Missing Buyer NTN
            "Total Amount": [1000.00 + i * 100 for i in range(1, num_rows + 1)],
        }

    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    return buffer


def test_template_download():
    """T020: Test Excel template download."""
    print("\n[T020] Testing Excel template download...")
    response = requests.get(f"{BASE_URL}/template/download")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.headers['content-type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert len(response.content) > 0
    print("✓ Template download successful")
    return True


def test_excel_upload_valid(token: str):
    """T021: Test Excel upload with valid data."""
    print("\n[T021] Testing Excel upload with valid data (10 invoices)...")

    excel_file = create_test_excel(num_rows=10, valid=True)
    files = {'file': ('test_invoices.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.post(f"{BASE_URL}/excel/upload", files=files, headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert 'session_id' in data
    assert data['total_rows'] == 10
    print(f"✓ Upload successful: {data['message']}")
    print(f"  Session ID: {data['session_id']}")
    return data['session_id']


def test_excel_upload_duplicate(token: str):
    """T022: Test Excel upload rejection for duplicate invoice numbers."""
    print("\n[T022] Testing duplicate invoice number rejection...")

    # Upload same file twice
    excel_file = create_test_excel(num_rows=5, valid=True)
    files = {'file': ('test_invoices.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    headers = {'Authorization': f'Bearer {token}'}

    # First upload
    response1 = requests.post(f"{BASE_URL}/excel/upload", files=files, headers=headers)
    assert response1.status_code == 200

    # Second upload with same invoice numbers
    excel_file.seek(0)
    files = {'file': ('test_invoices_dup.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    response2 = requests.post(f"{BASE_URL}/excel/upload", files=files, headers=headers)

    # Should reject duplicates
    if response2.status_code == 400:
        print(f"✓ Duplicate rejection working: {response2.json()['detail']}")
        return True
    else:
        print(f"⚠ Warning: Duplicate check may not be working (got {response2.status_code})")
        return False


def test_excel_upload_missing_columns(token: str):
    """T023: Test Excel upload rejection for missing columns."""
    print("\n[T023] Testing missing columns rejection...")

    excel_file = create_test_excel(num_rows=5, valid=False)
    files = {'file': ('test_invalid.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.post(f"{BASE_URL}/excel/upload", files=files, headers=headers)

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    print(f"✓ Missing columns rejected: {response.json()['detail']}")
    return True


def test_excel_upload_too_many_rows(token: str):
    """T024: Test Excel upload rejection for >1000 rows."""
    print("\n[T024] Testing >1000 rows rejection...")

    excel_file = create_test_excel(num_rows=1001, valid=True)
    files = {'file': ('test_large.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.post(f"{BASE_URL}/excel/upload", files=files, headers=headers)

    if response.status_code == 400:
        print(f"✓ Large file rejected: {response.json()['detail']}")
        return True
    else:
        print(f"⚠ Warning: Row limit check may not be working (got {response.status_code})")
        return False


def test_dashboard_stats(token: str):
    """T035: Test dashboard statistics endpoint."""
    print("\n[T035] Testing dashboard statistics...")

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert 'total_invoices' in data
    assert 'pending_invoices' in data
    assert 'submitted_invoices' in data
    assert 'failed_invoices' in data
    print(f"✓ Dashboard stats retrieved:")
    print(f"  Total: {data['total_invoices']}, Pending: {data['pending_invoices']}, "
          f"Submitted: {data['submitted_invoices']}, Failed: {data['failed_invoices']}")
    return True


def test_invoice_list(token: str):
    """T036: Test invoice list with filtering."""
    print("\n[T036] Testing invoice list filtering...")

    headers = {'Authorization': f'Bearer {token}'}

    # Test without filters
    response = requests.get(f"{BASE_URL}/dashboard/invoices", headers=headers)
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Invoice list retrieved: {len(data.get('invoices', []))} invoices")

    # Test with status filter
    response = requests.get(f"{BASE_URL}/dashboard/invoices?status=pending", headers=headers)
    assert response.status_code == 200
    print(f"✓ Status filter working")

    return True


def test_agent_health(token: str):
    """T083: Test AI Agent health endpoint."""
    print("\n[T083] Testing AI Agent health endpoint...")

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/agent/health", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Agent health retrieved:")
        print(f"  Status: {data.get('status', 'unknown')}")
        return True
    elif response.status_code == 404:
        print("⚠ No health check data yet (agent may not have run)")
        return True
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        return False


def test_agent_decisions(token: str):
    """T084: Test AI Agent decisions endpoint."""
    print("\n[T084] Testing AI Agent decisions endpoint...")

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/agent/decisions", headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    print(f"✓ Agent decisions retrieved: {len(data.get('decisions', []))} decisions")
    return True


def run_all_tests():
    """Run all automation API tests."""
    print("=" * 60)
    print("AUTOMATION API INTEGRATION TESTS")
    print("=" * 60)

    # Create test token
    print(f"\nCreating test token for user: {TEST_USER_ID}")
    token = create_test_token()
    print("✓ Token created")

    results = {}

    # User Story 1 Tests
    print("\n" + "=" * 60)
    print("USER STORY 1: Excel Template and Upload")
    print("=" * 60)

    try:
        results['T020'] = test_template_download()
    except Exception as e:
        print(f"✗ T020 failed: {e}")
        results['T020'] = False

    try:
        session_id = test_excel_upload_valid(token)
        results['T021'] = True
    except Exception as e:
        print(f"✗ T021 failed: {e}")
        results['T021'] = False

    try:
        results['T022'] = test_excel_upload_duplicate(token)
    except Exception as e:
        print(f"✗ T022 failed: {e}")
        results['T022'] = False

    try:
        results['T023'] = test_excel_upload_missing_columns(token)
    except Exception as e:
        print(f"✗ T023 failed: {e}")
        results['T023'] = False

    try:
        results['T024'] = test_excel_upload_too_many_rows(token)
    except Exception as e:
        print(f"✗ T024 failed: {e}")
        results['T024'] = False

    # User Story 3 Tests
    print("\n" + "=" * 60)
    print("USER STORY 3: Dashboard and Monitoring")
    print("=" * 60)

    try:
        results['T035'] = test_dashboard_stats(token)
    except Exception as e:
        print(f"✗ T035 failed: {e}")
        results['T035'] = False

    try:
        results['T036'] = test_invoice_list(token)
    except Exception as e:
        print(f"✗ T036 failed: {e}")
        results['T036'] = False

    # User Story 5 Tests
    print("\n" + "=" * 60)
    print("USER STORY 5: AI Agent Status")
    print("=" * 60)

    try:
        results['T083'] = test_agent_health(token)
    except Exception as e:
        print(f"✗ T083 failed: {e}")
        results['T083'] = False

    try:
        results['T084'] = test_agent_decisions(token)
    except Exception as e:
        print(f"✗ T084 failed: {e}")
        results['T084'] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_id, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_id}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
