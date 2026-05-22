import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import UUID
import json

from src.config.settings import settings
from src.models.fbr_response import FBRResponseCreate
from src.schemas.fbr import FBREnvironment
from src.utils.helpers import calculate_hash, generate_correlation_id
from src.utils.logging import log_fbr_interaction
from src.utils.encryption import get_encryption_service


logger = logging.getLogger(__name__)


class FBRClient:
    """
    Client for interacting with FBR APIs for validation and posting.
    """

    # Sale type code to description mapping (from FBR technical specification)
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

    # Reverse mapping: description -> code (for Excel parsing)
    SALE_TYPE_REVERSE_MAPPING = {v: k for k, v in SALE_TYPE_MAPPING.items()}

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout
            follow_redirects=True,
            verify=True  # Explicitly verify SSL/TLS certificates to prevent MITM attacks
        )
        self._uom_cache = {}  # Cache for UoM code to description mapping
        self.timeout = 30.0

    async def _fetch_uom_mappings(self, fbr_token: str, environment: FBREnvironment) -> Dict[str, str]:
        """
        Fetch UoM code to description mappings from FBR API.
        Matches the manual system's approach (fbr_service.py).

        Args:
            fbr_token: User's FBR access token
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            Dictionary mapping UoM codes to descriptions
        """
        cache_key = f"{environment.value}_{fbr_token[:10]}"  # Cache per environment and token

        if cache_key in self._uom_cache:
            return self._uom_cache[cache_key]

        uom_url = "https://gw.fbr.gov.pk/pdi/v1/uom"
        headers = {
            "Authorization": f"Bearer {fbr_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Fetching UoM mappings from FBR ({environment.value})")

        try:
            response = await self.client.get(uom_url, headers=headers)
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

    def _transform_items_to_fbr_format(self, items: list, uom_mapping: Dict[str, str]) -> list:
        """
        Transform items to FBR API format (camelCase and sale_type code to description).
        Matches the transformation in fbr_service.py for manual invoicing.

        Args:
            items: List of item dictionaries in snake_case format
            uom_mapping: Dictionary mapping UoM codes to descriptions from FBR API

        Returns:
            List of transformed items in camelCase format with sale_type descriptions
        """
        transformed_items = []
        for item in items:
            # Pass sale_type through as-is; only resolve pure digit codes for backward compatibility
            sale_type_input = str(item.get("sale_type", "01")).strip()
            if sale_type_input.isdigit() and sale_type_input in self.SALE_TYPE_MAPPING:
                sale_type_description = self.SALE_TYPE_MAPPING[sale_type_input]
            else:
                sale_type_description = sale_type_input  # Pass through stored name unchanged

            # Add % suffix only for non-zero numeric rates (0, "Exempt" stay as-is)
            rate = str(item.get("rate", "0"))
            if not rate.endswith("%"):
                try:
                    if float(rate) != 0:
                        rate = rate + "%"
                except ValueError:
                    pass  # Non-numeric rate like "Exempt" — keep as-is

            # Get UoM and convert to FBR's exact description using mapping
            # This matches the manual system's approach (fbr_service.py line 144-145)
            uom_input = str(item.get("uom", ""))
            uom_description = uom_mapping.get(uom_input, uom_input)  # Fallback to input if not found

            # Format HS code to 8 digits (XXXX.XXXX format)
            # FBR requires 4 digits before dot and 4 digits after dot
            hs_code = str(item.get("hs_code", ""))
            if "." in hs_code:
                parts = hs_code.split(".")
                # Pad the part after dot to 4 digits
                hs_code = f"{parts[0]}.{parts[1].ljust(4, '0')}"

            # Transform to camelCase format matching manual system
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
            # Omit extraTax when 0 — FBR rejects 0 as "extra tax provided" for some sale types
            if transformed_item["extraTax"] == 0:
                del transformed_item["extraTax"]
            transformed_items.append(transformed_item)

        return transformed_items

    async def validate_invoice(self, invoice_data: Dict[str, Any],
                              environment: FBREnvironment) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validate an invoice with the FBR system.

        Args:
            invoice_data: Invoice data to validate (matches FBR technical specification)
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            Tuple of (is_valid, response_data, reference_number)
        """
        start_time = datetime.utcnow()

        # Select the appropriate base URL based on environment
        # Use FBR's actual API endpoints based on the technical specification
        if environment == FBREnvironment.SANDBOX:
            validation_endpoint = f"{settings.fbr_sandbox_base_url}/validateinvoicedata_sb"
        else:
            validation_endpoint = f"{settings.fbr_production_base_url}/validateinvoicedata"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.fbr_api_key}",
            "X-Correlation-ID": generate_correlation_id(),
            "X-Client-ID": settings.fbr_client_id
        }

        # Prepare payload according to FBR technical specification
        payload = {
            "invoiceType": invoice_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": invoice_data.get("invoice_date"),
            "sellerNTNCNIC": invoice_data.get("seller_ntn_cnic"),
            "sellerBusinessName": invoice_data.get("seller_business_name"),
            "sellerProvince": invoice_data.get("seller_province"),
            "sellerAddress": invoice_data.get("seller_address"),
            "buyerNTNCNIC": invoice_data.get("buyer_ntn_cnic"),
            "buyerBusinessName": invoice_data.get("buyer_business_name"),
            "buyerProvince": invoice_data.get("buyer_province"),
            "buyerAddress": invoice_data.get("buyer_address"),
            "buyerRegistrationType": invoice_data.get("buyer_registration_type"),
            "invoiceRefNo": invoice_data.get("invoice_ref_no", ""),
            "items": invoice_data.get("items", []),
        }

        # Add scenario ID for sandbox environment
        if environment == FBREnvironment.SANDBOX:
            payload["scenarioId"] = invoice_data.get("scenario_id", "SN001")

        payload["timestamp"] = start_time.isoformat()

        try:
            # Make the API call to FBR
            response = await self.client.post(
                validation_endpoint,
                json=payload,
                headers=headers
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the interaction with raw response for debugging
            response_text = response.text if response.content else ""

            try:
                response_json = response.json() if response.content else {}
            except Exception as json_error:
                logger.error(f"Failed to parse FBR response as JSON. Status: {response.status_code}, Body: {response_text[:500]}")
                log_fbr_interaction(
                    endpoint=validation_endpoint,
                    method="POST",
                    status_code=response.status_code,
                    duration=duration,
                    request_payload=payload,
                    response_payload={"error": f"Invalid JSON response: {str(json_error)}", "raw_response": response_text[:500]},
                    environment=environment.value,
                    correlation_id=headers["X-Correlation-ID"]
                )
                return False, {"error": f"FBR API returned invalid response: {response_text[:200]}"}, None

            # Log the interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=response.status_code,
                duration=duration,
                request_payload=payload,
                response_payload=response_json,
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 200:
                # Check if validation was successful
                # FBR returns: {"validationResponse": {"status": "Valid", "statusCode": "00"}}
                validation_response = response_json.get("validationResponse", {})
                status = validation_response.get("status", "")
                status_code = validation_response.get("statusCode", "")

                # Success if status is "Valid" or statusCode is "00"
                is_valid = (status == "Valid" or status_code == "00")
                reference_number = response_json.get("reference_number")

                return is_valid, response_json, reference_number
            elif response.status_code in [400, 422]:
                # Validation failed with specific errors
                return False, response_json, None
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during validation: {response.status_code}")
                return False, response_json or {"error": "Unexpected response from FBR"}, None

        except httpx.RequestError as e:
            logger.error(f"Request error during FBR validation: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=0,  # No response status
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Request failed: {str(e)}"}, None
        except Exception as e:
            logger.error(f"Unexpected error during FBR validation: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=0,  # No response status
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Unexpected error: {str(e)}"}, None

    async def validate_invoice_with_user_credentials(
        self,
        invoice_data: Dict[str, Any],
        environment: FBREnvironment,
        fbr_token: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate an invoice with the FBR system using user's credentials.

        Args:
            invoice_data: Invoice data to validate (matches FBR technical specification)
            environment: Target environment (SANDBOX or PRODUCTION)
            fbr_token: User's ENCRYPTED FBR access token

        Returns:
            Tuple of (is_valid, response_data, reference_number, fbr_request_payload)
        """
        start_time = datetime.utcnow()

        # SECURITY: Decrypt the token before using it
        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(fbr_token)
        except Exception as e:
            logger.error(f"Failed to decrypt FBR token: {e}")
            return False, {"error": "Invalid FBR credentials"}, None, None

        # Use the same URLs as the manual system (fbr_service.py)
        if environment == FBREnvironment.SANDBOX:
            validation_endpoint = f"{settings.fbr_sandbox_base_url}/validateinvoicedata_sb"
        else:
            validation_endpoint = f"{settings.fbr_production_base_url}/validateinvoicedata"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "X-Correlation-ID": generate_correlation_id()
        }

        # Fetch UoM mappings from FBR API (matches manual system approach)
        uom_mapping = await self._fetch_uom_mappings(decrypted_token, environment)
        logger.info(f"UoM mapping contains {len(uom_mapping)} entries")

        # Transform items to FBR format (camelCase and sale_type code to description)
        transformed_items = self._transform_items_to_fbr_format(invoice_data.get("items", []), uom_mapping)

        # Log only metadata, not sensitive invoice data
        logger.info(f"Transformed {len(transformed_items)} invoice items for FBR validation")

        # Prepare payload according to FBR technical specification
        payload = {
            "invoiceType": invoice_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": invoice_data.get("invoice_date"),
            "sellerNTNCNIC": invoice_data.get("seller_ntn_cnic"),
            "sellerBusinessName": invoice_data.get("seller_business_name"),
            "sellerProvince": invoice_data.get("seller_province"),
            "sellerAddress": invoice_data.get("seller_address"),
            "buyerNTNCNIC": invoice_data.get("buyer_ntn_cnic"),
            "buyerBusinessName": invoice_data.get("buyer_business_name"),
            "buyerProvince": invoice_data.get("buyer_province"),
            "buyerAddress": invoice_data.get("buyer_address"),
            "buyerRegistrationType": invoice_data.get("buyer_registration_type"),
            "invoiceRefNo": invoice_data.get("invoice_ref_no", ""),
            "items": transformed_items,
        }

        # Add scenario ID for sandbox environment
        if environment == FBREnvironment.SANDBOX:
            payload["scenarioId"] = invoice_data.get("scenario_id", "SN001")

        payload["timestamp"] = start_time.isoformat()

        try:
            # Make the API call to FBR
            response = await self.client.post(
                validation_endpoint,
                json=payload,
                headers=headers
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the interaction with raw response for debugging
            response_text = response.text if response.content else ""

            try:
                response_json = response.json() if response.content else {}
            except Exception as json_error:
                logger.error(f"Failed to parse FBR response as JSON. Status: {response.status_code}, Body: {response_text[:500]}")
                log_fbr_interaction(
                    endpoint=validation_endpoint,
                    method="POST",
                    status_code=response.status_code,
                    duration=duration,
                    request_payload=payload,
                    response_payload={"error": f"Invalid JSON response: {str(json_error)}", "raw_response": response_text[:500]},
                    environment=environment.value,
                    correlation_id=headers["X-Correlation-ID"]
                )
                return False, {"error": f"FBR API returned invalid response: {response_text[:200]}"}, None, payload

            # Log the interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=response.status_code,
                duration=duration,
                request_payload=payload,
                response_payload=response_json,
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 200:
                # Check if validation was successful
                # FBR returns: {"validationResponse": {"status": "Valid", "statusCode": "00"}}
                validation_response = response_json.get("validationResponse", {})
                status = validation_response.get("status", "")
                status_code = validation_response.get("statusCode", "")

                # Success if status is "Valid" or statusCode is "00"
                is_valid = (status == "Valid" or status_code == "00")
                reference_number = response_json.get("reference_number")

                return is_valid, response_json, reference_number, payload
            elif response.status_code in [400, 422]:
                # Validation failed with specific errors
                return False, response_json, None, payload
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during validation: {response.status_code}")
                return False, response_json or {"error": "Unexpected response from FBR"}, None, payload

        except httpx.RequestError as e:
            logger.error(f"Request error during FBR validation: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=0,
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Request failed: {str(e)}"}, None, payload
        except Exception as e:
            logger.error(f"Unexpected error during FBR validation: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=0,
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Unexpected error: {str(e)}"}, None, payload

    async def post_invoice_with_user_credentials(
        self,
        invoice_data: Dict[str, Any],
        environment: FBREnvironment,
        fbr_token: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Post an invoice to the FBR system using user's credentials.

        Args:
            invoice_data: Invoice data to post (matches FBR technical specification)
            environment: Target environment (SANDBOX or PRODUCTION)
            fbr_token: User's ENCRYPTED FBR access token

        Returns:
            Tuple of (is_posted, response_data, reference_number)
        """
        start_time = datetime.utcnow()

        # SECURITY: Decrypt the token before using it
        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(fbr_token)
        except Exception as e:
            logger.error(f"Failed to decrypt FBR token: {e}")
            return False, {"error": "Invalid FBR credentials"}, None

        # Use the same URLs as the manual system (fbr_service.py)
        if environment == FBREnvironment.SANDBOX:
            posting_endpoint = f"{settings.fbr_sandbox_base_url}/postinvoicedata_sb"
        else:
            posting_endpoint = f"{settings.fbr_production_base_url}/postinvoicedata"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "X-Correlation-ID": generate_correlation_id()
        }

        # Fetch UoM mappings from FBR API (matches manual system approach)
        uom_mapping = await self._fetch_uom_mappings(decrypted_token, environment)

        # Transform items to FBR format (camelCase and sale_type code to description)
        transformed_items = self._transform_items_to_fbr_format(invoice_data.get("items", []), uom_mapping)

        # Log only metadata, not sensitive invoice data
        logger.info(f"Transformed {len(transformed_items)} invoice items for FBR validation")

        # Prepare payload according to FBR technical specification
        payload = {
            "invoiceType": invoice_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": invoice_data.get("invoice_date"),
            "sellerNTNCNIC": invoice_data.get("seller_ntn_cnic"),
            "sellerBusinessName": invoice_data.get("seller_business_name"),
            "sellerProvince": invoice_data.get("seller_province"),
            "sellerAddress": invoice_data.get("seller_address"),
            "buyerNTNCNIC": invoice_data.get("buyer_ntn_cnic"),
            "buyerBusinessName": invoice_data.get("buyer_business_name"),
            "buyerProvince": invoice_data.get("buyer_province"),
            "buyerAddress": invoice_data.get("buyer_address"),
            "buyerRegistrationType": invoice_data.get("buyer_registration_type"),
            "invoiceRefNo": invoice_data.get("invoice_ref_no", ""),
            "items": transformed_items,
        }

        # Add scenario ID for sandbox environment
        if environment == FBREnvironment.SANDBOX:
            payload["scenarioId"] = invoice_data.get("scenario_id", "SN001")

        payload["timestamp"] = start_time.isoformat()

        try:
            # Make the API call to FBR
            response = await self.client.post(
                posting_endpoint,
                json=payload,
                headers=headers
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=response.status_code,
                duration=duration,
                request_payload=payload,
                response_payload=response.json() if response.content else {},
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 201:
                response_data = response.json()

                # Invoice was successfully posted
                reference_number = response_data.get("reference_number")

                return True, response_data, reference_number
            elif response.status_code in [400, 422]:
                # Posting failed with specific errors
                response_data = response.json() if response.content else {}

                return False, response_data, None
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during posting: {response.status_code}")
                response_data = response.json() if response.content else {"error": "Unexpected response from FBR"}

                return False, response_data, None

        except httpx.RequestError as e:
            logger.error(f"Request error during FBR posting: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=0,
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Request failed: {str(e)}"}, None
        except Exception as e:
            logger.error(f"Unexpected error during FBR posting: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=0,
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Unexpected error: {str(e)}"}, None

    async def post_invoice(self, invoice_data: Dict[str, Any],
                          environment: FBREnvironment) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Post an invoice to the FBR system.

        Args:
            invoice_data: Invoice data to post (matches FBR technical specification)
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            Tuple of (is_posted, response_data, reference_number)
        """
        start_time = datetime.utcnow()

        # Select the appropriate base URL based on environment
        # Use FBR's actual API endpoints based on the technical specification
        if environment == FBREnvironment.SANDBOX:
            posting_endpoint = f"{settings.fbr_sandbox_base_url}/postinvoicedata_sb"
        else:
            posting_endpoint = f"{settings.fbr_production_base_url}/postinvoicedata"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.fbr_api_key}",
            "X-Correlation-ID": generate_correlation_id(),
            "X-Client-ID": settings.fbr_client_id
        }

        # Prepare payload according to FBR technical specification
        payload = {
            "invoiceType": invoice_data.get("invoice_type", "Sale Invoice"),
            "invoiceDate": invoice_data.get("invoice_date"),
            "sellerNTNCNIC": invoice_data.get("seller_ntn_cnic"),
            "sellerBusinessName": invoice_data.get("seller_business_name"),
            "sellerProvince": invoice_data.get("seller_province"),
            "sellerAddress": invoice_data.get("seller_address"),
            "buyerNTNCNIC": invoice_data.get("buyer_ntn_cnic"),
            "buyerBusinessName": invoice_data.get("buyer_business_name"),
            "buyerProvince": invoice_data.get("buyer_province"),
            "buyerAddress": invoice_data.get("buyer_address"),
            "buyerRegistrationType": invoice_data.get("buyer_registration_type"),
            "invoiceRefNo": invoice_data.get("invoice_ref_no", ""),
            "items": invoice_data.get("items", []),
        }

        # Add scenario ID for sandbox environment
        if environment == FBREnvironment.SANDBOX:
            payload["scenarioId"] = invoice_data.get("scenario_id", "SN001")

        payload["timestamp"] = start_time.isoformat()

        try:
            # Make the API call to FBR
            response = await self.client.post(
                posting_endpoint,
                json=payload,
                headers=headers
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=response.status_code,
                duration=duration,
                request_payload=payload,
                response_payload=response.json() if response.content else {},
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 201:
                response_data = response.json()

                # Invoice was successfully posted
                reference_number = response_data.get("reference_number")

                return True, response_data, reference_number
            elif response.status_code in [400, 422]:
                # Posting failed with specific errors
                response_data = response.json() if response.content else {}

                return False, response_data, None
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during posting: {response.status_code}")
                response_data = response.json() if response.content else {"error": "Unexpected response from FBR"}

                return False, response_data, None

        except httpx.RequestError as e:
            logger.error(f"Request error during FBR posting: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=0,  # No response status
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Request failed: {str(e)}"}, None
        except Exception as e:
            logger.error(f"Unexpected error during FBR posting: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=posting_endpoint,
                method="POST",
                status_code=0,  # No response status
                duration=duration,
                request_payload=payload,
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Unexpected error: {str(e)}"}, None

    async def get_invoice_status(self, reference_number: str,
                                environment: FBREnvironment) -> Tuple[bool, Dict[str, Any]]:
        """
        Get the status of an invoice from the FBR system.

        Args:
            reference_number: FBR reference number of the invoice
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            Tuple of (success, status_data)
        """
        start_time = datetime.utcnow()

        # Select the appropriate base URL based on environment
        base_url = (
            settings.fbr_sandbox_base_url if environment == FBREnvironment.SANDBOX
            else settings.fbr_production_base_url
        )

        # Prepare the status check request
        # Using FBR's actual endpoint based on technical specification
        status_endpoint = f"{base_url}/invoicestatus/{reference_number}"
        headers = {
            "Authorization": f"Bearer {settings.fbr_api_key}",
            "X-Correlation-ID": generate_correlation_id(),
            "X-Client-ID": settings.fbr_client_id
        }

        try:
            # Make the API call to FBR
            response = await self.client.get(
                status_endpoint,
                headers=headers
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the interaction
            log_fbr_interaction(
                endpoint=status_endpoint,
                method="GET",
                status_code=response.status_code,
                duration=duration,
                request_payload={},
                response_payload=response.json() if response.content else {},
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 200:
                response_data = response.json()

                return True, response_data
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during status check: {response.status_code}")
                response_data = response.json() if response.content else {"error": "Failed to get invoice status"}

                return False, response_data

        except httpx.RequestError as e:
            logger.error(f"Request error during FBR status check: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=status_endpoint,
                method="GET",
                status_code=0,  # No response status
                duration=duration,
                request_payload={},
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during FBR status check: {str(e)}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log the failed interaction
            log_fbr_interaction(
                endpoint=status_endpoint,
                method="GET",
                status_code=0,  # No response status
                duration=duration,
                request_payload={},
                response_payload={"error": str(e)},
                environment=environment.value
            )

            return False, {"error": f"Unexpected error: {str(e)}"}

    async def close(self):
        """
        Close the HTTP client connection.
        """
        await self.client.aclose()

    def prepare_fbr_response_record(self, request_payload: Dict[str, Any],
                                  response_payload: Dict[str, Any],
                                  endpoint: str, method: str, status_code: int,
                                  environment: FBREnvironment,
                                  correlation_id: Optional[str] = None,
                                  invoice_id: Optional[UUID] = None) -> FBRResponseCreate:
        """
        Prepare an FBR response record for database storage.

        Args:
            request_payload: Request sent to FBR
            response_payload: Response received from FBR
            endpoint: FBR API endpoint called
            method: HTTP method used
            status_code: HTTP status code received
            environment: Environment where request was made
            correlation_id: Correlation ID for request/response matching
            invoice_id: Associated invoice ID (if applicable)

        Returns:
            FBRResponseCreate object ready for database insertion
        """
        timestamp = datetime.utcnow()

        return FBRResponseCreate(
            request_payload=request_payload,
            response_payload=response_payload,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            timestamp=timestamp,
            environment=environment,
            correlation_id=correlation_id or generate_correlation_id(),
            processing_duration_ms=None  # Will be calculated separately
        )

    async def validate_connection(self, environment: FBREnvironment) -> bool:
        """
        Validate connection to FBR API.

        Args:
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            base_url = (
                settings.fbr_sandbox_base_url if environment == FBREnvironment.SANDBOX
                else settings.fbr_production_base_url
            )

            health_endpoint = f"{base_url}/health"
            headers = {
                "Authorization": f"Bearer {settings.fbr_api_key}",
            }

            response = await self.client.get(health_endpoint, headers=headers)

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False