"""
Master Data API endpoints for FBR-compliant reference data.
Provides dropdown options for invoice forms based on FBR specifications.
Fetches live data from FBR APIs when user has valid token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import logging

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# FBR API Base URLs (same for both sandbox and production, differentiated by token)
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
    {"code": "05", "name": "Services"}
]

FALLBACK_REGISTRATION_TYPES = [
    {"code": "REG", "name": "Registered"},
    {"code": "UNREG", "name": "Unregistered"}
]


async def get_user_fbr_token(db, user_id: str, environment: str = "SANDBOX") -> Optional[str]:
    """
    Get user's FBR access token based on environment.

    Args:
        db: Database session
        user_id: User ID
        environment: SANDBOX or PRODUCTION

    Returns:
        FBR access token or None
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return None

        if environment == "SANDBOX":
            return user.fbr_sandbox_token or user.fbr_access_token
        else:
            return user.fbr_production_token or user.fbr_access_token
    except Exception as e:
        logger.error(f"Error getting user FBR token: {str(e)}")
        return None


async def fetch_from_fbr(endpoint: str, token: Optional[str], environment: str = "SANDBOX") -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data from FBR API.

    Args:
        endpoint: FBR API endpoint path (e.g., "/pdi/v1/provinces")
        token: FBR access token
        environment: SANDBOX or PRODUCTION (both use same base URL, differentiated by token)

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
    Get list of FBR-compliant provinces from live FBR API.
    Returns empty list if user has no FBR token configured.

    Returns:
        List of provinces with code and name
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty provinces list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/provinces", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"stateProvinceCode": 7, "stateProvinceDesc": "PUNJAB"}
    # Our: {"code": "7", "name": "PUNJAB"}
    # Deduplicate by stateProvinceCode to ensure unique keys
    seen_ids = set()
    result = []
    for item in fbr_data:
        province_code = str(item.get("stateProvinceCode", ""))
        if province_code and province_code not in seen_ids:
            seen_ids.add(province_code)
            result.append({
                "code": province_code,
                "name": item.get("stateProvinceDesc", "")
            })
    return result


@router.get("/uom", response_model=List[Dict[str, Any]])
async def get_uom_codes(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of FBR-compliant Unit of Measure codes from live FBR API.
    Returns empty list if user has no FBR token configured.

    Returns:
        List of UOM codes with code and name
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty UOM list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/uom", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"uoM_ID": 77, "description": "Square Metre"}
    # Our: {"code": "77", "name": "Square Metre"}
    # Deduplicate by uoM_ID to ensure unique keys
    seen_ids = set()
    result = []
    duplicates_found = []

    for item in fbr_data:
        uom_id = str(item.get("uoM_ID", ""))
        description = item.get("description", "")

        if uom_id and uom_id not in seen_ids:
            seen_ids.add(uom_id)
            result.append({
                "code": uom_id,
                "name": description
            })
        elif uom_id in seen_ids:
            duplicates_found.append(f"ID:{uom_id} Name:{description}")

    if duplicates_found:
        logger.warning(f"Found {len(duplicates_found)} duplicate UOM IDs: {duplicates_found[:5]}")

    logger.info(f"Returning {len(result)} unique UOM codes")
    return result


@router.get("/tax-rates", response_model=List[Dict[str, str]])
async def get_tax_rates(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get list of FBR-compliant tax rates.
    Note: FBR doesn't have a direct API for tax rates, using fallback values.

    Returns:
        List of tax rates with rate and name
    """
    # No direct FBR API for tax rates, return fallback
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
    # No direct FBR API for sale types, return fallback
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
    # No direct FBR API for registration types, return fallback
    return FALLBACK_REGISTRATION_TYPES


@router.get("/invoice-types", response_model=List[Dict[str, Any]])
async def get_invoice_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of FBR-compliant invoice types from live FBR API.
    Returns empty list if user has no FBR token configured.

    Returns:
        List of invoice types with code and name
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty invoice types list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/doctypecode", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"docTypeId": 4, "docDescription": "Sale Invoice"}
    # Our: {"code": "4", "name": "Sale Invoice"}
    # Deduplicate by docTypeId to ensure unique keys
    seen_ids = set()
    result = []
    for item in fbr_data:
        doc_type_id = str(item.get("docTypeId", ""))
        if doc_type_id and doc_type_id not in seen_ids:
            seen_ids.add(doc_type_id)
            result.append({
                "code": doc_type_id,
                "name": item.get("docDescription", "")
            })
    return result


@router.get("/hs-codes", response_model=List[Dict[str, str]])
async def get_hs_codes(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of HS codes from live FBR API.
    Returns empty list if user has no FBR token configured.

    FBR API: /pdi/v1/itemdesccode
    Returns all HS codes with descriptions.

    Returns:
        List of HS codes with code and description
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty HS codes list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/itemdesccode", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"hS_CODE": "8432.1010", "description": "NUCLEAR REACTOR..."}
    # Our: {"code": "8432.1010", "description": "NUCLEAR REACTOR..."}
    result = []
    for item in fbr_data:
        hs_code = item.get("hS_CODE", "")
        description = item.get("description", "")

        if hs_code:
            result.append({
                "code": hs_code,
                "description": description
            })

    logger.info(f"Returning {len(result)} HS codes")
    return result


@router.get("/transaction-types", response_model=List[Dict[str, str]])
async def get_transaction_types(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of transaction types from live FBR API.
    Returns empty list if user has no FBR token configured.

    FBR API: /pdi/v1/transtypecode
    Returns all transaction types with IDs and descriptions.

    Returns:
        List of transaction types with code and name
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty transaction types list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/transtypecode", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"transactioN_TYPE_ID": 82, "transactioN_DESC": "DTRE goods"}
    # Our: {"code": "82", "name": "DTRE goods"}
    seen_ids = set()
    result = []
    for item in fbr_data:
        trans_type_id = str(item.get("transactioN_TYPE_ID", ""))
        if trans_type_id and trans_type_id not in seen_ids:
            seen_ids.add(trans_type_id)
            result.append({
                "code": trans_type_id,
                "name": item.get("transactioN_DESC", "")
            })

    logger.info(f"Returning {len(result)} transaction types")
    return result


@router.get("/sro-items", response_model=List[Dict[str, str]])
async def get_sro_items(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    environment: str = "SANDBOX"
):
    """
    Get list of SRO items from live FBR API.
    Returns empty list if user has no FBR token configured.

    FBR API: /pdi/v1/sroitemcode
    Returns all SRO items with IDs and descriptions.

    Returns:
        List of SRO items with code and name
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty SRO items list")
        return []

    fbr_data = await fetch_from_fbr("/pdi/v1/sroitemcode", token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"srO_ITEM_ID": 724, "srO_ITEM_DESC": "9"}
    # Our: {"code": "724", "name": "9"}
    seen_ids = set()
    result = []
    for item in fbr_data:
        sro_item_id = str(item.get("srO_ITEM_ID", ""))
        if sro_item_id and sro_item_id not in seen_ids:
            seen_ids.add(sro_item_id)
            result.append({
                "code": sro_item_id,
                "name": item.get("srO_ITEM_DESC", "")
            })

    logger.info(f"Returning {len(result)} SRO items")
    return result


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

    FBR API: /pdi/v1/SroSchedule

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

    # Build query string
    endpoint = f"/pdi/v1/SroSchedule?rate_id={rate_id}&date={date}&origination_supplier_csv={origination_supplier_csv}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"srO_ID": 7, "srO_DESC": "Zero Rated Gas"}
    # Our: {"id": "7", "description": "Zero Rated Gas"}
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
    Get applicable tax rates based on date, transaction type, and supplier type.

    FBR API: /pdi/v2/SaleTypeToRate

    Args:
        date: Invoice date (format: DD-MMM-YYYY, e.g., "24-Feb-2024")
        trans_type_id: Transaction type ID
        origination_supplier: Supplier type (1 or 0)

    Returns:
        List of applicable tax rates
    """
    token = await get_user_fbr_token(db, user_id, environment)

    if not token:
        logger.info("No FBR token found, returning empty sale type to rate list")
        return []

    # Build query string - Note: This is v2 API
    endpoint = f"/pdi/v2/SaleTypeToRate?date={date}&transTypeId={trans_type_id}&originationSupplier={origination_supplier}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    logger.info(f"Returning {len(fbr_data)} rates for trans_type_id={trans_type_id}")
    return fbr_data


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

    FBR API: /pdi/v2/HS_UOM

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

    # Build query string - Note: This is v2 API
    endpoint = f"/pdi/v2/HS_UOM?hs_code={hs_code}&annexure_id={annexure_id}"
    fbr_data = await fetch_from_fbr(endpoint, token, environment)

    if not fbr_data:
        return []

    # Transform FBR response format to our format
    # FBR: {"uoM_ID": 77, "description": "Square Meter"}
    # Our: {"code": "77", "name": "Square Meter"}
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

    FBR API: /pdi/v2/SROItem

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

    # Build query string - Note: This is v2 API
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
    Fetches live data from FBR APIs when user has valid token.
    Returns empty arrays for fields requiring FBR token if not configured.

    Returns:
        Dictionary containing all master data
    """
    token = await get_user_fbr_token(db, user_id, environment)

    # Fetch data from FBR APIs (only if token exists)
    provinces = []
    uom = []
    invoice_types = []
    hs_codes = []
    transaction_types = []
    sro_items = []

    if token:
        # Fetch provinces
        fbr_provinces = await fetch_from_fbr("/pdi/v1/provinces", token, environment)
        if fbr_provinces:
            seen_ids = set()
            for item in fbr_provinces:
                province_code = str(item.get("stateProvinceCode", ""))
                if province_code and province_code not in seen_ids:
                    seen_ids.add(province_code)
                    provinces.append({
                        "code": province_code,
                        "name": item.get("stateProvinceDesc", "")
                    })

        # Fetch UOM codes
        fbr_uom = await fetch_from_fbr("/pdi/v1/uom", token, environment)
        if fbr_uom:
            seen_ids = set()
            for item in fbr_uom:
                uom_id = str(item.get("uoM_ID", ""))
                if uom_id and uom_id not in seen_ids:
                    seen_ids.add(uom_id)
                    uom.append({
                        "code": uom_id,
                        "name": item.get("description", "")
                    })

        # Fetch invoice types
        fbr_invoice_types = await fetch_from_fbr("/pdi/v1/doctypecode", token, environment)
        if fbr_invoice_types:
            seen_ids = set()
            for item in fbr_invoice_types:
                doc_type_id = str(item.get("docTypeId", ""))
                if doc_type_id and doc_type_id not in seen_ids:
                    seen_ids.add(doc_type_id)
                    invoice_types.append({
                        "code": doc_type_id,
                        "name": item.get("docDescription", "")
                    })

        # Fetch HS codes
        logger.info("Fetching HS codes from FBR API...")
        fbr_hs_codes = await fetch_from_fbr("/pdi/v1/itemdesccode", token, environment)
        if fbr_hs_codes:
            logger.info(f"Received {len(fbr_hs_codes)} HS codes from FBR")
            for item in fbr_hs_codes:
                hs_code = item.get("hS_CODE", "")
                if hs_code:
                    hs_codes.append({
                        "code": hs_code,
                        "description": item.get("description", "")
                    })
            logger.info(f"Returning {len(hs_codes)} HS codes to frontend")
        else:
            logger.warning("No HS codes received from FBR API")

        # Fetch transaction types
        logger.info("Fetching transaction types from FBR API...")
        fbr_transaction_types = await fetch_from_fbr("/pdi/v1/transtypecode", token, environment)
        if fbr_transaction_types:
            logger.info(f"Received {len(fbr_transaction_types)} transaction types from FBR")
            seen_ids = set()
            for item in fbr_transaction_types:
                trans_type_id = str(item.get("transactioN_TYPE_ID", ""))
                if trans_type_id and trans_type_id not in seen_ids:
                    seen_ids.add(trans_type_id)
                    transaction_types.append({
                        "code": trans_type_id,
                        "name": item.get("transactioN_DESC", "")
                    })
            logger.info(f"Returning {len(transaction_types)} transaction types to frontend")
        else:
            logger.warning("No transaction types received from FBR API")

        # Fetch SRO items
        logger.info("Fetching SRO items from FBR API...")
        fbr_sro_items = await fetch_from_fbr("/pdi/v1/sroitemcode", token, environment)
        if fbr_sro_items:
            logger.info(f"Received {len(fbr_sro_items)} SRO items from FBR")
            seen_ids = set()
            for item in fbr_sro_items:
                sro_item_id = str(item.get("srO_ITEM_ID", ""))
                if sro_item_id and sro_item_id not in seen_ids:
                    seen_ids.add(sro_item_id)
                    sro_items.append({
                        "code": sro_item_id,
                        "name": item.get("srO_ITEM_DESC", "")
                    })
            logger.info(f"Returning {len(sro_items)} SRO items to frontend")
        else:
            logger.warning("No SRO items received from FBR API")
    else:
        logger.info("No FBR token found, returning empty arrays for FBR-dependent fields")

    return {
        "provinces": provinces,
        "uom": uom,
        "tax_rates": FALLBACK_TAX_RATES,
        "sale_types": FALLBACK_SALE_TYPES,
        "registration_types": FALLBACK_REGISTRATION_TYPES,
        "invoice_types": invoice_types,
        "hs_codes": hs_codes,
        "transaction_types": transaction_types,
        "sro_items": sro_items
    }
 
