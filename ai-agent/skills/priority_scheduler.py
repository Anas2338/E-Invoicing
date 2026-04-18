"""
Priority Scheduler Skill - Business rule-based invoice prioritization.

Implements multi-factor prioritization based on:
- Scheduled time proximity (50% weight)
- Invoice value (30% weight)
- Retry count (20% weight)
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, time as time_type
import sys
sys.path.insert(0, '/app')

from skills import BaseSkill, SkillResult, SkillStatus
from config import config


class PrioritySchedulerSkill(BaseSkill):
    """
    Skill for prioritizing invoices based on business rules.

    Calculates priority scores using weighted factors:
    - Time proximity: How close to scheduled time (higher = more urgent)
    - Invoice value: Higher value invoices get priority
    - Retry count: Failed invoices with fewer retries get priority
    """

    def __init__(self):
        """Initialize priority scheduler skill."""
        super().__init__("priority_scheduler")

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Must contain 'invoices' list

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'invoices' not in data:
            return False, "Missing required field: invoices"

        if not isinstance(data['invoices'], list):
            return False, "invoices must be a list"

        return True, None

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Calculate priority scores for invoices and sort by priority.

        Args:
            context: Must contain 'invoices' list with invoice objects

        Returns:
            SkillResult with prioritized invoice list
        """
        try:
            invoices = context['invoices']

            if not invoices:
                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    data={
                        "prioritized_invoices": [],
                        "count": 0
                    }
                )

            # Calculate priority scores
            scored_invoices = []
            for invoice in invoices:
                score = self._calculate_priority_score(invoice)

                # Handle both dict and object inputs
                if isinstance(invoice, dict):
                    invoice_id = str(invoice['id'])
                    invoice_number = invoice.get('invoice_number', 'N/A')
                else:
                    invoice_id = str(invoice.id)
                    invoice_number = invoice.invoice_number

                scored_invoices.append({
                    "invoice": invoice,
                    "priority_score": score,
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number
                })

            # Sort by priority score (highest first)
            scored_invoices.sort(key=lambda x: x['priority_score'], reverse=True)

            self.logger.info(
                f"Prioritized {len(scored_invoices)} invoices, "
                f"top priority: {scored_invoices[0]['invoice_number']} "
                f"(score: {scored_invoices[0]['priority_score']:.2f})"
            )

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "prioritized_invoices": scored_invoices,
                    "count": len(scored_invoices)
                },
                metadata={
                    "weight_time": config.PRIORITY_WEIGHT_TIME,
                    "weight_value": config.PRIORITY_WEIGHT_VALUE,
                    "weight_retry": config.PRIORITY_WEIGHT_RETRY
                }
            )

        except Exception as e:
            return self.handle_error(e, context)

    def _calculate_priority_score(self, invoice) -> float:
        """
        Calculate priority score for a single invoice.

        Args:
            invoice: AutomationInvoice object or dict

        Returns:
            Priority score (0-100, higher = more urgent)
        """
        # Handle both dict and object inputs
        if isinstance(invoice, dict):
            scheduled_date = invoice['scheduled_date']
            scheduled_time = invoice['scheduled_time']
            invoice_data = invoice.get('invoice_data', {})
            retry_count = invoice.get('retry_count', 0)
            total_amount = invoice.get('total_amount', 0)
        else:
            scheduled_date = invoice.scheduled_date
            scheduled_time = invoice.scheduled_time
            invoice_data = invoice.invoice_data
            retry_count = invoice.retry_count
            total_amount = None

        # Factor 1: Time proximity (0-100)
        time_score = self._calculate_time_proximity_score(
            scheduled_date,
            scheduled_time
        )

        # Factor 2: Invoice value (0-100)
        if total_amount is not None:
            # For dict input with total_amount
            value_score = self._calculate_value_score_from_amount(total_amount)
        else:
            # For object input with invoice_data
            value_score = self._calculate_value_score(invoice_data)

        # Factor 3: Retry count (0-100, fewer retries = higher score)
        retry_score = self._calculate_retry_score(retry_count)

        # Weighted sum
        priority_score = (
            time_score * config.PRIORITY_WEIGHT_TIME +
            value_score * config.PRIORITY_WEIGHT_VALUE +
            retry_score * config.PRIORITY_WEIGHT_RETRY
        )

        return priority_score

    def _calculate_time_proximity_score(
        self,
        scheduled_date,
        scheduled_time: time_type
    ) -> float:
        """
        Calculate time proximity score (0-100).

        Invoices closer to their scheduled time get higher scores.

        Args:
            scheduled_date: Scheduled date
            scheduled_time: Scheduled time

        Returns:
            Score from 0-100
        """
        from datetime import datetime, timedelta

        # Combine date and time
        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
        now = datetime.utcnow()

        # Calculate time difference in minutes
        time_diff = (scheduled_datetime - now).total_seconds() / 60

        if time_diff <= 0:
            # Past due - highest priority
            return 100.0
        elif time_diff <= 5:
            # Within 5 minutes - very high priority
            return 90.0
        elif time_diff <= 15:
            # Within 15 minutes - high priority
            return 70.0
        elif time_diff <= 60:
            # Within 1 hour - medium priority
            return 50.0
        else:
            # More than 1 hour away - low priority
            return max(0.0, 50.0 - (time_diff - 60) / 10)

    def _calculate_value_score(self, invoice_data: dict) -> float:
        """
        Calculate invoice value score (0-100).

        Higher value invoices get higher scores.

        Args:
            invoice_data: Invoice data dictionary

        Returns:
            Score from 0-100
        """
        # Extract total amount from invoice data
        total_amount = invoice_data.get('total_amount', 0)
        return self._calculate_value_score_from_amount(total_amount)

    def _calculate_value_score_from_amount(self, total_amount: float) -> float:
        """
        Calculate value score from total amount.

        Args:
            total_amount: Invoice total amount

        Returns:
            Score from 0-100
        """
        try:
            # Normalize to 0-100 scale
            # Assuming typical invoice range: 0 - 1,000,000 PKR
            if total_amount <= 0:
                return 0.0
            elif total_amount >= 1000000:
                return 100.0
            else:
                return (total_amount / 1000000) * 100

        except Exception as e:
            self.logger.warning(f"Error calculating value score: {str(e)}")
            return 50.0  # Default to medium priority

    def _calculate_retry_score(self, retry_count: int) -> float:
        """
        Calculate retry score (0-100).

        Invoices with fewer retries get higher scores to prevent
        starvation of new invoices.

        Args:
            retry_count: Number of retry attempts

        Returns:
            Score from 0-100
        """
        if retry_count == 0:
            # First attempt - highest priority
            return 100.0
        elif retry_count == 1:
            return 80.0
        elif retry_count == 2:
            return 60.0
        elif retry_count == 3:
            return 40.0
        elif retry_count == 4:
            return 20.0
        else:
            # 5+ retries - lowest priority
            return 10.0
