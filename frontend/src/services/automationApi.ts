/**
 * Automation API client for Excel upload and dashboard endpoints.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

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
}

export interface DashboardStats {
  total_invoices: number;
  pending_count: number;
  expired_count: number;
  validated_count: number;
  submitted_count: number;
  failed_count: number;
}

export interface AutomationInvoice {
  id: string;
  user_id: string;
  excel_upload_session_id: string;
  invoice_number: string;
  invoice_data: Record<string, any>;
  scheduled_date: string;
  scheduled_time: string;
  status: 'pending' | 'expired' | 'validated' | 'submitted' | 'failed';
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

class AutomationApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get authentication token from localStorage.
   */
  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  /**
   * Get headers with authentication.
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {};
    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Download Excel template.
   */
  async downloadTemplate(): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/v1/automation/template/download`, {
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

    const response = await fetch(`${this.baseUrl}/api/v1/automation/excel/upload`, {
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
      `${this.baseUrl}/api/v1/automation/excel/status/${sessionId}`,
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
    const response = await fetch(`${this.baseUrl}/api/v1/automation/dashboard/stats`, {
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
    page?: number;
    page_size?: number;
  }): Promise<InvoiceListResponse> {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.source) queryParams.append('source', params.source);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());

    const response = await fetch(
      `${this.baseUrl}/api/v1/automation/dashboard/invoices?${queryParams}`,
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
   * Get invoice details with logs.
   */
  async getInvoiceDetail(invoiceId: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/automation/dashboard/invoice/${invoiceId}`,
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
  async downloadExcel(sessionId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/automation/dashboard/download/${sessionId}`,
      {
        headers: this.getHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to download Excel file');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `invoices_${sessionId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  /**
   * Manually retry failed invoice.
   */
  async retryInvoice(invoiceId: string): Promise<InvoiceRetryResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/automation/invoice/${invoiceId}/retry`,
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
}

// Export singleton instance
export const automationApi = new AutomationApiClient();
