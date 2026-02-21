// API Service Layer for FBR Invoice Portal

// Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

// Base API client
class ApiClient {
  protected baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  // Helper method to make API requests
  protected async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Add auth token if available (exclude only login/register endpoints)
    const token = this.getAuthToken();
    const publicEndpoints = ['/auth/login', '/auth/register', '/auth/refresh'];
    const isPublicEndpoint = publicEndpoints.some(path => endpoint.startsWith(path));

    if (token && !isPublicEndpoint) {
      (config.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // FastAPI validation errors are in 'detail', other errors might be in 'error'
      const errorMessage = errorData.detail || errorData.error || `HTTP error! status: ${response.status}`;
      console.error('API Error:', errorMessage, errorData);
      throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }

    // Some endpoints may not return JSON (e.g., PDF downloads)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return {} as T;
  }

  protected getAuthToken(): string | null {
    // In a real app, you'd get this from a secure store
    // For now, we'll use localStorage as a placeholder
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  // Set auth token
  public setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  // Remove auth token
  public removeAuthToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }
}

// Specific service classes extending ApiClient
export class AuthService extends ApiClient {
  async login(email: string, password: string): Promise<{ user: any; token: string }> {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async register(userData: { email: string; password: string; name: string }): Promise<{ user: any }> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async logout(): Promise<void> {
    await this.request('/auth/logout', {
      method: 'POST',
    });
    this.removeAuthToken();
  }

  async getCurrentUser(): Promise<any> {
    return this.request('/auth/profile');
  }
}

export class InvoiceService extends ApiClient {
  async getInvoices(params?: {
    page?: number;
    limit?: number;
    status?: string;
    type?: string;
    search?: string;
    startDate?: string;
    endDate?: string;
    environment?: string;
  }): Promise<{ invoices: any[]; pagination: any }> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, String(value));
        }
      });
    }

    const queryString = queryParams.toString();
    const endpoint = `/invoices${queryString ? '?' + queryString : ''}`;

    return this.request(endpoint);
  }

  async getInvoice(id: string): Promise<any> {
    return this.request(`/invoices/${id}`);
  }

  async createInvoice(invoiceData: any): Promise<any> {
    const response = await this.request('/invoices/', {
      method: 'POST',
      body: JSON.stringify(invoiceData),
    });
    // Backend returns InvoiceResponse directly, wrap it for compatibility
    return { success: true, invoice: response };
  }

  async updateInvoice(id: string, invoiceData: any): Promise<any> {
    const response = await this.request(`/invoices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(invoiceData),
    });

    return { success: true, invoice: response };
  }

  async validateInvoice(id: string): Promise<any> {
    const response = await this.request(`/invoices/${id}/validate`, {
      method: 'POST',
    });
    return { success: true, result: response };
  }

  async postInvoice(id: string): Promise<any> {
    const response = await this.request(`/invoices/${id}/post`, {
      method: 'POST',
    });
    return { success: true, result: response };
  }

  async bulkPostInvoices(invoiceIds: string[]): Promise<{ success: boolean; results: any[] }> {
    return this.request('/invoices/bulk-post', {
      method: 'POST',
      body: JSON.stringify({ invoiceIds }),
    });
  }

  async getInvoicePdf(id: string): Promise<Blob> {
    const url = `${this.baseUrl}/invoices/${id}/pdf`;
    const token = this.getAuthToken();

    const response = await fetch(url, {
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // FastAPI validation errors are in 'detail', other errors might be in 'error'
      const errorMessage = errorData.detail || errorData.error || `HTTP error! status: ${response.status}`;
      console.error('API Error:', errorMessage, errorData);
      throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }

    return await response.blob();
  }
}

export class UserService extends ApiClient {
  async getCurrentUser(): Promise<any> {
    return this.request('/auth/profile');
  }

  async updateEnvironmentPreference(environment: 'sandbox' | 'production'): Promise<{ success: boolean; environment: string; canAccessProduction: boolean }> {
    return this.request('/auth/users/me/environment', {
      method: 'PUT',
      body: JSON.stringify({ environment }),
    });
  }

  async getEnvironmentPreference(): Promise<{ environment: string; canAccessProduction: boolean }> {
    return this.request('/auth/users/me/environment');
  }
}

// Master Data types
export interface Province {
  code: string;
  name: string;
}

export interface UomCode {
  code: string;
  name: string;
}

export interface TaxRate {
  rate: string;
  name: string;
}

export interface SaleType {
  code: string;
  name: string;
}

export interface RegistrationType {
  code: string;
  name: string;
}

export interface InvoiceType {
  code: string;
  name: string;
}

export interface HsCode {
  code: string;
  description: string;
}

export interface TransactionType {
  code: string;
  name: string;
}

export interface SroItem {
  code: string;
  name: string;
}

export interface AllMasterData {
  provinces: Province[];
  uom: UomCode[];
  tax_rates: TaxRate[];
  sale_types: SaleType[];
  registration_types: RegistrationType[];
  invoice_types: InvoiceType[];
  hs_codes: HsCode[];
  transaction_types: TransactionType[];
  sro_items: SroItem[];
}

export class MasterDataService extends ApiClient {
  async getProvinces(): Promise<Province[]> {
    return this.request('/masterdata/provinces');
  }

  async getUomCodes(): Promise<UomCode[]> {
    return this.request('/masterdata/uom');
  }

  async getTaxRates(): Promise<TaxRate[]> {
    return this.request('/masterdata/tax-rates');
  }

  async getSaleTypes(): Promise<SaleType[]> {
    return this.request('/masterdata/sale-types');
  }

  async getRegistrationTypes(): Promise<RegistrationType[]> {
    return this.request('/masterdata/registration-types');
  }

  async getInvoiceTypes(): Promise<InvoiceType[]> {
    return this.request('/masterdata/invoice-types');
  }

  async getAllMasterData(): Promise<AllMasterData> {
    return this.request('/masterdata/all');
  }

  // Parameterized APIs - called dynamically during form filling
  async getSroSchedule(rateId: number, date: string, originationSupplierCsv: number): Promise<Array<{id: string, description: string}>> {
    const params = new URLSearchParams({
      rate_id: rateId.toString(),
      date: date,
      origination_supplier_csv: originationSupplierCsv.toString()
    });
    return this.request(`/masterdata/sro-schedule?${params.toString()}`);
  }

  async getSaleTypeToRate(date: string, transTypeId: number, originationSupplier: number): Promise<any[]> {
    const params = new URLSearchParams({
      date: date,
      trans_type_id: transTypeId.toString(),
      origination_supplier: originationSupplier.toString()
    });
    return this.request(`/masterdata/sale-type-to-rate?${params.toString()}`);
  }

  async getHsUom(hsCode: string, annexureId: number): Promise<Array<{code: string, name: string}>> {
    const params = new URLSearchParams({
      hs_code: hsCode,
      annexure_id: annexureId.toString()
    });
    return this.request(`/masterdata/hs-uom?${params.toString()}`);
  }

  async getSroItemDetails(date: string, sroId: number): Promise<any[]> {
    const params = new URLSearchParams({
      date: date,
      sro_id: sroId.toString()
    });
    return this.request(`/masterdata/sro-item-details?${params.toString()}`);
  }
}

// FBR Integration types
export interface BuyerVerificationRequest {
  ntn_cnic: string;
  environment?: string;
}

export interface BuyerVerificationResponse {
  success: boolean;
  registration_type: string;
  is_registered: boolean;
  business_name?: string;
  error?: string;
}

export class FBRIntegrationService extends ApiClient {
  async verifyBuyer(ntnCnic: string, environment: string = 'SANDBOX'): Promise<BuyerVerificationResponse> {
    return this.request('/fbr/verify-buyer', {
      method: 'POST',
      body: JSON.stringify({
        ntn_cnic: ntnCnic,
        environment: environment
      }),
    });
  }

  async getHSCodeDescription(hsCode: string): Promise<{ hs_code: string; description: string | null; found: boolean; message?: string }> {
    return this.request(`/fbr-reference/hs-code/${encodeURIComponent(hsCode)}`, {
      method: 'GET',
    });
  }
}

// Export singleton instances
export const authService = new AuthService();
export const invoiceService = new InvoiceService();
export const userService = new UserService();
export const masterDataService = new MasterDataService();
export const fbrIntegrationService = new FBRIntegrationService();