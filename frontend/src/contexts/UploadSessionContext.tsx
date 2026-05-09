'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { automationApi } from '@/services/automationApi';

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

  // Load sessions from localStorage on mount
  useEffect(() => {
    const savedSessions = localStorage.getItem(STORAGE_KEY);
    if (savedSessions) {
      try {
        const sessions = JSON.parse(savedSessions);
        // Filter out completed/failed sessions older than 5 minutes
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
        const activeSessions = sessions.filter((session: UploadProgress) => {
          if (session.status === 'processing' || session.status === 'uploading') {
            return true;
          }
          const startedAt = new Date(session.startedAt).getTime();
          return startedAt > fiveMinutesAgo;
        });
        setActiveSessions(activeSessions);
      } catch (err) {
        console.error('Error loading saved sessions:', err);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

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
        } catch (err) {
          console.error(`Error polling session ${session.sessionId}:`, err);
          return session;
        }
      })
    );

    setActiveSessions(updatedSessions);

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
