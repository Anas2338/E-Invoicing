/**
 * Company API client for employee provisioning (company owner only).
 *
 * Pattern: frontend/src/services/adminApi.ts — class + getHeaders CSRF
 * convention, singleton export.
 */

// Use environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

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

export interface CompanyMember {
  id: string;
  email: string;
  name: string;
  role: string;
  is_company_owner: boolean;
  automation_enabled: boolean;
  is_active: boolean;
  account_status: string;
  created_at: string;
}

export interface EmployeeListResponse {
  members: CompanyMember[];
  total: number;
}

export interface EmployeeCreateResponse {
  id: string;
  email: string;
  name: string;
  temporary_password?: string | null; // present ONLY when server-generated
  automation_enabled: boolean;
  is_company_owner: boolean;
  created_at: string;
}

class CompanyApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get headers for API requests with CSRF token for state-changing methods.
   */
  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token - try cookie first, then sessionStorage (for cross-origin)
    const csrfToken = getCookie('csrf_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('csrf_token') : null);
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  }

  /**
   * Create an employee account. When the server generates the temporary
   * password it is returned ONCE in the response.
   */
  async createEmployee(data: { email: string; name: string; password?: string }): Promise<EmployeeCreateResponse> {
    const response = await fetch(`${this.baseUrl}/company/employees`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to create employee');
    }

    return response.json();
  }

  /**
   * List the company's members (owner + active + deactivated employees).
   */
  async listEmployees(): Promise<EmployeeListResponse> {
    const response = await fetch(`${this.baseUrl}/company/employees`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to get company members');
    }

    return response.json();
  }

  /**
   * Deactivate an employee — blocks their login and kills active sessions.
   * Their data stays with the company.
   */
  async deactivateEmployee(employeeId: string): Promise<{ id: string; is_active: boolean }> {
    const response = await fetch(`${this.baseUrl}/company/employees/${employeeId}/deactivate`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to deactivate employee');
    }

    return response.json();
  }
}

// Export singleton instance
export const companyApi = new CompanyApiClient();
