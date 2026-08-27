import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import UUID
import json

from src.config.settings import settings
from src.models.fbr_response import FBRResponseCreate
from src.utils.helpers import generate_correlation_id
from src.utils.logging import log_fbr_interaction
from src.utils.encryption import get_encryption_service


logger = logging.getLogger(__name__)


class FBRClient:
    """
    Client for interacting with FBR Digital Invoicing APIs (Production only).
    Mirrors the manual invoice system's FBRService approach.
    """

    SALE_TYPE_MAPPING = {
        "01": "Goods at standard rate (default)",
        "02": "Goods at reduced rate",
        "03": "Goods at zero rate",
        "04": "Exempt goods",
        "05": "Services",
        "06": "3rd Schedule Goods",
        "07": "Steel Melting and re-rolling",
        "08": "Ship breaking",
        "09": "Cotton Ginners",
        "10": "Telecommunication services",
        "11": "Toll Manufacturing",
        "12": "Petroleum Products",
        "13": "Electricity Supply to Retailers",
        "14": "Gas to CNG stations",
        "15": "Mobile Phones",
        "16": "Processing/Conversion of Goods",
        "17": "Goods (FED in ST Mode)",
        "18": "Services (FED in ST Mode)",
        "19": "Electric Vehicle",
        "20": "Cement/Concrete Block",
        "21": "Potassium Chlorate",
        "22": "CNG Sales",
        "23": "Goods as per SRO.297(I)/2023",
        "24": "Non-Adjustable Supplies"
    }

    SALE_TYPE_REVERSE_MAPPING = {v: k for k, v in SALE_TYPE_MAPPING.items()}

    PRODUCTION_VALIDATE_URL = f"{settings.fbr_production_base_url}/validateinvoicedata"
    PRODUCTION_POST_URL = f"{settings.fbr_production_base_url}/postinvoicedata"
    UOM_URL = "https://gw.fbr.gov.pk/pdi/v1/uom"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=False
        )
        self._uom_cache = {}
        self.timeout = 30.0

    async def _fetch_uom_mappings(self, access_token: str) -> Dict[str, str]:
        """Fetch UoM code to description mappings from FBR API (Production)."""
        cache_key = f"prod_{access_token[:10]}"
        if cache_key in self._uom_cache:
            return self._uom_cache[cache_key]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info("Fetching UoM mappings from FBR (PRODUCTION)")

        try:
            response = await self.client.get(self.UOM_URL, headers=headers)
            response.raise_for_status()
            uom_data = response.json()

            uom_mapping = {}
            for item in uom_data:
                uom_id = str(item.get("uoM_ID", ""))
                description = item.get("description", "")
                if uom_id and description:
                    uom_mapping[uom_id] = description

            self._uom_cache[cache_key] = uom_mapping
            logger.info(f"Cached {len(uom_mapping)} UoM mappings")
            return uom_mapping
        except Exception as e:
            logger.error(f"Failed to fetch UoM mappings: {str(e)}")
            return {}

    def _transform_items_to_fbr_format(self, items: list, uom_mapping: Dict[str, str]) -> list:
        """Transform items to FBR API format (matches manual system's _transform_invoice_to_fbr_format)."""
        transformed_items = []
        for item in items:
            sale_type_input = str(item.get("sale_type", "01")).strip()

            if sale_type_input in self.SALE_TYPE_REVERSE_MAPPING:
                sale_type_code = self.SALE_TYPE_REVERSE_MAPPING[sale_type_input]
            elif sale_type_input.isdigit() and sale_type_input in self.SALE_TYPE_MAPPING:
                sale_type_code = sale_type_input
            else:
                sale_type_code = "01"

            sale_type_description = self.SALE_TYPE_MAPPING[sale_type_code]

            rate = str(item.get("rate", "0"))
            if not rate.endswith("%"):
                rate = rate + "%"

            uom_code = str(item.get("uom", ""))
            uom_description = uom_mapping.get(uom_code, uom_code)

            hs_code = str(item.get("hs_code", ""))
            if "." in hs_code:
                parts = hs_code.split(".")
                hs_code = f"{parts[0]}.{parts[1].ljust(4, '0')}"

            transformed_item = {
                "hsCode": hs_code,
                "productDescription": item.get("product_description", ""),
                "rate": rate,
                "uoM": uom_description,
                "quantity": float(item.get("quantity", 0)),
                "totalValues": float(item.get("total_values", 0)),
                "valueSalesExcludingST": float(item.get("value_sales_excluding_st", 0)),
                "fixedNotifiedValueOrRetailPrice": float(item.get("fixed_notified_value_or_retail_price", 0)),
                "salesTaxApplicable": float(item.get("sales_tax_applicable", 0)),
                "salesTaxWithheldAtSource": float(item.get("sales_tax_withheld_at_source", 0)),
                "extraTax": float(item.get("extra_tax", 0)),
                "furtherTax": float(item.get("further_tax", 0)),
                "sroScheduleNo": item.get("sro_schedule_no", ""),
                "fedPayable": float(item.get("fed_payable", 0)),
                "discount": float(item.get("discount", 0)),
                "saleType": sale_type_description,
                "sroItemSerialNo": item.get("sro_item_serial_no", "")
            }
            transformed_items.append(transformed_item)

        return transformed_items

    async def validate_invoice_with_user_credentials(
        self,
        invoice_data: Dict[str, Any],
        fbr_token: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validate an invoice with FBR using user's production credentials.
        Mirrors manual system's validate_invoice method.
        """
        start_time = datetime.utcnow()

        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(fbr_token)
        except Exception as e:
            logger.error(f"Failed to decrypt FBR token: {e}")
            return False, {"error": "Invalid FBR credentials"}, None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "X-Correlation-ID": generate_correlation_id()
        }

        uom_mapping = await self._fetch_uom_mappings(decrypted_token)
        logger.info(f"UoM mapping contains {len(uom_mapping)} entries")

        # Validation-only override: FBR rejects invoice dates in the future.
        # Send today's date in the validation payload so future-dated invoices
        # pass validation; the stored invoice keeps its real date and is
        # posted with that original date when its scheduled time arrives.
        # NOTE: use the UTC date, not Pakistan local time — FBR's date check
        # is UTC-based, and the PKT date is a day ahead of UTC between
        # 19:00-00:00 UTC (FBR returns error 0043 for a "future" date then).
        validation_data = dict(invoice_data)
        validation_data["invoice_date"] = datetime.utcnow().strftime("%Y-%m-%d")

        transformed_items = self._transform_items_to_fbr_format(validation_data.get("items", []), uom_mapping)
        logger.info(f"Transformed {len(transformed_items)} invoice items for FBR validation")

        payload = {
            "invoiceType": validation_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": validation_data.get("invoice_date"),
            "sellerNTNCNIC": validation_data.get("seller_ntn_cnic", ""),
            "sellerBusinessName": validation_data.get("seller_business_name", ""),
            "sellerProvince": validation_data.get("seller_province", ""),
            "sellerAddress": validation_data.get("seller_address", ""),
            "buyerNTNCNIC": validation_data.get("buyer_ntn_cnic") or "",
            "buyerBusinessName": validation_data.get("buyer_business_name", ""),
            "buyerProvince": validation_data.get("buyer_province", ""),
            "buyerAddress": validation_data.get("buyer_address", ""),
            "buyerRegistrationType": validation_data.get("buyer_registration_type", ""),
            "items": transformed_items,
        }

        if validation_data.get("invoice_ref_no"):
            payload["invoiceRefNo"] = validation_data.get("invoice_ref_no")

        payload["timestamp"] = start_time.isoformat()

        try:
            response = await self.client.post(
                self.PRODUCTION_VALIDATE_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"FBR validation response: {json.dumps(result, default=str)[:500]}")

            validation_response = result.get("validationResponse", {})
            status = validation_response.get("status", "")
            status_code = validation_response.get("statusCode", "")
            is_valid = (status == "Valid" or status_code == "00")
            reference_number = result.get("reference_number")

            return is_valid, result, reference_number

        except httpx.HTTPStatusError as e:
            logger.error(f"FBR validation failed (HTTP {e.response.status_code}): {e.response.text}")
            try:
                return False, e.response.json(), None
            except Exception:
                return False, {"error": e.response.text or str(e)}, None

        except httpx.RequestError as e:
            logger.error(f"FBR validation request error: {str(e)}")
            return False, {"error": f"Request failed: {str(e)}"}, None

        except Exception as e:
            logger.error(f"Unexpected error during FBR validation: {str(e)}")
            return False, {"error": f"Unexpected error: {str(e)}"}, None

    async def post_invoice_with_user_credentials(
        self,
        invoice_data: Dict[str, Any],
        fbr_token: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Post an invoice to FBR using user's production credentials.
        Mirrors manual system's post_invoice method.
        """
        start_time = datetime.utcnow()

        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(fbr_token)
        except Exception as e:
            logger.error(f"Failed to decrypt FBR token: {e}")
            return False, {"error": "Invalid FBR credentials"}, None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "X-Correlation-ID": generate_correlation_id()
        }

        uom_mapping = await self._fetch_uom_mappings(decrypted_token)
        transformed_items = self._transform_items_to_fbr_format(invoice_data.get("items", []), uom_mapping)
        logger.info(f"Transformed {len(transformed_items)} invoice items for FBR posting")

        invoice_date = invoice_data.get("invoice_date", "")
        if hasattr(invoice_date, 'strftime'):
            invoice_date = invoice_date.strftime("%Y-%m-%d")

        payload = {
            "invoiceType": invoice_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": invoice_date,
            "sellerNTNCNIC": invoice_data.get("seller_ntn_cnic", ""),
            "sellerBusinessName": invoice_data.get("seller_business_name", ""),
            "sellerProvince": invoice_data.get("seller_province", ""),
            "sellerAddress": invoice_data.get("seller_address", ""),
            "buyerNTNCNIC": invoice_data.get("buyer_ntn_cnic") or "",
            "buyerBusinessName": invoice_data.get("buyer_business_name", ""),
            "buyerProvince": invoice_data.get("buyer_province", ""),
            "buyerAddress": invoice_data.get("buyer_address", ""),
            "buyerRegistrationType": invoice_data.get("buyer_registration_type", ""),
            "items": transformed_items,
        }

        if invoice_data.get("invoice_ref_no"):
            payload["invoiceRefNo"] = invoice_data.get("invoice_ref_no")

        payload["timestamp"] = start_time.isoformat()

        try:
            response = await self.client.post(
                self.PRODUCTION_POST_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"FBR posting response: {json.dumps(result, default=str)[:500]}")

            reference_number = result.get("reference_number")
            return True, result, reference_number

        except httpx.HTTPStatusError as e:
            logger.error(f"FBR posting failed (HTTP {e.response.status_code}): {e.response.text}")
            try:
                return False, e.response.json(), None
            except Exception:
                return False, {"error": e.response.text or str(e)}, None

        except httpx.RequestError as e:
            logger.error(f"FBR posting request error: {str(e)}")
            return False, {"error": f"Request failed: {str(e)}"}, None

        except Exception as e:
            logger.error(f"Unexpected error during FBR posting: {str(e)}")
            return False, {"error": f"Unexpected error: {str(e)}"}, None

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
