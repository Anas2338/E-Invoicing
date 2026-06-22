"""
Master Data API endpoints for FBR-compliant reference data.
Provides dropdown options for invoice forms based on FBR specifications.
Fetches data from local database (synced daily from FBR APIs).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import logging

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user import User
from src.models.fbr_master_data import (
    FBRProvince,
    FBRUOM,
    FBRHSCode,
    FBRTransactionType,
    FBRInvoiceType,
    FBRUserHSCodeUOM,
    FBRTaxRate
)

router = APIRouter()
logger = logging.getLogger(__name__)


# FBR API Base URLs (for dynamic endpoints that still need live API calls)
FBR_BASE_URL = "https://gw.fbr.gov.pk"


# Fallback hardcoded values for tax rates and sale types (no direct FBR API available)
FALLBACK_TAX_RATES = [
    {"rate": "0", "name": "0% - Zero rated"},
    {"rate": "1", "name": "1%"},
    {"rate": "5", "name": "5%"},
    {"rate": "10", "name": "10%"},
    {"rate": "12", "name": "12%"},
    {"rate": "15", "name": "15%"},
    {"rate": "17", "name": "17%"},
    {"rate": "18", "name": "18% - Standard rate"}
]

FALLBACK_SALE_TYPES = [
    {"code": "01", "name": "Goods at standard rate (default)"},
    {"code": "02", "name": "Goods at reduced rate"},
    {"code": "03", "name": "Goods at zero rate"},
    {"code": "04", "name": "Exempt goods"},
    {"code": "05", "name": "Services"},
    {"code": "06", "name": "3rd Schedule Goods"},
    {"code": "07", "name": "Steel Melting and re-rolling"},
    {"code": "08", "name": "Ship breaking"},
    {"code": "09", "name": "Cotton Ginners"},
    {"code": "10", "name": "Telecommunication services"},
    {"code": "11", "name": "Toll Manufacturing"},
    {"code": "12", "name": "Petroleum Products"},
    {"code": "13", "name": "Electricity Supply to Retailers"},
    {"code": "14", "name": "Gas to CNG stations"},
    {"code": "15", "name": "Mobile Phones"},
    {"code": "16", "name": "Processing/Conversion of Goods"},
    {"code": "17", "name": "Goods (FED in ST Mode)"},
    {"code": "18", "name": "Services (FED in ST Mode)"},
    {"code": "19", "name": "Electric Vehicle"},
    {"code": "20", "name": "Cement/Concrete Block"},
    {"code": "21", "name": "Potassium Chlorate"},
    {"code": "22", "name": "CNG Sales"},
    {"code": "23", "name": "Goods as per SRO.297(I)/2023"},
    {"code": "24", "name": "Non-Adjustable Supplies"}
]

FALLBACK_REGISTRATION_TYPES = [
    {"code": "REG", "name": "Registered"},
    {"code": "UNREG", "name": "Unregistered"}
]


async def get_user_fbr_token(db, user_id: str, environment: str = "SANDBOX") -> Optional[str]:
    """
    Get user's FBR access token based on environment.
    Decrypts the token before returning.
    Used for dynamic API calls that require user-specific token.

    Args:
        db: Database session
        user_id: User ID
        environment: SANDBOX or PRODUCTION

    Returns:
        Decrypted FBR access token or None
    """
    try:
        from src.utils.encryption import get_encryption_service

        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            logger.warning(f"User {user_id} not found in database")
            return None

        encrypted_token = None
        if environment == "SANDBOX":
            encrypted_token = user.fbr_sandbox_token or user.fbr_access_token
            # Fall back to production token if sandbox is not configured
            if not encrypted_token:
                encrypted_token = user.fbr_production_token
        else:
            encrypted_token = user.fbr_production_token or user.fbr_access_token
            # Fall back to sandbox token if production is not configured
            if not encrypted_token:
                encrypted_token = user.fbr_sandbox_token

        if not encrypted_token:
            logger.warning(
                f"User {user_id} ({user.email}) has no FBR token configured "
                f"(sandbox={'set' if user.fbr_sandbox_token else 'empty'}, "
                f"production={'set' if user.fbr_production_token else 'empty'}, "
                f"legacy={'set' if user.fbr_access_token else 'empty'})"
            )
            return None

        # Decrypt the token before returning
        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(encrypted_token)
            logger.info(f"Successfully decrypted FBR token for user {user.email}")
            return decrypted_token
        except Exception as decrypt_error:
            logger.error(f"Failed to decrypt FBR token for user {user_id}: {decrypt_error}")
            return None

    except Exception as e:
        logger.error(f"Error getting user FBR token: {str(e)}")
        return None


async def fetch_from_fbr(endpoint: str, token: Optional[str], environment: str = "SANDBOX") -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data from FBR API (for dynamic endpoints).

    Args:
        endpoint: FBR API endpoint path
        token: FBR access token
        environment: SANDBOX or PRODUCTION

    Returns:
        List of data from FBR or None if failed
    """
    if not token:
        logger.warning("No FBR token provided, returning empty data")
        return None

    url = f"{FBR_BASE_URL}{endpoint}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning(f"Unauthorized access to FBR API: {endpoint}")
                return None
            else:
                logger.error(f"FBR API error: {response.status_code} - {response.text}")
                return None

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching from FBR API: {endpoint}")
        return None
    except Exception as e:
        logger.error(f"Error fetching from FBR API: {str(e)}")
        return None


@router.get("/provinces", response_model=List[Dict[str, Any]])
async def get_provinces(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of FBR-compliant provinces from local database.

    Returns:
        List of provinces with code and name
    """
    try:
        provinces = db.query(FBRProvince).all()
        return [{"code": p.code, "name": p.name} for p in provinces]
    except Exception as e:
        logger.error(f"Error fetching provinces from database: {str(e)}")
        return []


@router.get("/uom", response_model=List[Dict[str, Any]])
async def get_uom_codes(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of FBR-compliant Unit of Measure codes from local database.

    Returns:
        List of UOM codes with code and name
    """
    try:
        uom_codes = db.query(FBRUOM).all()
        return [{"code": u.code, "name": u.name} for u in uom_codes]
    except Exception as e:
        logger.error(f"Error fetching UOM codes from database: {str(e)}")
        return []


@router.get("/tax-rates", response_model=List[Dict[str, str]])
async def get_tax_rates(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get list of FBR-compliant tax rates from local database.
    Falls back to hardcoded values if no synced rates exist.

    Returns:
        List of tax rates with rate and name
    """
    try:
        # Get all unique rates from the synced tax rates table
        rates = db.query(FBRTaxRate).all()
        if rates:
            # Deduplicate by rate_value while preserving order
            seen = set()
            result = []
            for r in rates:
                if r.rate_value not in seen:
                    seen.add(r.rate_value)
                    result.append({"rate": r.rate_value, "name": r.rate_desc})
            return result
    except Exception as e:
        logger.error(f"Error fetching tax rates from database: {str(e)}")

    return FALLBACK_TAX_RATES


@router.get("/tax-rates/by-transaction-type", response_model=List[Dict[str, str]])
async def get_tax_rates_by_transaction_type(
    transaction_type_code: str,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get tax rates filtered by transaction type from local database.

    This is system-wide shared data (no user_id filter) — synced by admin.
    Falls back to hardcoded values if no rates exist for this transaction type.

    Args:
        transaction_type_code: FBR transaction type code (e.g., "01", "02")

    Returns:
        List of tax rates applicable to this transaction type
    """
    try:
        rates = db.query(FBRTaxRate).filter(
            FBRTaxRate.transaction_type_code == transaction_type_code.strip()
        ).all()

        if rates:
            result = []
            seen = set()
            for r in rates:
                if r.rate_value not in seen:
                    seen.add(r.rate_value)
                    result.append({"rate": r.rate_value, "name": r.rate_desc})
            logger.info(
                f"Returning {len(result)} tax rates for transaction type {transaction_type_code}"
            )
            return result
    except Exception as e:
        logger.error(
            f"Error fetching tax rates for transaction type {transaction_type_code}: {str(e)}"
        )

    logger.info(
        f"No synced tax rates for transaction type {transaction_type_code}, using fallback"
    )
    return FALLBACK_TAX_RATES


@router.get("/sale-types", response_model=List[Dict[str, str]])
async def get_sale_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get list of FBR-compliant sale types.
    Note: FBR doesn't have a direct API for sale types, using fallback values.

    Returns:
        List of sale types with code and name
    """
    return FALLBACK_SALE_TYPES


@router.get("/registration-types", response_model=List[Dict[str, str]])
async def get_registration_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get list of FBR-compliant registration types.
    Note: FBR doesn't have a direct API for registration types, using fallback values.

    Returns:
        List of registration types with code and name
    """
    return FALLBACK_REGISTRATION_TYPES


@router.get("/invoice-types", response_model=List[Dict[str, Any]])
async def get_invoice_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of FBR-compliant invoice types from local database.

    Returns:
        List of invoice types with code and name
    """
    try:
        invoice_types = db.query(FBRInvoiceType).all()
        return [{"code": i.code, "name": i.name} for i in invoice_types]
    except Exception as e:
        logger.error(f"Error fetching invoice types from database: {str(e)}")
        return []


@router.get("/hs-codes/validate/{hs_code}", response_model=Dict[str, Any])
async def validate_hs_code(
    hs_code: str,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Validate a single HS code against the local database.

    Args:
        hs_code: HS code to validate

    Returns:
        Dictionary with validation result
    """
    try:
        hs_code_obj = db.query(FBRHSCode).filter(FBRHSCode.code == hs_code.strip()).first()

        if hs_code_obj:
            return {
                "valid": True,
                "code": hs_code_obj.code,
                "description": hs_code_obj.description
            }
        else:
            return {
                "valid": False,
                "code": hs_code,
                "description": None
            }
    except Exception as e:
        logger.error(f"Error validating HS code {hs_code}: {str(e)}")
        return {
            "valid": False,
            "code": hs_code,
            "description": None
        }


@router.get("/hs-codes", response_model=List[Dict[str, str]])
async def get_hs_codes(
    search: Optional[str] = Query(None, description="Filter HS codes by code prefix (case-insensitive)"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of HS codes from local database.
    Optionally filter by a search prefix for autocomplete.

    Returns:
        List of HS codes with code and description
    """
    try:
        query = db.query(FBRHSCode)
        if search:
            query = query.filter(FBRHSCode.code.ilike(f"{search.strip()}%"))
        hs_codes = query.order_by(FBRHSCode.code).limit(limit).all()
        result = [{"code": h.code, "description": h.description} for h in hs_codes]
        logger.info(f"Returning {len(result)} HS codes from database (search={search})")
        return result
    except Exception as e:
        logger.error(f"Error fetching HS codes from database: {str(e)}")
        return []


@router.get("/transaction-types", response_model=List[Dict[str, str]])
async def get_transaction_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of transaction types from local database.

    Returns:
        List of transaction types with code and name
    """
    try:
        transaction_types = db.query(FBRTransactionType).all()
        result = [{"code": t.code, "name": t.name.strip()} for t in transaction_types]
        return result
    except Exception as e:
        logger.error(f"Error fetching transaction types from database: {str(e)}")
        return []


# Dynamic endpoints that still require live FBR API calls (parameter-based queries)

@router.get("/sro-schedule", response_model=List[Dict[str, Any]])
async def get_sro_schedule(
    rate_id: int,
    date: str,
    origination_supplier_csv: int,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get SRO schedule based on rate ID, date, and supplier type.
    This endpoint requires live FBR API call as it's parameter-based.

    Args:
        rate_id: Tax rate ID
        date: Invoice date (format: DD-MMM-YYYY, e.g., "04-Feb-2024")
        origination_supplier_csv: Supplier type (1 or 0)

    Returns:
        List of applicable SRO schedules with ID and description
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty SRO schedule list")
        return []

    endpoint = f"/pdi/v1/SroSchedule?rate_id={rate_id}&date={date}&origination_supplier_csv={origination_supplier_csv}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    result = []
    for item in fbr_data:
        sro_id = str(item.get("srO_ID", ""))
        if sro_id:
            result.append({
                "id": sro_id,
                "description": item.get("srO_DESC", "")
            })

    logger.info(f"Returning {len(result)} SRO schedules for rate_id={rate_id}")
    return result


@router.get("/sale-type-to-rate", response_model=List[Dict[str, Any]])
async def get_sale_type_to_rate(
    date: str,
    trans_type_id: int,
    origination_supplier: int,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get applicable tax rates based on date, transaction type, and province.
    This endpoint requires live FBR API call as it's parameter-based.

    Args:
        date: Invoice date (format: DD-MMM-YYYY, e.g., "24-Feb-2024")
        trans_type_id: Transaction type ID
        origination_supplier: Province ID

    Returns:
        List of applicable tax rates
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning fallback tax rates")
        return FALLBACK_TAX_RATES

    endpoint = f"/pdi/v2/SaleTypeToRate?date={date}&transTypeId={trans_type_id}&originationSupplier={origination_supplier}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        logger.warning("FBR API returned no data, returning fallback tax rates")
        return FALLBACK_TAX_RATES

    result = []
    for item in fbr_data:
        rate_value = item.get("ratE_VALUE") or item.get("rate_value")
        rate_desc = item.get("ratE_DESC") or item.get("rate_desc", "")

        if rate_value is not None:
            if rate_desc == f"{rate_value}%":
                name = rate_desc
            elif rate_desc:
                cleaned_desc = rate_desc
                if rate_desc.startswith(f"{rate_value}%"):
                    cleaned_desc = rate_desc[len(f"{rate_value}%"):].strip()
                    if cleaned_desc.startswith("-"):
                        cleaned_desc = cleaned_desc[1:].strip()

                name = f"{rate_value}% - {cleaned_desc}" if cleaned_desc else f"{rate_value}%"
            else:
                name = f"{rate_value}%"

            result.append({
                "rate": str(rate_value),
                "name": name
            })

    if not result:
        logger.warning("No valid rates in FBR response, returning fallback tax rates")
        return FALLBACK_TAX_RATES

    logger.info(f"Returning {len(result)} rates from FBR for trans_type_id={trans_type_id}")
    return result


@router.get("/hs-uom", response_model=List[Dict[str, Any]])
async def get_hs_uom(
    hs_code: str,
    annexure_id: int,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get valid UOM options for a specific HS code.
    This endpoint requires live FBR API call as it's parameter-based.

    Args:
        hs_code: HS code (e.g., "5904.9000")
        annexure_id: Sales annexure ID

    Returns:
        List of valid UOM options for the HS code
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty HS-UOM list")
        return []

    endpoint = f"/pdi/v2/HS_UOM?hs_code={hs_code}&annexure_id={annexure_id}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    result = []
    for item in fbr_data:
        uom_id = str(item.get("uoM_ID", ""))
        if uom_id:
            result.append({
                "code": uom_id,
                "name": item.get("description", "")
            })

    logger.info(f"Returning {len(result)} UOM options for HS code {hs_code}")
    return result


@router.get("/hs-uom/cached", response_model=List[Dict[str, Any]])
async def get_hs_uom_cached(
    hs_code: str,
    annexure_id: int = 3,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get valid UOM options for a specific HS code with user-scoped local caching.

    First checks the user's local cache (fbr_user_hs_code_uom). If found,
    returns immediately. Otherwise fetches from FBR API using the user's
    own FBR token, caches the results, and returns them.

    Data is scoped per-user — User A cannot see User B's cached HS UOMs.

    Args:
        hs_code: HS code (e.g., "5904.9000")
        annexure_id: Sales annexure ID (default: 3)
    """
    try:
        from uuid import UUID

        user_uuid = UUID(user_id)

        # Step 1: Check local cache for this user + HS code
        cached = db.query(FBRUserHSCodeUOM).filter(
            FBRUserHSCodeUOM.hs_code == hs_code.strip(),
            FBRUserHSCodeUOM.user_id == user_uuid
        ).all()

        if cached:
            logger.info(
                f"Returning {len(cached)} cached UOMs for HS code {hs_code} (user {user_id})"
            )
            return [{"code": c.uom_id, "name": c.uom_description} for c in cached]

        # Step 2: Not cached — fetch from FBR using user's own token
        token = await get_user_fbr_token(db, user_id, environment)

        if not token:
            logger.warning(
                f"No FBR token for user {user_id}, cannot fetch HS-UOM for {hs_code}"
            )
            return []

        endpoint = f"/pdi/v2/HS_UOM?hs_code={hs_code.strip()}&annexure_id={annexure_id}"
        fbr_data = await fetch_from_fbr(endpoint, token, environment)

        if not fbr_data:
            logger.warning(f"No FBR HS-UOM data for HS code {hs_code}")
            return []

        # Step 3: Save to local cache and return
        result = []
        for item in fbr_data:
            uom_id = str(item.get("uoM_ID", ""))
            if uom_id:
                result.append({
                    "code": uom_id,
                    "name": item.get("description", "")
                })
                try:
                    cache_entry = FBRUserHSCodeUOM(
                        user_id=user_uuid,
                        hs_code=hs_code.strip(),
                        uom_id=uom_id,
                        uom_description=item.get("description", "")
                    )
                    db.add(cache_entry)
                except Exception as insert_err:
                    logger.warning(f"Could not cache HS-UOM entry: {insert_err}")

        if result:
            try:
                db.commit()
            except Exception as commit_err:
                logger.warning(f"Could not commit HS-UOM cache: {commit_err}")
                db.rollback()

        logger.info(
            f"Fetched and cached {len(result)} UOM options for HS code {hs_code} (user {user_id})"
        )
        return result

    except Exception as e:
        logger.error(f"Error in get_hs_uom_cached for HS code {hs_code}: {str(e)}")
        return []


@router.get("/sro-item-details", response_model=List[Dict[str, Any]])
async def get_sro_item_details(
    date: str,
    sro_id: int,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get detailed SRO item information based on date and SRO ID.
    This endpoint requires live FBR API call as it's parameter-based.

    Args:
        date: Invoice date (format: YYYY-MM-DD, e.g., "2025-03-25")
        sro_id: SRO schedule ID

    Returns:
        List of SRO item details
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty SRO item details list")
        return []

    endpoint = f"/pdi/v2/SROItem?date={date}&sro_id={sro_id}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    logger.info(f"Returning {len(fbr_data)} SRO item details for sro_id={sro_id}")
    return fbr_data


@router.get("/all", response_model=Dict[str, Any])
async def get_all_master_data(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get all master data in a single request.
    Fetches data from local database (synced daily from FBR APIs).

    Note: HS codes are excluded from this endpoint for performance.
    Users should fetch HS codes separately only when needed.

    Returns:
        Dictionary containing all master data (excluding HS codes)
    """
    try:
        # Fetch all data from database (excluding HS codes for performance)
        provinces = db.query(FBRProvince).all()
        uom = db.query(FBRUOM).all()
        invoice_types = db.query(FBRInvoiceType).all()
        transaction_types = db.query(FBRTransactionType).all()

        # Tax rates: pull from synced DB, fallback to hardcoded
        tax_rates = FALLBACK_TAX_RATES
        try:
            db_rates = db.query(FBRTaxRate).all()
            if db_rates:
                seen = set()
                tax_rates = []
                for r in db_rates:
                    if r.rate_value not in seen:
                        seen.add(r.rate_value)
                        tax_rates.append({"rate": r.rate_value, "name": r.rate_desc})
        except Exception:
            pass  # Table may not exist yet, use fallback

        return {
            "provinces": [{"code": p.code, "name": p.name} for p in provinces],
            "uom": [{"code": u.code, "name": u.name} for u in uom],
            "tax_rates": tax_rates,
            "sale_types": FALLBACK_SALE_TYPES,
            "registration_types": FALLBACK_REGISTRATION_TYPES,
            "invoice_types": [{"code": i.code, "name": i.name} for i in invoice_types],
            "hs_codes": [],  # Excluded for performance - fetch separately if needed
            "transaction_types": [{"code": t.code, "name": t.name.strip()} for t in transaction_types]
        }
    except Exception as e:
        logger.error(f"Error fetching all master data from database: {str(e)}")
        return {
            "provinces": [],
            "uom": [],
            "tax_rates": FALLBACK_TAX_RATES,
            "sale_types": FALLBACK_SALE_TYPES,
            "registration_types": FALLBACK_REGISTRATION_TYPES,
            "invoice_types": [],
            "hs_codes": [],
            "transaction_types": []
        }
