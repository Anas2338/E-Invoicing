/**
 * Automation API client for Excel upload and dashboard endpoints.
 * Routes directly to the AI-agent backend (separate service, CORS-protected).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_AI_AGENT_API_URL || 'http://localhost:8002/api/v1';

// Helper function to get cookie value by name
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

export interface ExcelUploadResponse {
  session_id: string;
  total_rows: number;
  message: string;
}

export interface ExcelUploadStatusResponse {
  session_id: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  processed_rows: number;
  total_rows: number;
  error_message?: string;
  validated_count?: number;
  failed_count?: number;
  expired_count?: number;
  pending_count?: number;
  progress_percentage?: number;
}

export interface DashboardStats {
  total_invoices: number;
  pending_count: number;
  expired_count: number;
  validated_count: number;
  paused_count: number;
  transferred_count: number;
  transfer_failed_count: number;
  failed_count: number;
  blocked_count: number;
}

export interface AutomationInvoice {
  id: string;
  user_id: string;
  excel_upload_session_id: string;
  invoice_number: string;
  invoice_data: Record<string, any>;
  scheduled_date: string;
  scheduled_time: string;
  status: 'pending' | 'expired' | 'validated' | 'transferred' | 'transfer_failed' | 'failed' | 'blocked';
  validation_errors?: string;
  fbr_response?: Record<string, any>;
  created_at: string;
  processed_at?: string;
}

export interface InvoiceListResponse {
  invoices: AutomationInvoice[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InvoiceRetryResponse {
  message: string;
  invoice_id: string;
  status: string;
  result?: Record<string, any>;
}

export interface UploadSession {
  id: string;
  uploaded_at: string;
  total_count: number;
  pending_count: number;
  validated_count: number;
  transferred_count: number;
  transfer_failed_count: number;
  failed_count: number;
  blocked_count: number;
  expired_count: number;
  can_delete: boolean;
  can_delete_file: boolean;
  has_file: boolean;
  processing_status: string;
  processed_rows: number;
  total_rows: number;
  error_message?: string;
}

export interface UploadSessionsResponse {
  sessions: UploadSession[];
  total: number;
}

class AutomationApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get headers for API requests with CSRF token for state-changing methods.
   */
  private getHeaders(includeContentType: boolean = false): HeadersInit {
    const headers: Record<string, string> = {};

    // Add CSRF token - try cookie first, then sessionStorage (for cross-origin)
    const csrfToken = getCookie('csrf_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('csrf_token') : null);
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    } else {
      // Log warning if CSRF token is missing (helps debug cross-origin issues)
      console.warn('CSRF token not found in cookie or sessionStorage. This may cause request failures.');
    }

    // Add access token as Authorization header for cross-origin requests
    // The httpOnly cookie from the main backend (port 8001) cannot be sent to
    // the AI-agent service (port 8002), so we pass the token explicitly
    const accessToken = getCookie('access_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('access_token') : null);
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    if (includeContentType) {
      headers['Content-Type'] = 'application/json';
    }

    return headers;
  }

  /**
   * Download Excel template.
   */
  async downloadTemplate(): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/automation/template/download`, {
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to download template');
    }
    return response.blob();
  }

  /**
   * Upload Excel file for bulk invoice scheduling.
   */
  async uploadExcel(file: File): Promise<ExcelUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Get CSRF token for debugging
    const csrfToken = getCookie('csrf_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('csrf_token') : null);

    if (!csrfToken) {
      throw new Error('CSRF token not found. Please log out and log in again to refresh your session.');
    }

    const response = await fetch(`${this.baseUrl}/automation/excel/upload`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  /**
   * Check upload processing status.
   */
  async getUploadStatus(sessionId: string): Promise<ExcelUploadStatusResponse> {
    const response = await fetch(
      `${this.baseUrl}/automation/excel/status/${sessionId}`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get upload status');
    }

    return response.json();
  }

  /**
   * Get dashboard statistics.
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await fetch(`${this.baseUrl}/automation/dashboard/stats`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get dashboard stats');
    }

    return response.json();
  }

  /**
   * Get paginated invoice list with filters.
   */
  async getInvoiceList(params: {
    status?: string;
    source?: string;
    date_from?: string;
    date_to?: string;
    invoice_number?: string;
    customer?: string;
    page?: number;
    page_size?: number;
  }): Promise<InvoiceListResponse> {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.source) queryParams.append('source', params.source);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.invoice_number) queryParams.append('invoice_number', params.invoice_number);
    if (params.customer) queryParams.append('customer', params.customer);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());

    const response = await fetch(
      `${this.baseUrl}/automation/dashboard/invoices?${queryParams}`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get invoices');
    }

    return response.json();
  }

  /**
   * Get ALL invoice IDs matching filters (no pagination).
   * Used for "Select All" across all pages.
   */
  async getAllInvoiceIds(params: {
    status?: string;
    source?: string;
    date_from?: string;
    date_to?: string;
    invoice_number?: string;
    customer?: string;
  }): Promise<{ invoice_ids: string[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.source) queryParams.append('source', params.source);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.invoice_number) queryParams.append('invoice_number', params.invoice_number);
    if (params.customer) queryParams.append('customer', params.customer);

    const response = await fetch(
      `${this.baseUrl}/automation/dashboard/invoices/ids?${queryParams}`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get invoice IDs');
    }

    return response.json();
  }

  /**
   * Get invoice details with logs.
   */
  async getInvoiceDetail(invoiceId: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/automation/dashboard/invoice/${invoiceId}`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get invoice details');
    }

    return response.json();
  }

  /**
   * Download updated Excel file.
   */
  async downloadExcel(sessionId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/automation/dashboard/download/${sessionId}`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      throw new Error('Failed to download Excel file');
    }

    return response.blob();
  }

  /**
   * Manually retry failed invoice.
   */
  async retryInvoice(invoiceId: string): Promise<InvoiceRetryResponse> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}/retry`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to retry invoice');
    }

    return response.json();
  }

  /**
   * Get all upload sessions with invoice counts.
   */
  async getUploadSessions(): Promise<UploadSessionsResponse> {
    const response = await fetch(
      `${this.baseUrl}/automation/upload-sessions`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get upload sessions');
    }

    return response.json();
  }

  /**
   * Delete an upload session and all its invoices.
   */
  async deleteUploadSession(sessionId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/automation/upload-session/${sessionId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete upload session');
    }
  }

  /**
   * Delete only the Excel file for an upload session.
   * Session and invoice records remain for audit purposes.
   */
  async deleteExcelFile(sessionId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/automation/upload-session/${sessionId}/file`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete Excel file');
    }
  }

  /**
   * Block an invoice from FBR submission.
   */
  async blockInvoice(invoiceId: string, reason?: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}/block`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ reason }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to block invoice');
    }
  }

  /**
   * Unblock an invoice to allow FBR submission.
   */
  async unblockInvoice(invoiceId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}/unblock`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to unblock invoice');
    }
  }

  /**
   * Delete a single invoice.
   */
  async deleteInvoice(invoiceId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete invoice');
    }
  }

  /**
   * Get simplified statistics for main dashboard.
   */
  async getStatistics(): Promise<{
    pending: number;
    validated: number;
    transferred: number;
    failed: number;
  }> {
    const stats = await this.getDashboardStats();
    return {
      pending: stats.pending_count,
      validated: stats.validated_count,
      transferred: stats.transferred_count,
      failed: stats.failed_count,
    };
  }

  /**
   * Block multiple invoices at once.
   */
  async bulkBlockInvoices(invoiceIds: string[], reason?: string): Promise<{ blocked_count: number }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/bulk-block`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds, reason }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to block invoices');
    }

    return response.json();
  }

  /**
   * Delete multiple invoices at once.
   */
  async bulkDeleteInvoices(invoiceIds: string[]): Promise<{ deleted_count: number }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/bulk-delete`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete invoices');
    }

    return response.json();
  }

  /**
   * Retry multiple invoices at once (re-validates each against FBR).
   */
  async bulkRetryInvoices(invoiceIds: string[]): Promise<{
    retried_count: number;
    validated_count: number;
    failed_count: number;
  }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/bulk-retry`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to retry invoices');
    }

    return response.json();
  }

  /**
   * Generate and download PDF for a single invoice.
   */
  async printInvoice(invoiceId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/${invoiceId}/pdf`,
      {
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate PDF');
    }

    return response.blob();
  }

  /**
   * Pause a validated invoice to prevent AI agent transfer.
   */
  async pauseInvoice(invoiceId: string): Promise<{ success: boolean; message: string; invoice_id: string; status: string }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}/pause`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to pause invoice');
    }

    return response.json();
  }

  /**
   * Resume a paused invoice so AI agent can transfer it.
   */
  async resumeInvoice(invoiceId: string): Promise<{ success: boolean; message: string; invoice_id: string; status: string }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoice/${invoiceId}/resume`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resume invoice');
    }

    return response.json();
  }

  /**
   * Bulk pause multiple validated invoices.
   */
  async bulkPauseInvoices(invoiceIds: string[]): Promise<{ paused_count: number }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/bulk-pause`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to pause invoices');
    }

    return response.json();
  }

  /**
   * Bulk resume multiple paused invoices.
   */
  async bulkResumeInvoices(invoiceIds: string[]): Promise<{ resumed_count: number }> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/bulk-resume`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resume invoices');
    }

    return response.json();
  }

  /**
   * Generate and download batch PDF for multiple invoices.
   */
  async printBatchInvoices(invoiceIds: string[]): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/automation/invoices/batch-pdf`,
      {
        method: 'POST',
        headers: this.getHeaders(true),
          body: JSON.stringify({ invoice_ids: invoiceIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate batch PDF');
    }

    return response.blob();
  }
}

// Export singleton instance
export const automationApi = new AutomationApiClient();
