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


logger = logging.getLogger(__name__)


class FBRClient:
    """
    Client for interacting with FBR APIs for validation and posting.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout
            follow_redirects=True
        )

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
            validation_endpoint = f"{settings.fbr_sandbox_base_url}/di_data/v1/di/validateinvoicedata_sb"
        else:
            validation_endpoint = f"{settings.fbr_production_base_url}/di_data/v1/di/validateinvoicedata"

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

            # Log the interaction
            log_fbr_interaction(
                endpoint=validation_endpoint,
                method="POST",
                status_code=response.status_code,
                duration=duration,
                request_payload=payload,
                response_payload=response.json() if response.content else {},
                environment=environment.value,
                correlation_id=headers["X-Correlation-ID"]
            )

            # Handle the response
            if response.status_code == 200:
                response_data = response.json()

                # Check if validation was successful
                is_valid = response_data.get("valid", False)
                reference_number = response_data.get("reference_number")

                return is_valid, response_data, reference_number
            elif response.status_code in [400, 422]:
                # Validation failed with specific errors
                response_data = response.json() if response.content else {}

                return False, response_data, None
            else:
                # Unexpected status code
                logger.error(f"Unexpected status code during validation: {response.status_code}")
                response_data = response.json() if response.content else {"error": "Unexpected response from FBR"}

                return False, response_data, None

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
            posting_endpoint = f"{settings.fbr_sandbox_base_url}/di_data/v1/di/postinvoicedata_sb"
        else:
            posting_endpoint = f"{settings.fbr_production_base_url}/di_data/v1/di/postinvoicedata"

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
        status_endpoint = f"{base_url}/di_data/v1/di/invoicestatus/{reference_number}"
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