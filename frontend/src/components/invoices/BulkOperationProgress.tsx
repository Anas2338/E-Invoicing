'use client';

import React, { useState } from 'react';
import { useBulkOperation } from '@/contexts/BulkOperationContext';
import { X, CheckCircle, AlertTriangle, XCircle, Loader2, ChevronDown, ChevronUp, Square } from 'lucide-react';

interface BulkOperationProgressProps {
  isOpen: boolean;
  onClose: () => void;
}

export function BulkOperationProgress({ isOpen, onClose }: BulkOperationProgressProps) {
  const { activeOperations, removeOperation, cancelOperation } = useBulkOperation();
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 max-h-[80vh] overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Bulk Operations
          {activeOperations.length > 0 && (
            <span className="ml-1.5 text-xs text-gray-500 dark:text-gray-400">
              ({activeOperations.length})
            </span>
          )}
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {activeOperations.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
          No active bulk operations
        </div>
      ) : (
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          {activeOperations.map((op) => {
            const isExpanded = expandedTaskId === op.taskId;
            const isProcessing = op.status === 'processing';
            const operationLabel =
              op.operationType === 'bulk_validate' ? 'Validation' : 'Posting';

            return (
              <div key={op.taskId} className="px-4 py-3">
                {/* Header row */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isProcessing ? (
                      <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                    ) : op.status === 'completed' ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : op.status === 'partially_completed' ? (
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Bulk {operationLabel}
                    </span>
                    {!isProcessing && (
                      <span className="text-[10px] text-gray-500 dark:text-gray-400 capitalize px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded-full">
                        {op.status.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                  {isProcessing ? (
                    <button
                      onClick={async () => {
                        await cancelOperation(op.taskId);
                      }}
                      className="flex items-center gap-1 text-xs text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 px-2 py-1 rounded-md transition-colors font-medium"
                      title="Stop operation"
                    >
                      <Square className="h-3 w-3 fill-current" />
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => removeOperation(op.taskId)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      title="Dismiss"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                {/* Progress */}
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                  <span>
                    {op.processedCount} of {op.totalCount} processed
                  </span>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    {op.progressPercentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      op.status === 'completed'
                        ? 'bg-green-500'
                        : op.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-blue-500'
                    }`}
                    style={{ width: `${Math.min(op.progressPercentage, 100)}%` }}
                  />
                </div>

                {/* Counts */}
                <div className="flex gap-3 text-xs">
                  <span className="text-green-600 dark:text-green-400 font-medium">
                    {op.successCount} success
                  </span>
                  {op.failureCount > 0 && (
                    <span className="text-red-600 dark:text-red-400 font-medium">
                      {op.failureCount} failed
                    </span>
                  )}
                </div>

                {/* Error details */}
                {op.errors.length > 0 && (
                  <>
                    <button
                      onClick={() => setExpandedTaskId(isExpanded ? null : op.taskId)}
                      className="flex items-center gap-1 mt-1.5 text-xs text-red-600 dark:text-red-400 hover:underline"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      {op.errors.length} error{op.errors.length > 1 ? 's' : ''}
                    </button>
                    {isExpanded && (
                      <div className="mt-1.5 space-y-1 max-h-24 overflow-y-auto">
                        {op.errors.map((err, idx) => (
                          <div
                            key={idx}
                            className="text-[10px] text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 rounded p-1.5"
                          >
                            <span className="font-semibold">{err.invoice_number || err.invoice_id}:</span>{' '}
                            {err.error}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
