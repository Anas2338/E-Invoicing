from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from uuid import UUID
import httpx
import logging
from functools import lru_cache

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache for HS code descriptions (valid for 24 hours)
hs_code_cache: Dict[str, str] = {}


async def fetch_all_hs_codes(access_token: str) -> Dict[str, str]:
    """
    Fetch all HS codes and descriptions from FBR API.
    Returns a dictionary mapping HS codes to descriptions.

    Args:
        access_token: Bearer token for FBR API authentication (required by FBR)

    Note: Per TECHNICAL 1.pdf Section 5.3, this endpoint requires authentication.
    """
    url = "https://gw.fbr.gov.pk/pdi/v1/itemdesccode"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Build a dictionary of HS code -> description
            hs_dict = {}
            for item in data:
                hs_code = item.get("hS_CODE", "").strip()
                description = item.get("description", "").strip()
                if hs_code and description:
                    hs_dict[hs_code] = description

            logger.info(f"Fetched {len(hs_dict)} HS codes from FBR API")
            return hs_dict

    except httpx.HTTPStatusError as e:
        logger.error(f"FBR API error fetching HS codes: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch HS codes from FBR API: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error fetching HS codes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to FBR API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching HS codes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/hs-code/{hs_code}")
async def get_hs_code_description(
    hs_code: str,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
) -> Dict[str, Any]:
    """
    Get the description for a specific HS code.

    Args:
        hs_code: The HS code to lookup (e.g., "0102.2301")

    Returns:
        Dictionary with hs_code and description

    Note: Per TECHNICAL 1.pdf Section 5.3, the FBR itemdesccode endpoint requires
    authentication with a Bearer token.
    """
    global hs_code_cache

    # Get the authenticated user
    user_uuid = UUID(user_id)
    user = db.query(User).filter(User.id == user_uuid).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get the appropriate FBR token (prefer sandbox for reference data)
    access_token = user.fbr_sandbox_token or user.fbr_production_token or user.fbr_access_token

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FBR access token not configured. Please configure your FBR token in settings."
        )

    # Normalize the HS code (remove spaces, convert to uppercase)
    hs_code_normalized = hs_code.strip().upper()

    # If cache is empty, fetch all HS codes
    if not hs_code_cache:
        logger.info("HS code cache is empty, fetching from FBR API...")
        hs_code_cache = await fetch_all_hs_codes(access_token)

    # Look up the HS code in the cache
    description = hs_code_cache.get(hs_code_normalized)

    if description:
        return {
            "hs_code": hs_code_normalized,
            "description": description,
            "found": True
        }
    else:
        # Try to find a partial match (in case the format is slightly different)
        # Remove dots and try again
        hs_code_no_dots = hs_code_normalized.replace(".", "")

        for cached_code, cached_desc in hs_code_cache.items():
            if cached_code.replace(".", "") == hs_code_no_dots:
                return {
                    "hs_code": cached_code,
                    "description": cached_desc,
                    "found": True
                }

        # Not found
        return {
            "hs_code": hs_code_normalized,
            "description": None,
            "found": False,
            "message": "HS code not found in FBR database"
        }


@router.post("/refresh-hs-codes")
async def refresh_hs_code_cache(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
) -> Dict[str, Any]:
    """
    Manually refresh the HS code cache from FBR API.

    Note: Per TECHNICAL 1.pdf Section 5.3, the FBR itemdesccode endpoint requires
    authentication with a Bearer token.
    """
    global hs_code_cache

    # Get the authenticated user
    user_uuid = UUID(user_id)
    user = db.query(User).filter(User.id == user_uuid).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get the appropriate FBR token
    access_token = user.fbr_sandbox_token or user.fbr_production_token or user.fbr_access_token

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FBR access token not configured. Please configure your FBR token in settings."
        )

    logger.info("Manually refreshing HS code cache...")
    hs_code_cache = await fetch_all_hs_codes(access_token)

    return {
        "success": True,
        "message": f"HS code cache refreshed with {len(hs_code_cache)} entries"
    }
