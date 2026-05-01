// API Service Layer for FBR Invoice Portal

// Configuration - use environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

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

// Helper function to get CSRF token from cookie or sessionStorage
// SECURITY: Try cookie first (same-origin), then sessionStorage (cross-origin)
// sessionStorage is more secure than localStorage (cleared on tab close)
function getCsrfToken(): string | null {
  // Try cookie first
  const cookieToken = getCookie('csrf_token');
  if (cookieToken) return cookieToken;

  // Fallback to sessionStorage for cross-origin scenarios
  if (typeof sessionStorage !== 'undefined') {
    return sessionStorage.getItem('csrf_token');
  }

  return null;
}

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

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    // Add CSRF token for state-changing requests
    const method = options.method?.toUpperCase() || 'GET';
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    const config: RequestInit = {
      headers,
      credentials: 'include', // Important: send httpOnly cookies with request
      ...options,
    };

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
    // Cookies are cleared by the backend
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

    const response = await fetch(url, {
      credentials: 'include', // Important: send httpOnly cookies with request
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

export class NotificationService extends ApiClient {
  async getAll(): Promise<any[]> {
    const response = await this.request<any[]>('/notifications/feed?limit=50');

    // Transform backend response to frontend format
    return response.map((notif: any) => ({
      id: notif.id.toString(),
      title: this.generateTitle(notif.data_type, notif.change_type),
      message: notif.summary,
      type: this.mapChangeTypeToNotificationType(notif.change_type),
      read: notif.is_read,
      created_at: notif.created_at
    }));
  }

  async getUnreadCount(): Promise<{ count: number }> {
    const response = await this.request<any>('/notifications/unread-count');
    return { count: response.unread_count || 0 };
  }

  async markAsRead(id: string): Promise<void> {
    await this.request(`/notifications/mark-read/${id}`, {
      method: 'POST',
    });
  }

  async markAllAsRead(): Promise<void> {
    await this.request('/notifications/mark-all-read', {
      method: 'POST',
    });
  }

  async delete(id: string): Promise<void> {
    // Backend doesn't have delete endpoint for FBR notifications
    // FBR notifications are system-wide and auto-cleaned after 2 days
    // Just mark as read instead
    await this.markAsRead(id);
  }

  // Helper methods to transform backend data
  private generateTitle(dataType: string, changeType: string): string {
    const typeMap: { [key: string]: string } = {
      'provinces': 'Province',
      'uom': 'UOM',
      'hs_codes': 'HS Code',
      'tax_rates': 'Tax Rate',
      'transaction_types': 'Transaction Type',
      'sro_schedules': 'SRO Schedule',
      'sale_types': 'Sale Type',
      'registration_types': 'Registration Type',
      'invoice_types': 'Invoice Type'
    };

    const changeMap: { [key: string]: string } = {
      'added': 'Added',
      'modified': 'Updated',
      'deleted': 'Removed'
    };

    const type = typeMap[dataType] || dataType;
    const change = changeMap[changeType] || changeType;

    return `FBR ${type} ${change}`;
  }

  private mapChangeTypeToNotificationType(changeType: string): 'info' | 'success' | 'warning' | 'error' {
    switch (changeType) {
      case 'added':
        return 'info';
      case 'modified':
        return 'warning';
      case 'deleted':
        return 'error';
      default:
        return 'info';
    }
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

  async updateFbrCredentials(credentials: {
    fbr_sandbox_token?: string;
    fbr_production_token?: string;
    fbr_system_sync_token?: string;
  }): Promise<{ success: boolean; message: string }> {
    return this.request('/auth/profile/fbr-credentials', {
      method: 'PUT',
      body: JSON.stringify(credentials),
    });
  }

  // Profile Management
  async getUserProfile(): Promise<any> {
    return this.request('/profile');
  }

  async updateUserProfile(data: {
    name?: string;
    fbr_seller_ntn?: string;
    fbr_business_name?: string;
    fbr_seller_province?: string;
    fbr_seller_address?: string;
  }): Promise<any> {
    return this.request('/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getSellerInfo(): Promise<{
    seller_ntn_cnic: string;
    seller_business_name: string;
    seller_province: string;
    seller_address: string;
    is_complete: boolean;
  }> {
    return this.request('/profile/seller-info');
  }

  // Saved Products Management
  async getSavedProducts(activeOnly: boolean = true): Promise<any[]> {
    const params = new URLSearchParams();
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    return this.request(`/profile/saved-products?${params.toString()}`);
  }

  async getSavedProduct(id: number): Promise<any> {
    return this.request(`/profile/saved-products/${id}`);
  }

  async createSavedProduct(data: {
    hs_code: string;
    product_description: string;
    default_uom?: string;
    default_rate?: string;
    default_sale_type?: string;
    default_unit_price?: number;
    display_order?: number;
  }): Promise<any> {
    return this.request('/profile/saved-products', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSavedProduct(id: number, data: {
    hs_code?: string;
    product_description?: string;
    default_uom?: string;
    default_rate?: string;
    default_sale_type?: string;
    default_unit_price?: number;
    display_order?: number;
    is_active?: number;
  }): Promise<any> {
    return this.request(`/profile/saved-products/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSavedProduct(id: number, hardDelete: boolean = false): Promise<{ message: string }> {
    const params = new URLSearchParams();
    if (hardDelete) {
      params.append('hard_delete', 'true');
    }
    return this.request(`/profile/saved-products/${id}?${params.toString()}`, {
      method: 'DELETE',
    });
  }

  async reorderSavedProducts(productIds: number[]): Promise<{ message: string }> {
    return this.request('/profile/saved-products/reorder', {
      method: 'POST',
      body: JSON.stringify(productIds),
    });
  }

  // Saved HS Codes Management
  async getSavedHSCodes(activeOnly: boolean = true): Promise<any[]> {
    const params = new URLSearchParams();
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    return this.request(`/profile/saved-hs-codes?${params.toString()}`);
  }

  async createSavedHSCode(data: { hs_code: string }): Promise<any> {
    return this.request('/profile/saved-hs-codes', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSavedHSCode(id: number, data: { hs_code: string }): Promise<any> {
    return this.request(`/profile/saved-hs-codes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSavedHSCode(id: number): Promise<{ message: string }> {
    return this.request(`/profile/saved-hs-codes/${id}`, {
      method: 'DELETE',
    });
  }

  // Saved Product Descriptions Management
  async getSavedProductDescriptions(activeOnly: boolean = true): Promise<any[]> {
    const params = new URLSearchParams();
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    return this.request(`/profile/saved-product-descriptions?${params.toString()}`);
  }

  async createSavedProductDescription(data: { product_description: string }): Promise<any> {
    return this.request('/profile/saved-product-descriptions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSavedProductDescription(id: number, data: { product_description: string }): Promise<any> {
    return this.request(`/profile/saved-product-descriptions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSavedProductDescription(id: number): Promise<{ message: string }> {
    return this.request(`/profile/saved-product-descriptions/${id}`, {
      method: 'DELETE',
    });
  }

  // Saved UOMs Management
  async getSavedUOMs(activeOnly: boolean = true): Promise<any[]> {
    const params = new URLSearchParams();
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    return this.request(`/profile/saved-uoms?${params.toString()}`);
  }

  async createSavedUOM(data: { uom_code: string; uom_name: string }): Promise<any> {
    return this.request('/profile/saved-uoms', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSavedUOM(id: number, data: { uom_code: string; uom_name: string }): Promise<any> {
    return this.request(`/profile/saved-uoms/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSavedUOM(id: number): Promise<{ message: string }> {
    return this.request(`/profile/saved-uoms/${id}`, {
      method: 'DELETE',
    });
  }

  // Saved Tax Rates Management
  async getSavedTaxRates(activeOnly: boolean = true): Promise<any[]> {
    const params = new URLSearchParams();
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    return this.request(`/profile/saved-tax-rates?${params.toString()}`);
  }

  async createSavedTaxRate(data: { tax_rate: string; description?: string }): Promise<any> {
    return this.request('/profile/saved-tax-rates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSavedTaxRate(id: number, data: { tax_rate: string; description?: string }): Promise<any> {
    return this.request(`/profile/saved-tax-rates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSavedTaxRate(id: number): Promise<{ message: string }> {
    return this.request(`/profile/saved-tax-rates/${id}`, {
      method: 'DELETE',
    });
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

  // Parameterized APIs - REMOVED: Data is synced to local DB at 6am daily
  // These methods now return empty arrays to prevent runtime FBR API calls
  // All data should be fetched from local database via getAllMasterData()

  async getSroSchedule(rateId: number, date: string, originationSupplierCsv: number): Promise<Array<{id: string, description: string}>> {
    return [];
  }

  async getSaleTypeToRate(date: string, transTypeId: number, originationSupplier: number): Promise<any[]> {
    return [];
  }

  async getHsUom(hsCode: string, annexureId: number): Promise<Array<{code: string, name: string}>> {
    return [];
  }

  async getSroItemDetails(date: string, sroId: number): Promise<any[]> {
    return [];
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
  // REMOVED: Buyer verification causes performance issues during peak times
  // Users should manually select registration type
  async verifyBuyer(ntnCnic: string, environment: string = 'SANDBOX'): Promise<BuyerVerificationResponse> {
    return {
      success: false,
      registration_type: 'Registered',
      is_registered: false,
      error: 'Buyer verification disabled for performance - please select registration type manually'
    };
  }

  // REMOVED: HS code descriptions are synced to local DB at 6am daily
  async getHSCodeDescription(hsCode: string): Promise<{ hs_code: string; description: string | null; found: boolean; message?: string }> {
    return {
      hs_code: hsCode,
      description: null,
      found: false,
      message: 'HS code descriptions available in local database'
    };
  }
}

// Export singleton instances
export const authService = new AuthService();
export const invoiceService = new InvoiceService();
export const userService = new UserService();
export const masterDataService = new MasterDataService();
export const fbrIntegrationService = new FBRIntegrationService();
export const notificationService = new NotificationService();