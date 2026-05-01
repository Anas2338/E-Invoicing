import { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface UseActivityTimeoutOptions {
  timeoutMinutes?: number;
  warningMinutes?: number;
  onWarning?: () => void;
  onTimeout?: () => void;
}

/**
 * Hook to track user activity and auto-logout after inactivity period.
 *
 * @param timeoutMinutes - Minutes of inactivity before auto-logout (default: 30)
 * @param warningMinutes - Minutes before timeout to show warning (default: 5)
 * @param onWarning - Callback when warning threshold is reached
 * @param onTimeout - Callback when timeout is reached (before logout)
 */
export function useActivityTimeout({
  timeoutMinutes = 30,
  warningMinutes = 5,
  onWarning,
  onTimeout
}: UseActivityTimeoutOptions = {}) {
  const router = useRouter();
  const lastActivityRef = useRef<number>(Date.now());
  const warningShownRef = useRef<boolean>(false);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const timeoutMs = timeoutMinutes * 60 * 1000;
  const warningMs = (timeoutMinutes - warningMinutes) * 60 * 1000;

  // Update last activity timestamp
  const updateActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
    warningShownRef.current = false;
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    // Call backend logout endpoint to clear httpOnly cookies
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

      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers,
      });
    } catch (error) {
      // Logout error - continue anyway
    }

    // SECURITY: No localStorage usage - user data is only in React state (memory)

    // Call onTimeout callback if provided
    if (onTimeout) {
      onTimeout();
    }

    // Redirect to login
    router.push('/login');
  }, [router, onTimeout]);

  // Check for inactivity
  const checkInactivity = useCallback(() => {
    const now = Date.now();
    const timeSinceLastActivity = now - lastActivityRef.current;

    // Check if timeout reached
    if (timeSinceLastActivity >= timeoutMs) {
      logout();
      return;
    }

    // Check if warning threshold reached
    if (timeSinceLastActivity >= warningMs && !warningShownRef.current) {
      warningShownRef.current = true;
      if (onWarning) {
        onWarning();
      }
    }
  }, [timeoutMs, warningMs, logout, onWarning]);

  useEffect(() => {
    // Activity event types to track
    const events = [
      'mousedown',
      'mousemove',
      'keydown',
      'scroll',
      'touchstart',
      'click'
    ];

    // Add event listeners
    events.forEach(event => {
      document.addEventListener(event, updateActivity, { passive: true });
    });

    // Start checking for inactivity every 30 seconds
    checkIntervalRef.current = setInterval(checkInactivity, 30000);

    // Initial activity timestamp
    updateActivity();

    // Cleanup
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity);
      });

      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
    };
  }, [updateActivity, checkInactivity]);

  return {
    updateActivity,
    logout
  };
}
