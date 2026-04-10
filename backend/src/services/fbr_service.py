"""
FBR (Federal Board of Revenue) API Integration Service.
Handles validation and posting of invoices to FBR Digital Invoicing System.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.models.invoice import Invoice, InvoiceStatus


logger = logging.getLogger(__name__)


class FBRService:
    """Service for interacting with FBR Digital Invoicing APIs."""

    # FBR API URLs (from FBR Technical Documentation v1.12)
    # Note: Both sandbox and production use gw.fbr.gov.pk
    # Sandbox endpoints have _sb suffix
    # Routing is based on the security token being used
    SANDBOX_VALIDATE_URL = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
    PRODUCTION_VALIDATE_URL = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata"

    SANDBOX_POST_URL = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
    PRODUCTION_POST_URL = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata"

    # Sale type code to full description mapping (as per FBR documentation)
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

    def __init__(self):
        self.timeout = 30.0  # 30 seconds timeout for FBR API calls
        self._uom_cache = {}  # Cache for UoM code to description mapping

    def _get_validate_url(self, environment: str) -> str:
        """Get the appropriate validation URL based on environment."""
        return self.SANDBOX_VALIDATE_URL if environment == "SANDBOX" else self.PRODUCTION_VALIDATE_URL

    def _get_post_url(self, environment: str) -> str:
        """Get the appropriate posting URL based on environment."""
        return self.SANDBOX_POST_URL if environment == "SANDBOX" else self.PRODUCTION_POST_URL

    async def _fetch_uom_mappings(self, access_token: str, environment: str = "SANDBOX") -> Dict[str, str]:
        """
        Fetch UoM code to description mappings from FBR API.

        Args:
            access_token: Bearer token for FBR API authentication
            environment: SANDBOX or PRODUCTION

        Returns:
            Dictionary mapping UoM codes to descriptions
        """
        cache_key = f"{environment}_{access_token[:10]}"  # Cache per environment and token

        if cache_key in self._uom_cache:
            return self._uom_cache[cache_key]

        uom_url = "https://gw.fbr.gov.pk/pdi/v1/uom"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Fetching UoM mappings from FBR ({environment})")
        logger.debug(f"UoM API URL: {uom_url}")

        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            try:
                response = await client.get(uom_url, headers=headers)
                response.raise_for_status()

                uom_data = response.json()

                # Build mapping: code -> description
                uom_mapping = {}
                for item in uom_data:
                    uom_id = str(item.get("uoM_ID", ""))
                    description = item.get("description", "")
                    if uom_id and description:
                        uom_mapping[uom_id] = description

                # Cache the mapping
                self._uom_cache[cache_key] = uom_mapping
                logger.info(f"Cached {len(uom_mapping)} UoM mappings")

                return uom_mapping

            except Exception as e:
                logger.error(f"Failed to fetch UoM mappings: {str(e)}")
                return {}  # Return empty dict on error

    async def _transform_invoice_to_fbr_format(self, invoice: Invoice, uom_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Transform internal invoice format to FBR API format.

        Args:
            invoice: Invoice object from database
            uom_mapping: Dictionary mapping UoM codes to descriptions

        Returns:
            Dictionary in FBR API format
        """
        # Transform items from snake_case to camelCase
        transformed_items = []
        for item in (invoice.items or []):
            # Get sale type code and convert to full description
            sale_type_code = item.get("sale_type", "01")
            sale_type_description = self.SALE_TYPE_MAPPING.get(sale_type_code, sale_type_code)

            # Get rate and ensure it has % suffix
            rate = str(item.get("rate", "0"))
            if not rate.endswith("%"):
                rate = rate + "%"

            # Get UoM code and convert to description
            uom_code = str(item.get("uom", ""))
            uom_description = uom_mapping.get(uom_code, uom_code)  # Fallback to code if not found

            transformed_item = {
                "hsCode": item.get("hs_code", ""),
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

        fbr_data = {
            "invoiceType": invoice.invoice_type,
            "invoiceDate": invoice.invoice_date.strftime("%Y-%m-%d") if isinstance(invoice.invoice_date, datetime) else invoice.invoice_date,
            "sellerNTNCNIC": invoice.seller_ntn_cnic,
            "sellerBusinessName": invoice.seller_business_name,
            "sellerProvince": invoice.seller_province,
            "sellerAddress": invoice.seller_address,
            "buyerNTNCNIC": invoice.buyer_ntn_cnic or "",
            "buyerBusinessName": invoice.buyer_business_name,
            "buyerProvince": invoice.buyer_province,
            "buyerAddress": invoice.buyer_address,
            "buyerRegistrationType": invoice.buyer_registration_type,
            "items": transformed_items
        }

        # Add optional fields
        if invoice.invoice_ref_no:
            fbr_data["invoiceRefNo"] = invoice.invoice_ref_no

        if invoice.scenario_id:
            fbr_data["scenarioId"] = invoice.scenario_id

        return fbr_data

    async def validate_invoice(self, invoice: Invoice, access_token: str) -> Dict[str, Any]:
        """
        Validate an invoice with FBR.

        Args:
            invoice: Invoice object to validate
            access_token: Bearer token for FBR API authentication

        Returns:
            FBR validation response

        Raises:
            httpx.HTTPError: If API call fails
        """
        url = self._get_validate_url(invoice.environment)

        # Fetch UoM mappings from FBR API
        uom_mapping = await self._fetch_uom_mappings(access_token, invoice.environment)
        logger.info(f"UoM mapping contains {len(uom_mapping)} entries")

        fbr_data = await self._transform_invoice_to_fbr_format(invoice, uom_mapping)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Validating invoice {invoice.id} with FBR ({invoice.environment})")
        logger.info(f"FBR validation payload: {fbr_data}")

        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            try:
                response = await client.post(url, json=fbr_data, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"FBR validation response for invoice {invoice.id}: {result}")

                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"FBR validation failed with status {e.response.status_code}: {e.response.text}")
                return {
                    "error": True,
                    "statusCode": e.response.status_code,
                    "message": f"FBR API error: {e.response.text}"
                }
            except httpx.RequestError as e:
                logger.error(f"FBR validation request failed: {str(e)}")
                return {
                    "error": True,
                    "message": f"Failed to connect to FBR: {str(e)}"
                }

    async def post_invoice(self, invoice: Invoice, access_token: str) -> Dict[str, Any]:
        """
        Post a validated invoice to FBR.

        Args:
            invoice: Invoice object to post (must be validated first)
            access_token: Bearer token for FBR API authentication

        Returns:
            FBR posting response including FBR invoice number

        Raises:
            httpx.HTTPError: If API call fails
        """
        url = self._get_post_url(invoice.environment)

        # Fetch UoM mappings from FBR API
        uom_mapping = await self._fetch_uom_mappings(access_token, invoice.environment)

        fbr_data = await self._transform_invoice_to_fbr_format(invoice, uom_mapping)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Posting invoice {invoice.id} to FBR ({invoice.environment})")
        logger.debug(f"FBR posting payload: {fbr_data}")

        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            try:
                response = await client.post(url, json=fbr_data, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"FBR posting response for invoice {invoice.id}: {result}")

                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"FBR posting failed with status {e.response.status_code}: {e.response.text}")
                return {
                    "error": True,
                    "statusCode": e.response.status_code,
                    "message": f"FBR API error: {e.response.text}"
                }
            except httpx.RequestError as e:
                logger.error(f"FBR posting request failed: {str(e)}")
                return {
                    "error": True,
                    "message": f"Failed to connect to FBR: {str(e)}"
                }

    def parse_validation_response(self, fbr_response: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[list]]:
        """
        Parse FBR validation response.

        Args:
            fbr_response: Response from FBR validation API

        Returns:
            Tuple of (is_valid, error_message, item_errors)
        """
        if fbr_response.get("error"):
            return False, fbr_response.get("message", "Unknown error"), None

        validation_response = fbr_response.get("validationResponse", {})
        status = validation_response.get("status", "")

        if status == "Valid":
            return True, None, None

        # Extract error details
        error_message = validation_response.get("error", "Validation failed")
        item_errors = validation_response.get("invoiceStatuses", [])

        return False, error_message, item_errors

    def parse_posting_response(self, fbr_response: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Parse FBR posting response.

        Args:
            fbr_response: Response from FBR posting API

        Returns:
            Tuple of (is_success, fbr_invoice_number, error_message)
        """
        if fbr_response.get("error"):
            return False, None, fbr_response.get("message", "Unknown error")

        posting_response = fbr_response.get("postingResponse", {})
        status = posting_response.get("status", "")

        if status == "Posted" or status == "Success":
            fbr_invoice_number = posting_response.get("invoiceNumber")
            return True, fbr_invoice_number, None

        error_message = posting_response.get("error", "Posting failed")
        return False, None, error_message

    async def verify_buyer_registration(self, ntn_cnic: str, access_token: str, environment: str = "SANDBOX") -> Dict[str, Any]:
        """
        Verify buyer registration status with FBR using Get_Reg_Type endpoint.

        Args:
            ntn_cnic: Buyer's NTN or CNIC number
            access_token: Bearer token for FBR API authentication
            environment: SANDBOX or PRODUCTION

        Returns:
            Dictionary with registration status and details
        """
        # FBR buyer verification endpoint (from TECHNICAL 1.pdf page 34)
        # URL: https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type
        verify_url = "https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Request format from FBR documentation
        payload = {
            "Registration_No": ntn_cnic
        }

        logger.info(f"Verifying buyer registration for NTN/CNIC: {ntn_cnic} ({environment})")

        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            try:
                response = await client.post(verify_url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Buyer verification response: {result}")

                # Parse FBR response format:
                # statuscode "00" = Registered
                # statuscode "01" = Unregistered
                status_code = result.get("statuscode", "01")
                registration_type = result.get("REGISTRATION_TYPE", "Unregistered")
                is_registered = status_code == "00"

                return {
                    "success": True,
                    "registrationType": registration_type,
                    "isRegistered": is_registered,
                    "businessName": result.get("businessName"),
                    "details": result
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"Buyer verification failed with status {e.response.status_code}: {e.response.text}")
                return {
                    "success": False,
                    "error": f"FBR API error: {e.response.text}",
                    "registrationType": "Unregistered"  # Default to unregistered on error
                }
            except httpx.RequestError as e:
                logger.error(f"Buyer verification request failed: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to connect to FBR: {str(e)}",
                    "registrationType": "Unregistered"  # Default to unregistered on error
                }


# Singleton instance
fbr_service = FBRService()
