'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useActivityTimeout } from '@/hooks/useActivityTimeout';
import { toast } from 'sonner';

// API Base URL - use relative path to leverage Next.js proxy
const API_BASE_URL = '/api/v1';

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
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<{status?: string; message?: string} | void>;
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
        // With httpOnly cookies, we can't check the token directly
        // Instead, try to fetch user profile from the API
        // The cookie will be sent automatically
        const response = await fetch(`${API_BASE_URL}/auth/profile`, {
          method: 'GET',
          credentials: 'include', // Important: send cookies with request
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          // Optionally store user data in localStorage for quick access
          localStorage.setItem('user', JSON.stringify(userData));
        } else {
          // Not authenticated or token expired
          setUser(null);
          localStorage.removeItem('user');
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
        setUser(null);
        localStorage.removeItem('user');
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
        console.error('Login error:', errorData);
        setLoading(false);
        throw new Error(errorData.detail || errorData.error || 'Invalid credentials');
      }

      const data = await response.json();

      // With httpOnly cookies, token is set automatically by the browser
      // We only need to store user data and CSRF token
      if (data.user) {
        setUser(data.user);
        localStorage.setItem('user', JSON.stringify(data.user));
      }

      // Store CSRF token for cross-origin requests
      if (data.csrf_token) {
        localStorage.setItem('csrf_token', data.csrf_token);
      }

      await new Promise(resolve => setTimeout(resolve, 100));

      window.location.href = '/dashboard';

    } catch (error) {
      console.error('Sign in error:', error);
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
        credentials: 'include', // Important: receive and send cookies
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
        if (data.user) {
          setUser(data.user);
          localStorage.setItem('user', JSON.stringify(data.user));
          router.push('/dashboard');
        }
      } else {
        throw new Error(data.detail || data.error || 'Registration failed');
      }
    } catch (error) {
      console.error('Sign up error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      // Get CSRF token from cookie
      const getCookie = (name: string): string | null => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
          return parts.pop()?.split(';').shift() || null;
        }
        return null;
      };

      const csrfToken = getCookie('csrf_token');
      const headers: Record<string, string> = {};
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      // Call backend logout endpoint to clear httpOnly cookies
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include', // Important: send cookies to be cleared
        headers,
      });
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      setUser(null);
      localStorage.removeItem('user');
      localStorage.removeItem('csrf_token');
      router.push('/login');
    }
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