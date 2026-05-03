from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import time, datetime


class AutoPostingConfigBase(BaseModel):
    """Base schema for auto-posting configuration."""
    auto_posting_enabled: bool = Field(
        default=False,
        description="Master toggle for auto-posting feature"
    )
    auto_posting_start_time: time = Field(
        default=time(9, 0),
        description="Start time of posting window (24-hour format)"
    )
    auto_posting_end_time: time = Field(
        default=time(18, 0),
        description="End time of posting window (24-hour format)"
    )
    auto_posting_environment: str = Field(
        default="SANDBOX",
        description="Target FBR environment (SANDBOX/PRODUCTION)"
    )
    auto_posting_daily_limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum invoices to post per day (1-1000)"
    )
    auto_posting_paused_until: Optional[datetime] = Field(
        default=None,
        description="Temporary pause until this timestamp"
    )

    @validator('auto_posting_environment')
    def validate_environment(cls, v):
        """Validate environment is SANDBOX or PRODUCTION."""
        if v not in ['SANDBOX', 'PRODUCTION']:
            raise ValueError('Environment must be SANDBOX or PRODUCTION')
        return v

    @validator('auto_posting_daily_limit')
    def validate_daily_limit(cls, v):
        """Validate daily limit is between 1 and 1000."""
        if v < 1 or v > 1000:
            raise ValueError('Daily limit must be between 1 and 1000')
        return v


class AutoPostingConfig(AutoPostingConfigBase):
    """Schema for reading auto-posting configuration."""
    pass


class AutoPostingConfigUpdate(BaseModel):
    """Schema for updating auto-posting configuration."""
    auto_posting_enabled: Optional[bool] = None
    auto_posting_start_time: Optional[time] = None
    auto_posting_end_time: Optional[time] = None
    auto_posting_environment: Optional[str] = None
    auto_posting_daily_limit: Optional[int] = Field(None, ge=1, le=1000)
    auto_posting_paused_until: Optional[datetime] = None

    @validator('auto_posting_start_time', 'auto_posting_end_time', pre=True)
    def parse_time(cls, v):
        """Parse time from string if needed."""
        if v is None:
            return v
        if isinstance(v, time):
            return v
        if isinstance(v, str):
            # Parse ISO format time string (HH:MM:SS or HH:MM)
            try:
                parts = v.split(':')
                if len(parts) == 2:
                    return time(int(parts[0]), int(parts[1]))
                elif len(parts) == 3:
                    return time(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    raise ValueError(f'Invalid time format: {v}')
            except (ValueError, IndexError) as e:
                raise ValueError(f'Invalid time format: {v}. Expected HH:MM:SS or HH:MM')
        raise ValueError(f'Invalid time type: {type(v)}')

    @validator('auto_posting_environment')
    def validate_environment(cls, v):
        """Validate environment is SANDBOX or PRODUCTION."""
        if v is not None and v not in ['SANDBOX', 'PRODUCTION']:
            raise ValueError('Environment must be SANDBOX or PRODUCTION')
        return v


class ManualPostingRequest(BaseModel):
    """Schema for manual posting request."""
    override_daily_limit: bool = Field(
        default=False,
        description="Override daily limit warning"
    )


class ManualPostingResponse(BaseModel):
    """Schema for manual posting response."""
    success: bool
    message: str
    invoice_id: str
    fbr_reference_number: Optional[str] = None
    error_details: Optional[dict] = None
    daily_limit_warning: bool = Field(
        default=False,
        description="True if daily limit was reached"
    )


class PostingStatusResponse(BaseModel):
    """Schema for posting status response."""
    status: str = Field(
        description="Current status: active, outside_hours, disabled, paused, limit_reached"
    )
    auto_posting_enabled: bool
    current_window_active: bool
    next_check_time: Optional[datetime] = None
    today_posted_count: int
    today_failed_count: int
    remaining_limit: int
    daily_limit: int
    environment: str
    paused_until: Optional[datetime] = None


class PostingHistoryItem(BaseModel):
    """Schema for posting history item."""
    id: str
    invoice_id: str
    action: str  # 'auto' or 'manual'
    result: str  # 'success' or 'failure'
    environment: str
    error_details: Optional[dict] = None
    created_at: datetime


class PostingHistoryResponse(BaseModel):
    """Schema for posting history response."""
    items: list[PostingHistoryItem]
    total: int
    page: int
    page_size: int


class EmergencyPauseResponse(BaseModel):
    """Schema for emergency pause response."""
    success: bool
    message: str
    auto_posting_enabled: bool
