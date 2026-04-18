"""
FBR Poster Skill - Posts invoices to FBR using existing FBRClient.

Wraps the backend FBRClient to provide FBR submission within the
AI Agent context.
"""
from typing import Dict, Any, Optional
import sys
import asyncio
from pathlib import Path

# Add project root and backend to path (works on both Windows and Docker)
# Backend must be in path for its relative imports (from src.*)
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

# Import backend dependencies using src.* (not backend.src.*) to match backend's own imports
# This ensures there's only ONE import path, preventing SQLAlchemy metadata conflicts
from src.services.fbr_client import FBRClient
from src.schemas.fbr import FBREnvironment

from skills import BaseSkill, SkillResult, SkillStatus


class FBRPosterSkill(BaseSkill):
    """
    Skill for posting invoices to FBR API.

    Wraps the existing FBRClient from the backend.
    """

    def __init__(self):
        """Initialize FBR poster skill."""
        super().__init__("fbr_poster")

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Must contain 'invoice_data', 'environment', and 'fbr_token' keys

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'invoice_data' not in data:
            return False, "Missing required field: invoice_data"

        if 'environment' not in data:
            return False, "Missing required field: environment"

        if 'fbr_token' not in data:
            return False, "Missing required field: fbr_token"

        if data['environment'] not in ['SANDBOX', 'PRODUCTION']:
            return False, "environment must be 'SANDBOX' or 'PRODUCTION'"

        return True, None

    async def execute_async(self, context: Dict[str, Any]) -> SkillResult:
        """
        Post invoice to FBR API (async version).

        Args:
            context: Must contain 'invoice_data', 'environment', and 'fbr_token'

        Returns:
            SkillResult with submission outcome
        """
        try:
            from config import config

            invoice_data = context['invoice_data']
            environment_str = context['environment']
            fbr_token = context['fbr_token']
            environment = FBREnvironment.SANDBOX if environment_str == 'SANDBOX' else FBREnvironment.PRODUCTION

            # DRY RUN MODE - Simulate FBR response without actual API call
            if config.DRY_RUN:
                import random
                import time

                self.logger.info(f"[DRY RUN] Simulating FBR posting for invoice {invoice_data.get('invoice_number', 'unknown')}")

                # Simulate API delay (100-500ms)
                await asyncio.sleep(random.uniform(0.1, 0.5))

                # Simulate 95% success rate (5% random failures for testing error handling)
                is_posted = random.random() < 0.95

                if is_posted:
                    # Simulate successful FBR response
                    reference_number = f"DRY-{int(time.time())}-{random.randint(1000, 9999)}"
                    response_data = {
                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "postingResponse": {
                            "statusCode": "00",
                            "status": "Posted",
                            "invoiceNumber": reference_number,
                            "error": ""
                        }
                    }
                    self.logger.info(f"[DRY RUN] Simulated SUCCESS for invoice {invoice_data.get('invoice_number')}")
                else:
                    # Simulate random FBR error for testing
                    error_scenarios = [
                        {"code": "0052", "msg": "HS Code does not match with provided sale type"},
                        {"code": "0078", "msg": "Valid Item Sr. No. is mandatory where SRO/Schedule No. is provided"},
                        {"code": "0099", "msg": "Network timeout - please retry"}
                    ]
                    error = random.choice(error_scenarios)
                    reference_number = None
                    response_data = {
                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "postingResponse": {
                            "statusCode": "01",
                            "status": "Failed",
                            "error": f"[{error['code']}] {error['msg']}"
                        }
                    }
                    self.logger.warning(f"[DRY RUN] Simulated FAILURE for invoice {invoice_data.get('invoice_number')}: {error['msg']}")
            else:
                # REAL MODE - Actual FBR API call
                fbr_client = FBRClient()

                # Post invoice to FBR using user's credentials
                is_posted, response_data, reference_number = await fbr_client.post_invoice_with_user_credentials(
                    invoice_data=invoice_data,
                    environment=environment,
                    fbr_token=fbr_token
                )

            if is_posted:
                self.logger.info(f"Invoice {invoice_data.get('invoice_number', 'unknown')} posted successfully to FBR")
                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    data={
                        "is_posted": True,
                        "invoice_number": invoice_data.get('invoice_number'),
                        "reference_number": reference_number,
                        "response_data": response_data
                    }
                )
            else:
                self.logger.warning(f"Invoice {invoice_data.get('invoice_number', 'unknown')} FBR submission failed")
                return SkillResult(
                    status=SkillStatus.FAILURE,
                    data={
                        "is_posted": False,
                        "invoice_number": invoice_data.get('invoice_number'),
                        "response_data": response_data
                    },
                    error=f"FBR submission failed: {response_data}"
                )

        except Exception as e:
            return self.handle_error(e, context)

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Post invoice to FBR API (sync wrapper).

        Args:
            context: Must contain 'invoice_data' and 'environment'

        Returns:
            SkillResult with submission outcome
        """
        import asyncio

        try:
            # Create a new event loop for this thread (APScheduler runs in thread pool)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                return loop.run_until_complete(self.execute_async(context))
            finally:
                loop.close()

        except Exception as e:
            return self.handle_error(e, context)
