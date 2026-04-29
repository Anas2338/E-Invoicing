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
  const method = options.method?.toUpperCase() || 'GET';
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrfToken = getCookie('csrf_token');
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
      localStorage.removeItem('user');
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
