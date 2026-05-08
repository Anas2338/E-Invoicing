// Use environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

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

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  };

  // Add CSRF token for state-changing requests
  // Try cookie first, then sessionStorage (for cross-origin scenarios)
  const method = options.method?.toUpperCase() || 'GET';
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrfToken = getCookie('csrf_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('csrf_token') : null);
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: 'include', // Important: send httpOnly cookies with request
  });

  if (!response.ok) {
    // Handle 401 Unauthorized - token expired or invalid
    if (response.status === 401) {
      // SECURITY: No localStorage usage - redirect to login
      // The auth provider will handle clearing React state
      window.location.href = '/login';
      throw new ApiError(401, 'Session expired. Please login again.');
    }

    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new ApiError(response.status, errorData.error || errorData.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  // Invoice endpoints
  invoices: {
    list: async (params?: {
      status?: string;
      page?: number;
      size?: number;
    }) => {
      const queryParams = new URLSearchParams();
      if (params?.status) queryParams.append('status', params.status);
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.size) queryParams.append('size', params.size.toString());

      const query = queryParams.toString();
      return fetchWithAuth(`/invoices${query ? `?${query}` : ''}`);
    },

    get: async (id: string) => {
      return fetchWithAuth(`/invoices/${id}`);
    },

    create: async (data: any) => {
      return fetchWithAuth('/invoices', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    update: async (id: string, data: any) => {
      return fetchWithAuth(`/invoices/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    delete: async (id: string) => {
      return fetchWithAuth(`/invoices/${id}`, {
        method: 'DELETE',
      });
    },

    getHistory: async (id: string) => {
      return fetchWithAuth(`/invoices/${id}/history`);
    },

    validate: async (id: string) => {
      return fetchWithAuth(`/invoices/${id}/validate`, {
        method: 'POST',
      });
    },

    post: async (id: string) => {
      return fetchWithAuth(`/invoices/${id}/post`, {
        method: 'POST',
      });
    },

    getUnifiedHistory: async (params?: {
      source?: string;
      status?: string;
      date_from?: string;
      date_to?: string;
      page?: number;
      page_size?: number;
    }) => {
      const queryParams = new URLSearchParams();
      if (params?.source) queryParams.append('source', params.source);
      if (params?.status) queryParams.append('status', params.status);
      if (params?.date_from) queryParams.append('date_from', params.date_from);
      if (params?.date_to) queryParams.append('date_to', params.date_to);
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

      const query = queryParams.toString();
      return fetchWithAuth(`/invoices/unified-history${query ? `?${query}` : ''}`);
    },

    getBuyersFromHistory: async (search?: string) => {
      const queryParams = new URLSearchParams();
      if (search) queryParams.append('search', search);

      const query = queryParams.toString();
      return fetchWithAuth(`/invoices/buyers-from-history${query ? `?${query}` : ''}`);
    },

    bulkPdf: async (invoiceIds: string[]) => {
      return fetchWithAuth('/invoices/bulk-pdf', {
        method: 'POST',
        body: JSON.stringify(invoiceIds),
      });
    },
  },

  // Dashboard endpoints
  dashboard: {
    getStats: async () => {
      return fetchWithAuth('/dashboard/stats');
    },
  },

  // Auth endpoints
  auth: {
    getProfile: async () => {
      return fetchWithAuth('/auth/profile');
    },

    getPermissions: async () => {
      return fetchWithAuth('/auth/permissions');
    },

    getFbrCredentials: async () => {
      return fetchWithAuth('/auth/profile/fbr-credentials');
    },

    updateFbrCredentials: async (credentials: any) => {
      return fetchWithAuth('/auth/profile/fbr-credentials', {
        method: 'PUT',
        body: JSON.stringify(credentials),
      });
    },

    deleteFbrCredentials: async (environment?: string) => {
      const url = environment
        ? `/auth/profile/fbr-credentials?environment=${environment}`
        : '/auth/profile/fbr-credentials';
      return fetchWithAuth(url, {
        method: 'DELETE',
      });
    },

    getSavedProducts: async (activeOnly: boolean = true) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      return fetchWithAuth(`/profile/saved-products?${params.toString()}`);
    },

    createSavedProduct: async (data: {
      item_code: string;
      item_name: string;
      hs_code: string;
      product_description: string;
      default_uom?: string;
      default_rate?: string;
      default_sale_type?: string;
      transaction_type?: string;
      default_unit_price?: number;
      sro_schedule_no?: string;
      sro_item_serial_no?: string;
    }) => {
      return fetchWithAuth('/profile/saved-products', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    updateSavedProduct: async (id: number, data: {
      item_code?: string;
      item_name?: string;
      hs_code?: string;
      product_description?: string;
      default_uom?: string;
      default_rate?: string;
      default_sale_type?: string;
      transaction_type?: string;
      default_unit_price?: number;
      sro_schedule_no?: string;
      sro_item_serial_no?: string;
    }) => {
      return fetchWithAuth(`/profile/saved-products/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    deleteSavedProduct: async (id: number) => {
      return fetchWithAuth(`/profile/saved-products/${id}`, {
        method: 'DELETE',
      });
    },

    bulkDeleteSavedProducts: async (ids: number[]) => {
      return fetchWithAuth('/profile/saved-products/bulk-delete', {
        method: 'POST',
        body: JSON.stringify(ids),
      });
    },

    downloadSavedProductsTemplate: async () => {
      const headers: Record<string, string> = {};

      const response = await fetch(`${API_BASE_URL}/profile/saved-products/template/download`, {
        method: 'GET',
        headers,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new ApiError(response.status, 'Failed to download template');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'saved_items_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },

    uploadSavedProducts: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);

      const headers: Record<string, string> = {};

      // Add CSRF token
      const csrfToken = getCookie('csrf_token') || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('csrf_token') : null);
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      const response = await fetch(`${API_BASE_URL}/profile/saved-products/upload`, {
        method: 'POST',
        headers,
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 401) {
          window.location.href = '/login';
          throw new ApiError(401, 'Session expired. Please login again.');
        }
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new ApiError(response.status, errorData.error || errorData.detail || 'Upload failed');
      }

      return response.json();
    },

    getSavedHSCodes: async (activeOnly: boolean = true) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      return fetchWithAuth(`/profile/saved-hs-codes?${params.toString()}`);
    },

    getSavedProductDescriptions: async (activeOnly: boolean = true) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      return fetchWithAuth(`/profile/saved-product-descriptions?${params.toString()}`);
    },

    getSavedUOMs: async (activeOnly: boolean = true) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      return fetchWithAuth(`/profile/saved-uoms?${params.toString()}`);
    },

    getSavedTaxRates: async (activeOnly: boolean = true) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      return fetchWithAuth(`/profile/saved-tax-rates?${params.toString()}`);
    },

    getSavedBuyers: async (activeOnly: boolean = true, search?: string) => {
      const params = new URLSearchParams();
      if (activeOnly) {
        params.append('active_only', 'true');
      }
      if (search) {
        params.append('search', search);
      }
      return fetchWithAuth(`/profile/saved-buyers?${params.toString()}`);
    },

    createSavedBuyer: async (data: {
      buyer_ntn_cnic: string;
      buyer_business_name: string;
      buyer_province?: string;
      buyer_address?: string;
      buyer_registration_type?: string;
    }) => {
      return fetchWithAuth('/profile/saved-buyers', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    updateSavedBuyer: async (id: number, data: {
      buyer_ntn_cnic?: string;
      buyer_business_name?: string;
      buyer_province?: string;
      buyer_address?: string;
      buyer_registration_type?: string;
    }) => {
      return fetchWithAuth(`/profile/saved-buyers/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    deleteSavedBuyer: async (id: number) => {
      return fetchWithAuth(`/profile/saved-buyers/${id}`, {
        method: 'DELETE',
      });
    },

    getNextInvoiceNumber: async () => {
      return fetchWithAuth('/profile/next-invoice-number');
    },

    updateInvoiceSettings: async (settings: {
      invoice_prefix?: string;
      invoice_start_number?: number;
      invoice_padding?: number;
      invoice_include_year?: boolean;
    }) => {
      return fetchWithAuth('/profile/invoice-settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      });
    },
  },
};

export { ApiError };
