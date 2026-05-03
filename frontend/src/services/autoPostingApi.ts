/**
 * API client for auto-posting configuration and operations
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

/**
 * Get CSRF token from cookie or sessionStorage
 */
function getCsrfToken(): string | null {
  // Try to get from cookie first
  const value = `; ${document.cookie}`;
  const parts = value.split(`; csrf_token=`);
  if (parts.length === 2) {
    const token = parts.pop()?.split(';').shift() || null;
    if (token) return token;
  }

  // Fallback to sessionStorage
  return sessionStorage.getItem('csrf_token');
}

/**
 * Get headers with CSRF token
 */
function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  return headers;
}

export interface AutoPostingConfig {
  auto_posting_enabled: boolean;
  auto_posting_start_time: string;
  auto_posting_end_time: string;
  auto_posting_environment: 'SANDBOX' | 'PRODUCTION';
  auto_posting_daily_limit: number;
  auto_posting_paused_until: string | null;
}

export interface AutoPostingConfigUpdate {
  auto_posting_enabled?: boolean;
  auto_posting_start_time?: string;
  auto_posting_end_time?: string;
  auto_posting_environment?: 'SANDBOX' | 'PRODUCTION';
  auto_posting_daily_limit?: number;
  auto_posting_paused_until?: string | null;
}

export interface PostingStatusResponse {
  status: string;
  auto_posting_enabled: boolean;
  current_window_active: boolean;
  next_check_time: string | null;
  today_posted_count: number;
  today_failed_count: number;
  remaining_limit: number;
  daily_limit: number;
  environment: string;
  paused_until: string | null;
}

export interface ManualPostingResponse {
  success: boolean;
  message: string;
  invoice_id: string;
  fbr_reference_number: string | null;
  error_details: any | null;
  daily_limit_warning: boolean;
}

/**
 * Get auto-posting configuration
 */
export async function getAutoPostingConfig(): Promise<AutoPostingConfig> {
  const response = await fetch(`${API_BASE_URL}/profile/auto-posting`, {
    method: 'GET',
    credentials: 'include',
    headers: getHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch auto-posting configuration');
  }

  return response.json();
}

/**
 * Update auto-posting configuration
 */
export async function updateAutoPostingConfig(
  config: AutoPostingConfigUpdate
): Promise<AutoPostingConfig & { message: string }> {
  const response = await fetch(`${API_BASE_URL}/profile/auto-posting`, {
    method: 'PUT',
    credentials: 'include',
    headers: getHeaders(),
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update auto-posting configuration');
  }

  return response.json();
}

/**
 * Emergency pause auto-posting
 */
export async function emergencyPauseAutoPosting(): Promise<{
  success: boolean;
  message: string;
  auto_posting_enabled: boolean;
}> {
  const response = await fetch(`${API_BASE_URL}/profile/auto-posting/emergency-pause`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to pause auto-posting');
  }

  return response.json();
}

/**
 * Get posting status and statistics
 */
export async function getPostingStatus(): Promise<PostingStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/invoices/posting-status`, {
    method: 'GET',
    credentials: 'include',
    headers: getHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch posting status');
  }

  return response.json();
}

/**
 * Manually post invoice to FBR
 */
export async function manualPostInvoice(
  invoiceId: string,
  overrideDailyLimit: boolean = false
): Promise<ManualPostingResponse> {
  const response = await fetch(`${API_BASE_URL}/invoices/${invoiceId}/post-to-fbr`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders(),
    body: JSON.stringify({ override_daily_limit: overrideDailyLimit }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to post invoice');
  }

  return response.json();
}
