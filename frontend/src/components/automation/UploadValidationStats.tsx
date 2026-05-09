'use client';

import { useUploadSession } from '@/contexts/UploadSessionContext';
import { CheckCircle, XCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';

export function UploadValidationStats() {
  const { activeSessions } = useUploadSession();

  // Show the most recent session (first in array since they're sorted by start time)
  const currentSession = activeSessions.length > 0 ? activeSessions[activeSessions.length - 1] : null;

  if (!currentSession) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'border-green-500 bg-green-50 dark:bg-green-950/20';
      case 'failed':
        return 'border-red-500 bg-red-50 dark:bg-red-950/20';
      case 'processing':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950/20';
      default:
        return 'border-gray-500 bg-gray-50 dark:bg-gray-950/20';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Validation Complete!';
      case 'failed':
        return 'Validation Failed';
      case 'processing':
        return 'Validating with FBR...';
      default:
        return 'Uploading...';
    }
  };

  return (
    <div className={`mt-6 border-2 rounded-xl overflow-hidden ${getStatusColor(currentSession.status)}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-[#008060] to-[#006e52] dark:from-[#00a876] dark:to-[#008f64] p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {currentSession.status === 'processing' ? (
              <Loader2 className="w-6 h-6 text-white animate-spin" />
            ) : currentSession.status === 'completed' ? (
              <CheckCircle className="w-6 h-6 text-white" />
            ) : (
              <XCircle className="w-6 h-6 text-white" />
            )}
            <div>
              <h3 className="text-white font-bold text-lg">
                {getStatusText(currentSession.status)}
              </h3>
              <p className="text-white/90 text-sm">
                Real-time validation progress
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-white">
              {currentSession.progressPercentage.toFixed(0)}%
            </div>
            <div className="text-white/90 text-xs">
              {currentSession.processedRows} / {currentSession.totalRows}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-3 w-full bg-white/20 rounded-full h-3">
          <div
            className="bg-white h-3 rounded-full transition-all duration-300 shadow-lg"
            style={{ width: `${currentSession.progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Validated */}
          <div className="bg-white dark:bg-[#1a1a1a] rounded-lg p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Validated</span>
            </div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {currentSession.validatedCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Ready for FBR
            </div>
          </div>

          {/* Pending */}
          <div className="bg-white dark:bg-[#1a1a1a] rounded-lg p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Pending</span>
            </div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {currentSession.pendingCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              In queue
            </div>
          </div>

          {/* Failed */}
          <div className="bg-white dark:bg-[#1a1a1a] rounded-lg p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Failed</span>
            </div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {currentSession.failedCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Validation errors
            </div>
          </div>

          {/* Expired */}
          <div className="bg-white dark:bg-[#1a1a1a] rounded-lg p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Expired</span>
            </div>
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {currentSession.expiredCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Past schedule
            </div>
          </div>
        </div>

        {/* Error Message */}
        {currentSession.errorMessage && (
          <div className="mt-4 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800 dark:text-red-300">Error</p>
                <p className="text-xs text-red-700 dark:text-red-400 mt-1">
                  {currentSession.errorMessage}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Completion Message */}
        {currentSession.status === 'completed' && (
          <div className="mt-4 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-green-800 dark:text-green-300">
                  Validation Complete!
                </p>
                <p className="text-xs text-green-700 dark:text-green-400 mt-1">
                  {currentSession.validatedCount} invoice(s) validated successfully.
                  {currentSession.failedCount > 0 && ` ${currentSession.failedCount} failed validation.`}
                  {currentSession.expiredCount > 0 && ` ${currentSession.expiredCount} expired.`}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Info Note */}
        <div className="mt-4 flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <p>
            Validation continues in the background. You can navigate to other pages and check progress anytime.
          </p>
        </div>
      </div>
    </div>
  );
}
