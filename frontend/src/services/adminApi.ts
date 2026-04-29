/**
 * Admin API client for user management and approval.
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

export interface PendingUser {
  id: string;
  email: string;
  name: string;
  created_at: string;
  account_status: string;
  automation_enabled: boolean;
}

export interface UserListResponse {
  total: number;
  users: PendingUser[];
}

class AdminApiClient {
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

    // Add CSRF token
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  }

  /**
   * Get all pending users.
   */
  async getPendingUsers(): Promise<UserListResponse> {
    const response = await fetch(`${this.baseUrl}/admin/users/pending`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get pending users');
    }

    return response.json();
  }

  /**
   * Get all users with optional status filter.
   */
  async getAllUsers(statusFilter?: string): Promise<UserListResponse> {
    const url = statusFilter
      ? `${this.baseUrl}/admin/users/all?status_filter=${statusFilter}`
      : `${this.baseUrl}/admin/users/all`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get users');
    }

    return response.json();
  }

  /**
   * Approve a user account.
   */
  async approveUser(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/users/${userId}/approve`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to approve user');
    }

    return response.json();
  }

  /**
   * Reject a user account.
   */
  async rejectUser(userId: string, reason?: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/users/${userId}/reject`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ reason: reason || 'No reason provided' }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to reject user');
    }

    return response.json();
  }

  /**
   * Delete a user account.
   */
  async deleteUser(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/users/${userId}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete user');
    }

    return response.json();
  }

  /**
   * Toggle automation access for a user.
   */
  async toggleAutomationAccess(userId: string, enabled: boolean): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/users/${userId}/toggle-automation`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ enabled }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to toggle automation access');
    }

    return response.json();
  }

  /**
   * Manually trigger FBR master data sync.
   */
  async triggerSync(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/sync/trigger`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to trigger sync');
    }

    return response.json();
  }

  /**
   * Get FBR sync status and recent history.
   */
  async getSyncStatus(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/sync/status`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get sync status');
    }

    return response.json();
  }

  /**
   * Get FBR sync logs.
   */
  async getSyncLogs(limit: number = 50): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/sync/logs?limit=${limit}`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get sync logs');
    }

    return response.json();
  }
}

// Export singleton instance
export const adminApi = new AdminApiClient();
