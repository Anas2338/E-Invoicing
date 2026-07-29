'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StagingRow {
  id: string;
  excel_row_number: number;
  group_key: string;
  is_valid: boolean;
  is_dirty: boolean;
  field_errors: Record<string, string[]>;
  [key: string]: any;
}

interface StagingSession {
  session_id: string;
  status: string;
  original_filename: string;
  total_rows: number;
  valid_rows: number;
  errored_rows: number;
  created_at: string;
  updated_at: string;
}

interface StagingSessionDetail extends StagingSession {
  rows: StagingRow[];
}

interface ExcelStagingContextType {
  /** Current active staging session (null = none active) */
  activeSessions: StagingSession[];
  /** Rows from the current session (if loaded) */
  rows: StagingRow[];
  /** Current session detail (null = not loaded) */
  currentSession: StagingSessionDetail | null;
  /** Processing state for UI feedback */
  isProcessing: boolean;
  /** Processing status text */
  processingText: string;
  /** Error message if something went wrong */
  error: string | null;

  /** Upload an Excel file and create a staging session */
  uploadFile: (file: File) => Promise<void>;
  /** Update a single cell on a row */
  updateCell: (rowId: string, field: string, value: any) => Promise<void>;
  /** Re-validate all dirty rows */
  recheckSession: () => Promise<void>;
  /** Create DRAFT invoices from all valid rows */
  commitSession: () => Promise<void>;
  /** Cancel and delete the current session */
  cancelSession: () => Promise<void>;
  /** Refresh session data from backend */
  refreshSession: () => Promise<void>;
  /** Clear current session (after commit/cancel) */
  clearSession: () => void;
  /** Load a specific session by ID */
  loadSession: (sessionId: string) => Promise<void>;
}

const ExcelStagingContext = createContext<ExcelStagingContextType | undefined>(undefined);

const POLL_INTERVAL = 3000; // 3 seconds
const STORAGE_KEY_PREFIX = 'excel_staging_session_';

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function ExcelStagingProvider({ children }: { children: React.ReactNode }) {
  const [activeSessions, setActiveSessions] = useState<StagingSession[]>([]);
  const [currentSession, setCurrentSession] = useState<StagingSessionDetail | null>(null);
  const [rows, setRows] = useState<StagingRow[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingText, setProcessingText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { user, isAuthenticated } = useAuth();
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const backendRecoveryDone = useRef(false);

  const storageKey = user?.id ? `${STORAGE_KEY_PREFIX}${user.id}` : null;

  // -----------------------------------------------------------------------
  // Persistence helpers
  // -----------------------------------------------------------------------

  const saveSessionId = useCallback((sessionId: string | null) => {
    if (storageKey) {
      if (sessionId) {
        localStorage.setItem(storageKey, sessionId);
      } else {
        localStorage.removeItem(storageKey);
      }
    }
  }, [storageKey]);

  const getSavedSessionId = useCallback((): string | null => {
    if (!storageKey) return null;
    return localStorage.getItem(storageKey);
  }, [storageKey]);

  // -----------------------------------------------------------------------
  // Backend recovery on mount (after auth)
  // -----------------------------------------------------------------------

  useEffect(() => {
    if (!isAuthenticated || backendRecoveryDone.current) return;
    backendRecoveryDone.current = true;

    const recover = async () => {
      try {
        const savedId = getSavedSessionId();
        const resp = await api.excelStaging.getActiveSessions();
        const sessions = resp.sessions || [];

        if (sessions.length > 0) {
          setActiveSessions(sessions);
          // If we have a saved session ID matching an active session, load it
          const match = sessions.find(s => s.session_id === savedId) || sessions[0];
          saveSessionId(match.session_id);
          // Load the full session detail (including rows)
          setIsProcessing(true);
          setProcessingText('Restoring session...');
          try {
            const detail = await api.excelStaging.getSession(match.session_id);
            if (detail && detail.rows) {
              setCurrentSession(detail);
              setRows(detail.rows);
            }
          } catch {
            // Non-fatal — grid will show "No rows" until user resumes
          } finally {
            setIsProcessing(false);
            setProcessingText('');
          }
        } else if (savedId) {
          // Try loading the saved session directly (for "active" but not returned)
          try {
            const detail = await api.excelStaging.getSession(savedId);
            if (detail && detail.session_id) {
              setActiveSessions([detail]);
              saveSessionId(detail.session_id);
            }
          } catch {
            // Session expired or deleted — clear saved ID
            saveSessionId(null);
          }
        }
      } catch (err) {
        console.error('Error recovering staging session:', err);
      }
    };

    recover();
  }, [isAuthenticated, getSavedSessionId, saveSessionId]);

  // -----------------------------------------------------------------------
  // Polling during processing states
  // -----------------------------------------------------------------------

  useEffect(() => {
    const savedId = getSavedSessionId();
    if (!savedId || !isProcessing) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const detail = await api.excelStaging.getSession(savedId);
        if (detail && detail.rows) {
          setCurrentSession(detail);
          setRows(detail.rows);
          setActiveSessions(prev =>
            prev.map(s =>
              s.session_id === savedId
                ? { ...s, status: detail.status, valid_rows: detail.valid_rows, errored_rows: detail.errored_rows }
                : s
            )
          );

          // If session reached ready_for_review, stop processing
          if (detail.status !== 'parsing' && detail.status !== 'rechecking' && detail.status !== 'committing') {
            setIsProcessing(false);
            setProcessingText('');
          }
        }
      } catch (err: any) {
        if (err?.status === 404 || String(err?.message ?? '').toLowerCase().includes('not found')) {
          // Session was deleted (e.g. committed/cancelled elsewhere) — stop polling
          clearSession();
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        } else {
          console.error('Error polling staging session:', err);
        }
      }
    }, POLL_INTERVAL);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [isProcessing, getSavedSessionId]);

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  const uploadFile = useCallback(async (file: File) => {
    setError(null);
    setIsProcessing(true);
    setProcessingText('Uploading and parsing Excel file...');

    try {
      const result = await api.excelStaging.uploadExcel(file);
      saveSessionId(result.session_id);

      // Add to active sessions
      const session: StagingSession = {
        session_id: result.session_id,
        status: result.status || 'parsing',
        original_filename: result.original_filename || file.name,
        total_rows: result.total_rows,
        valid_rows: result.valid_rows,
        errored_rows: result.errored_rows,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setActiveSessions([session]);

      // Load full session detail
      const detail = await api.excelStaging.getSession(result.session_id);
      if (detail) {
        setCurrentSession(detail);
        setRows(detail.rows || []);
      }

      setIsProcessing(false);
      setProcessingText('');
      toast.success(`File parsed: ${result.total_rows} rows found (${result.valid_rows} valid, ${result.errored_rows} with errors)`);
    } catch (err: any) {
      setIsProcessing(false);
      setProcessingText('');
      const msg = err.message || 'Failed to upload file';
      setError(msg);
      toast.error(msg);
      throw err; // Re-throw so the caller knows upload failed
    }
  }, [saveSessionId]);

  const loadSession = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      const detail = await api.excelStaging.getSession(sessionId);
      setCurrentSession(detail);
      setRows(detail.rows || []);
      saveSessionId(sessionId);
    } catch (err: any) {
      setError(err.message || 'Failed to load session');
      saveSessionId(null);
    }
  }, [saveSessionId]);

  const updateCell = useCallback(async (rowId: string, field: string, value: any) => {
    const sessionId = getSavedSessionId();
    if (!sessionId) return;

    setError(null);
    try {
      const updated = await api.excelStaging.updateRow(sessionId, rowId, { [field]: value });
      // Update local rows state (always use functional updater for correctness)
      setRows(prev =>
        prev.map(r => (r.id === rowId ? { ...r, ...updated } : r))
      );
      // Update session if loaded — use functional updater to avoid stale closure
      setCurrentSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          rows: prev.rows.map(r => (r.id === rowId ? { ...r, ...updated } : r)),
        };
      });
    } catch (err: any) {
      setError(err.message || 'Failed to update cell');
    }
  }, [getSavedSessionId]);

  const recheckSession = useCallback(async () => {
    const sessionId = getSavedSessionId();
    if (!sessionId) return;

    setError(null);
    setIsProcessing(true);
    setProcessingText('Re-checking corrected rows...');

    try {
      const result = await api.excelStaging.recheck(sessionId);
      // Update rows from result
      const updatedRows = result.rows || [];
      setRows(updatedRows);

      if (currentSession) {
        setCurrentSession({
          ...currentSession,
          rows: updatedRows,
          status: 'ready_for_review',
          valid_rows: currentSession.total_rows - (result.errored_rows_after || 0),
          errored_rows: result.errored_rows_after || 0,
        });
      }

      if (result.all_clear) {
        toast.success('All rows are valid! You can now upload all invoices.');
      } else {
        toast.info(`${result.errored_rows_after || 0} row(s) still have errors.`);
      }
    } catch (err: any) {
      setError(err.message || 'Recheck failed');
      toast.error(err.message || 'Recheck failed');
    } finally {
      setIsProcessing(false);
      setProcessingText('');
    }
  }, [getSavedSessionId, currentSession]);

  const commitSession = useCallback(async () => {
    const sessionId = getSavedSessionId();
    if (!sessionId) return;

    setError(null);
    setIsProcessing(true);
    setProcessingText('Creating invoices...');

    try {
      const result = await api.excelStaging.commit(sessionId);
      // Session is deleted on backend — clear local state
      clearSession();
      toast.success(`${result.total_committed || 0} invoices created as DRAFT.`);
    } catch (err: any) {
      setIsProcessing(false);
      setProcessingText('');
      setError(err.message || 'Commit failed');
      toast.error(err.message || 'Commit failed');
    }
  }, [getSavedSessionId]);

  const cancelSession = useCallback(async () => {
    const sessionId = getSavedSessionId();
    if (!sessionId) return;

    setError(null);
    try {
      await api.excelStaging.cancel(sessionId);
      clearSession();
      toast.info('Upload cancelled. Staging session deleted.');
    } catch (err: any) {
      setError(err.message || 'Cancel failed');
      toast.error(err.message || 'Cancel failed');
    }
  }, [getSavedSessionId]);

  const refreshSession = useCallback(async () => {
    const sessionId = getSavedSessionId();
    if (!sessionId) return;

    try {
      const detail = await api.excelStaging.getSession(sessionId);
      if (detail) {
        setCurrentSession(detail);
        setRows(detail.rows || []);
      }
    } catch (err: any) {
      // Session might be deleted
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        clearSession();
      }
    }
  }, [getSavedSessionId]);

  const clearSession = useCallback(() => {
    setCurrentSession(null);
    setRows([]);
    setActiveSessions([]);
    setError(null);
    setIsProcessing(false);
    setProcessingText('');
    saveSessionId(null);
  }, [saveSessionId]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <ExcelStagingContext.Provider
      value={{
        activeSessions,
        rows,
        currentSession,
        isProcessing,
        processingText,
        error,
        uploadFile,
        updateCell,
        recheckSession,
        commitSession,
        cancelSession,
        refreshSession,
        clearSession,
        loadSession,
      }}
    >
      {children}
    </ExcelStagingContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useExcelStaging(): ExcelStagingContextType {
  const context = useContext(ExcelStagingContext);
  if (context === undefined) {
    throw new Error('useExcelStaging must be used within an ExcelStagingProvider');
  }
  return context;
}
