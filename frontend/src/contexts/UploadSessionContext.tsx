'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { automationApi } from '@/services/automationApi';
import { useAuth } from '@/providers/auth-provider';

interface UploadProgress {
  sessionId: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  processedRows: number;
  totalRows: number;
  validatedCount: number;
  failedCount: number;
  expiredCount: number;
  pendingCount: number;
  progressPercentage: number;
  errorMessage?: string;
  startedAt: string;
}

interface UploadSessionContextType {
  activeSessions: UploadProgress[];
  startSession: (sessionId: string, totalRows: number) => void;
  removeSession: (sessionId: string) => void;
  hasActiveSessions: boolean;
}

const UploadSessionContext = createContext<UploadSessionContextType | undefined>(undefined);

const STORAGE_KEY = 'active_upload_sessions';
const POLL_INTERVAL = 3000; // 3 seconds

export function UploadSessionProvider({ children }: { children: React.ReactNode }) {
  const [activeSessions, setActiveSessions] = useState<UploadProgress[]>([]);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { isAuthenticated } = useAuth();
  const backendRecoveryDone = useRef(false);

  // Load sessions from localStorage on mount (immediate, before auth check)
  useEffect(() => {
    const savedSessions = localStorage.getItem(STORAGE_KEY);
    if (savedSessions) {
      try {
        const sessions: UploadProgress[] = JSON.parse(savedSessions);
        // Keep processing/uploading sessions; filter out completed/failed older than 5 min
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
        const active = sessions.filter((session) => {
          if (session.status === 'processing' || session.status === 'uploading') {
            return true;
          }
          const startedAt = new Date(session.startedAt).getTime();
          return startedAt > fiveMinutesAgo;
        });
        if (active.length > 0) {
          setActiveSessions(active);
        }
      } catch (err) {
        console.error('Error loading saved sessions:', err);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Recover in-progress sessions from backend after authentication is confirmed.
  // This handles the case where the user logged out, processing continued server-side,
  // and the user logged back in — localStorage may be stale or missing.
  useEffect(() => {
    if (!isAuthenticated || backendRecoveryDone.current) return;
    backendRecoveryDone.current = true;

    let cancelled = false;

    const recoverFromBackend = async () => {
      try {
        const response = await automationApi.getUploadSessions();
        const processingSessions = response.sessions.filter(
          (s) => s.processing_status === 'processing'
        );

        if (processingSessions.length === 0) return;

        setActiveSessions((prev) => {
          const existing = new Set(prev.map((s) => s.sessionId));
          const newSessions: UploadProgress[] = [];

          for (const s of processingSessions) {
            if (!existing.has(s.id)) {
              newSessions.push({
                sessionId: s.id,
                status: 'processing',
                processedRows: s.processed_rows || 0,
                totalRows: s.total_rows || s.total_count,
                validatedCount: s.validated_count || 0,
                failedCount: s.failed_count || 0,
                expiredCount: s.expired_count || 0,
                pendingCount: s.pending_count || 0,
                progressPercentage:
                  s.total_rows > 0
                    ? ((s.processed_rows || 0) / s.total_rows) * 100
                    : 0,
                errorMessage: s.error_message,
                startedAt: s.uploaded_at,
              });
            }
          }

          if (newSessions.length === 0) return prev;
          return [...prev, ...newSessions];
        });
      } catch {
        // Silently ignore — if not authenticated or network error, we'll keep
        // whatever localStorage had
      }
    };

    recoverFromBackend();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    if (activeSessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(activeSessions));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [activeSessions]);

  // Poll for status updates
  const pollSessions = useCallback(async () => {
    if (activeSessions.length === 0) return;

    const updatedSessions = await Promise.all(
      activeSessions.map(async (session) => {
        // Skip polling for completed/failed sessions
        if (session.status === 'completed' || session.status === 'failed') {
          return session;
        }

        try {
          const status = await automationApi.getUploadStatus(session.sessionId);

          return {
            sessionId: status.session_id,
            status: status.status,
            processedRows: status.processed_rows,
            totalRows: status.total_rows,
            validatedCount: status.validated_count || 0,
            failedCount: status.failed_count || 0,
            expiredCount: status.expired_count || 0,
            pendingCount: status.pending_count || 0,
            progressPercentage: status.progress_percentage || 0,
            errorMessage: status.error_message,
            startedAt: session.startedAt
          };
        } catch (err: any) {
          // 404: session no longer exists — mark for removal
          if (err?.message?.includes('not found') || err?.status === 404) {
            return null; // will be filtered out below
          }
          // 401/403: auth error (e.g. logged out) — keep session as-is, will be
          // recovered when user logs back in and backendRecovery effect fires
          if (err?.message?.includes('Unauthorized') || err?.status === 401 ||
              err?.message?.includes('Forbidden') || err?.status === 403) {
            return session;
          }
          console.error(`Error polling session ${session.sessionId}:`, err);
          return session;
        }
      })
    );

    // Remove sessions that returned 404 (no longer exist)
    const filtered = updatedSessions.filter((s): s is NonNullable<typeof s> => s !== null);
    setActiveSessions(filtered);

    // Auto-remove completed/failed sessions after 10 seconds
    setTimeout(() => {
      setActiveSessions(prev =>
        prev.filter(s => s.status !== 'completed' && s.status !== 'failed')
      );
    }, 10000);
  }, [activeSessions]);

  // Start polling when there are active sessions
  useEffect(() => {
    if (activeSessions.length > 0) {
      pollIntervalRef.current = setInterval(pollSessions, POLL_INTERVAL);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [activeSessions.length, pollSessions]);

  const startSession = useCallback((sessionId: string, totalRows: number) => {
    const newSession: UploadProgress = {
      sessionId,
      status: 'processing',
      processedRows: 0,
      totalRows,
      validatedCount: 0,
      failedCount: 0,
      expiredCount: 0,
      pendingCount: totalRows,
      progressPercentage: 0,
      startedAt: new Date().toISOString()
    };

    setActiveSessions(prev => {
      // Remove any existing session with same ID
      const filtered = prev.filter(s => s.sessionId !== sessionId);
      return [...filtered, newSession];
    });
  }, []);

  const removeSession = useCallback((sessionId: string) => {
    setActiveSessions(prev => prev.filter(s => s.sessionId !== sessionId));
  }, []);

  const hasActiveSessions = activeSessions.some(
    s => s.status === 'processing' || s.status === 'uploading'
  );

  return (
    <UploadSessionContext.Provider
      value={{
        activeSessions,
        startSession,
        removeSession,
        hasActiveSessions
      }}
    >
      {children}
    </UploadSessionContext.Provider>
  );
}

export function useUploadSession() {
  const context = useContext(UploadSessionContext);
  if (context === undefined) {
    throw new Error('useUploadSession must be used within UploadSessionProvider');
  }
  return context;
}
