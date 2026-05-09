'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUploadSession } from '@/contexts/UploadSessionContext';
import { X, ChevronDown, ChevronUp, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';

export function ValidationProgressWidget() {
  const router = useRouter();
  const { activeSessions, removeSession } = useUploadSession();
  const [isExpanded, setIsExpanded] = useState(true);

  // Don't render if no active sessions
  if (activeSessions.length === 0) {
    return null;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Validation Complete';
      case 'failed':
        return 'Validation Failed';
      case 'processing':
        return 'Validating with FBR...';
      default:
        return 'Uploading...';
    }
  };

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

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-w-[calc(100vw-2rem)]">
      <div className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-2xl border-2 border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#008060] to-[#006e52] dark:from-[#00a876] dark:to-[#008f64] p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 text-white animate-spin" />
              <h3 className="text-white font-semibold">
                Background Validation
              </h3>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-white hover:bg-white/20 rounded-lg p-1 transition-colors"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? (
                <ChevronDown className="w-5 h-5" />
              ) : (
                <ChevronUp className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-white/90 text-xs mt-1">
            {activeSessions.length} upload{activeSessions.length !== 1 ? 's' : ''} in progress
          </p>
        </div>

        {/* Sessions List */}
        {isExpanded && (
          <div className="max-h-96 overflow-y-auto">
            {activeSessions.map((session) => (
              <div
                key={session.sessionId}
                className={`p-4 border-l-4 ${getStatusColor(session.status)} border-b border-gray-200 dark:border-gray-700 last:border-b-0`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(session.status)}
                    <div>
                      <h4 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {getStatusText(session.status)}
                      </h4>
                      <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                        Session: {session.sessionId.slice(0, 8)}...
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeSession(session.sessionId)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    aria-label="Dismiss"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Progress Bar */}
                <div className="mb-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-[#6d7175] dark:text-[#8c9196]">Progress</span>
                    <span className="font-medium text-[#202223] dark:text-[#e3e3e3]">
                      {session.progressPercentage.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-[#008060] dark:bg-[#00a876] h-2 rounded-full transition-all duration-300"
                      style={{ width: `${session.progressPercentage}%` }}
                    />
                  </div>
                </div>

                {/* Statistics Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                  <div className="flex justify-between">
                    <span className="text-[#6d7175] dark:text-[#8c9196]">Processed:</span>
                    <span className="font-medium text-[#202223] dark:text-[#e3e3e3]">
                      {session.processedRows}/{session.totalRows}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d7175] dark:text-[#8c9196]">Validated:</span>
                    <span className="font-medium text-green-600 dark:text-green-400">
                      {session.validatedCount}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d7175] dark:text-[#8c9196]">Failed:</span>
                    <span className="font-medium text-red-600 dark:text-red-400">
                      {session.failedCount}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d7175] dark:text-[#8c9196]">Expired:</span>
                    <span className="font-medium text-yellow-600 dark:text-yellow-400">
                      {session.expiredCount}
                    </span>
                  </div>
                </div>

                {/* Error Message */}
                {session.errorMessage && (
                  <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-2 mb-3">
                    <p className="text-xs text-red-800 dark:text-red-300">
                      {session.errorMessage}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => router.push('/automation/dashboard')}
                    className="flex-1 text-xs font-medium text-[#008060] dark:text-[#00a876] hover:bg-[#008060]/10 dark:hover:bg-[#00a876]/10 py-2 rounded-lg transition-colors"
                  >
                    View Dashboard
                  </button>
                  {session.status === 'completed' && (
                    <button
                      onClick={() => removeSession(session.sessionId)}
                      className="flex-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 py-2 rounded-lg transition-colors"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer Note */}
        {isExpanded && (
          <div className="bg-gray-50 dark:bg-gray-900/50 px-4 py-2 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-center text-[#6d7175] dark:text-[#8c9196]">
              You can navigate freely while validation continues
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
