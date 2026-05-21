'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useActivityTimeout } from '@/hooks/useActivityTimeout';
import { toast } from 'sonner';

// API Base URL - use environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

// Define types
interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  approval_flags?: {
    has_production_access?: boolean;
    can_post_to_production?: boolean;
  };
  has_production_access?: boolean;
  can_post_to_production?: boolean;
  automation_enabled?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string, pin: string) => Promise<{status?: string; message?: string} | void>;
  signOut: () => Promise<void>;
  isAuthenticated: boolean;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Activity-based timeout (30 minutes of inactivity)
  useActivityTimeout({
    timeoutMinutes: 30,
    warningMinutes: 5,
    onWarning: () => {
      // Show warning toast 5 minutes before timeout
      if (user) {
        toast.warning('Session Expiring Soon', {
          description: 'You will be logged out in 5 minutes due to inactivity.',
          duration: 10000,
        });
      }
    },
    onTimeout: () => {
      // Show timeout toast when logging out
      if (user) {
        toast.error('Session Expired', {
          description: 'You have been logged out due to inactivity.',
          duration: 5000,
        });
      }
    }
  });

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/profile`, {
          method: 'GET',
          credentials: 'include',
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          setUser(null);
        }
      } catch (error) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  const signIn = async (email: string, password: string) => {
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // Important: receive and send cookies
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Login failed' }));
        setLoading(false);
        throw new Error(errorData.detail || errorData.error || 'Invalid credentials');
      }

      const data = await response.json();

      // SECURITY: With httpOnly cookies, token is set automatically by the browser
      // We only store user data in React state (memory), NOT localStorage
      if (data.user) {
        setUser(data.user);
      }

      // SECURITY: Store CSRF token in sessionStorage (not localStorage)
      // sessionStorage is cleared when tab closes, more secure than localStorage
      // Needed for cross-origin requests where cookie isn't accessible to JavaScript
      if (data.csrf_token) {
        sessionStorage.setItem('csrf_token', data.csrf_token);
      }

      // SECURITY: Store access token in sessionStorage for cross-origin API calls
      // The httpOnly cookie can't be sent to other ports (AI-agent on 8002),
      // so we include the token in Authorization header for cross-service requests
      if (data.access_token) {
        sessionStorage.setItem('access_token', data.access_token);
      }

      await new Promise(resolve => setTimeout(resolve, 100));

      window.location.href = '/dashboard';

    } catch (error) {
      setLoading(false);
      throw error;
    }
  };

  const signUp = async (email: string, password: string, name: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password, name }),
      });

      const data = await response.json();

      if (response.ok) {
        // Check if registration requires approval
        if (data.status === 'pending_approval') {
          // Don't set user, just return success message
          setLoading(false);
          return data; // Return the response data with message
        }

        // Auto-approved: user data is returned
        // SECURITY: Store only in React state (memory), NOT localStorage
        if (data.user) {
          setUser(data.user);
          router.push('/dashboard');
        }
      } else {
        throw new Error(data.detail || data.error || 'Registration failed');
      }
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    // SECURITY: Clear React state immediately to prevent UI from showing authenticated state
    setUser(null);

    try {
      // Get CSRF token from cookie or sessionStorage
      const getCookie = (name: string): string | null => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
          return parts.pop()?.split(';').shift() || null;
        }
        return null;
      };

      const csrfToken = getCookie('csrf_token') || sessionStorage.getItem('csrf_token');
      const headers: Record<string, string> = {};
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      // CRITICAL: Call backend logout endpoint and WAIT for it to complete
      // This increments token_version on the server, invalidating all tokens
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers,
      });

      // Clear all cookies manually (may not work in cross-origin, but try anyway)
      const clearCookie = (name: string) => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; secure; samesite=none;`;
      };

      clearCookie('access_token');
      clearCookie('refresh_token');
      clearCookie('csrf_token');

      // Clear CSRF token and access token from sessionStorage
      sessionStorage.removeItem('csrf_token');
      sessionStorage.removeItem('access_token');

    } catch (error) {
      // Continue with logout even if backend call fails
    }

    // Set timestamp to prevent immediate re-authentication on next page load
    // This timestamp is checked in the auth status check
    sessionStorage.setItem('logout_timestamp', Date.now().toString());

    // CRITICAL: Use window.location.href for hard redirect
    // This clears all React state and forces a fresh page load
    window.location.href = '/login';
  };

  const value = {
    user,
    loading,
    signIn,
    signUp,
    signOut,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use the auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}