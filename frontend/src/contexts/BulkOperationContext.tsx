'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

interface BulkOperationError {
  invoice_id: string;
  invoice_number: string;
  error: string;
}

interface BulkOperationProgress {
  taskId: string;
  operationType: 'bulk_validate' | 'bulk_post';
  status: 'processing' | 'completed' | 'partially_completed' | 'failed';
  totalCount: number;
  processedCount: number;
  successCount: number;
  failureCount: number;
  errors: BulkOperationError[];
  progressPercentage: number;
  startedAt: string;
  invoiceIds: string[];
}

interface BulkOperationContextType {
  activeOperations: BulkOperationProgress[];
  startOperation: (taskId: string, operationType: string, totalCount: number, invoiceIds: string[]) => void;
  removeOperation: (taskId: string) => void;
  cancelOperation: (taskId: string) => Promise<void>;
  hasActiveOperation: boolean;
  processingInvoiceIds: string[];
}

const BulkOperationContext = createContext<BulkOperationContextType | undefined>(undefined);

const STORAGE_KEY = 'active_bulk_operations';
const POLL_INTERVAL = 3000; // 3 seconds, matching UploadSessionContext
const AUTO_REMOVE_DELAY = 10000; // 10 seconds after completion

export function BulkOperationProvider({ children }: { children: React.ReactNode }) {
  const [activeOperations, setActiveOperations] = useState<BulkOperationProgress[]>([]);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { isAuthenticated } = useAuth();
  const backendRecoveryDone = useRef(false);
  const completedToastShown = useRef<Set<string>>(new Set());

  // Load operations from localStorage on mount (immediate, before auth check)
  useEffect(() => {
    const savedOperations = localStorage.getItem(STORAGE_KEY);
    if (savedOperations) {
      try {
        const operations: BulkOperationProgress[] = JSON.parse(savedOperations);
        // Keep processing operations; filter out completed/failed older than 2 min
        const twoMinutesAgo = Date.now() - 2 * 60 * 1000;
        const active = operations.filter((op) => {
          if (op.status === 'processing') {
            return true;
          }
          const startedAt = new Date(op.startedAt).getTime();
          return startedAt > twoMinutesAgo;
        });
        if (active.length > 0) {
          setActiveOperations(active);
        }
      } catch (err) {
        console.error('Error loading saved bulk operations:', err);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Recover in-progress operations from backend after authentication is confirmed
  useEffect(() => {
    if (!isAuthenticated || backendRecoveryDone.current) return;
    backendRecoveryDone.current = true;

    let cancelled = false;

    const recoverFromBackend = async () => {
      try {
        const response = await api.invoices.getActiveBulkTasks();
        const processingTasks: BulkOperationProgress[] = (response.tasks || []).map(
          (task: any) => ({
            taskId: task.task_id,
            operationType: task.operation_type,
            status: task.status,
            totalCount: task.total_count,
            processedCount: task.processed_count,
            successCount: task.success_count,
            failureCount: task.failure_count,
            errors: task.errors || [],
            progressPercentage: task.progress_percentage || 0,
            startedAt: task.created_at || new Date().toISOString(),
          })
        );

        if (cancelled) return;

        if (processingTasks.length > 0) {
          setActiveOperations((prev) => {
            const existingIds = new Set(prev.map((op) => op.taskId));
            const newOps = processingTasks.filter(
              (op) => !existingIds.has(op.taskId)
            );
            if (newOps.length === 0) return prev;
            return [...prev, ...newOps];
          });
        }
      } catch (err) {
        console.error('Error recovering bulk operations from backend:', err);
      }
    };

    recoverFromBackend();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  // Poll active operations and auto-remove completed ones
  useEffect(() => {
    if (activeOperations.length === 0) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    const processingOps = activeOperations.filter((op) => op.status === 'processing');
    if (processingOps.length === 0) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    // Start polling
    pollIntervalRef.current = setInterval(async () => {
      for (const op of processingOps) {
        try {
          const task = await api.invoices.getBulkTaskStatus(op.taskId);

          setActiveOperations((prev) =>
            prev.map((p) =>
              p.taskId === op.taskId
                ? {
                    ...p,
                    status: task.status,
                    processedCount: task.processed_count,
                    successCount: task.success_count,
                    failureCount: task.failure_count,
                    errors: task.errors || [],
                    progressPercentage: task.progress_percentage || 0,
                  }
                : p
            )
          );

          // Show toast on completion (only once per task)
          const terminalStatuses = ['completed', 'partially_completed', 'failed'];
          if (terminalStatuses.includes(task.status) && !completedToastShown.current.has(op.taskId)) {
            completedToastShown.current.add(op.taskId);

            if (task.status === 'completed') {
              toast.success(
                `Bulk ${op.operationType === 'bulk_validate' ? 'validation' : 'posting'} completed: ${task.success_count} succeeded, ${task.failure_count} failed.`,
                { autoClose: 5000 }
              );
            } else if (task.status === 'partially_completed') {
              toast.warning(
                `Bulk ${op.operationType === 'bulk_validate' ? 'validation' : 'posting'} completed with errors: ${task.success_count} succeeded, ${task.failure_count} failed. Check details on the history page.`,
                { autoClose: 5000 }
              );
            } else if (task.status === 'failed') {
              toast.error(
                `Bulk ${op.operationType === 'bulk_validate' ? 'validation' : 'posting'} failed.`,
                { autoClose: 5000 }
              );
            }

            // Auto-remove after delay
            const taskId = op.taskId;
            setTimeout(() => {
              setActiveOperations((prev) =>
                prev.filter((p) => p.taskId !== taskId)
              );
            }, AUTO_REMOVE_DELAY);
          }
        } catch (err) {
          console.error(`Error polling bulk task ${op.taskId}:`, err);
        }
      }
    }, POLL_INTERVAL);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [activeOperations.length]);

  // Persist to localStorage whenever activeOperations changes
  useEffect(() => {
    if (activeOperations.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(activeOperations));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [activeOperations]);

  const startOperation = useCallback(
    (taskId: string, operationType: string, totalCount: number, invoiceIds: string[]) => {
      const newOp: BulkOperationProgress = {
        taskId,
        operationType: operationType as 'bulk_validate' | 'bulk_post',
        status: 'processing',
        totalCount,
        processedCount: 0,
        successCount: 0,
        failureCount: 0,
        errors: [],
        progressPercentage: 0,
        startedAt: new Date().toISOString(),
        invoiceIds,
      };

      setActiveOperations((prev) => {
        // Don't add if already tracked
        if (prev.some((op) => op.taskId === taskId)) return prev;
        return [...prev, newOp];
      });
    },
    []
  );

  const removeOperation = useCallback((taskId: string) => {
    setActiveOperations((prev) => prev.filter((op) => op.taskId !== taskId));
  }, []);

  const cancelOperation = useCallback(async (taskId: string) => {
    try {
      await api.invoices.cancelBulkTask(taskId);
    } catch (err: any) {
      // 404 means the task already completed or was already removed — treat as success
      if (err?.status !== 404) {
        console.error('Error cancelling bulk operation:', err);
        return;
      }
    }
    setActiveOperations((prev) => prev.filter((op) => op.taskId !== taskId));
  }, []);

  const hasActiveOperation = activeOperations.some(
    (op) => op.status === 'processing'
  );

  const processingInvoiceIds = activeOperations
    .filter((op) => op.status === 'processing')
    .flatMap((op) => op.invoiceIds);

  return (
    <BulkOperationContext.Provider
      value={{
        activeOperations,
        startOperation,
        removeOperation,
        cancelOperation,
        hasActiveOperation,
        processingInvoiceIds,
      }}
    >
      {children}
    </BulkOperationContext.Provider>
  );
}

export function useBulkOperation(): BulkOperationContextType {
  const context = useContext(BulkOperationContext);
  if (!context) {
    throw new Error('useBulkOperation must be used within a BulkOperationProvider');
  }
  return context;
}
