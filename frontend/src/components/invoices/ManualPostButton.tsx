'use client';

import { useState } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { manualPostInvoice } from '@/services/autoPostingApi';

interface ManualPostButtonProps {
  invoiceId: string;
  invoiceStatus: string;
  onSuccess?: () => void;
}

export default function ManualPostButton({
  invoiceId,
  invoiceStatus,
  onSuccess
}: ManualPostButtonProps) {
  const { isAuthenticated } = useAuth();
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLimitWarning, setShowLimitWarning] = useState(false);

  const handlePost = async (overrideLimit: boolean = false) => {
    if (!isAuthenticated) return;

    try {
      setPosting(true);
      setError(null);

      const result = await manualPostInvoice(
        invoiceId,
        overrideLimit
      );

      if (result.success) {
        if (onSuccess) onSuccess();
      } else if (result.daily_limit_warning && !overrideLimit) {
        setShowLimitWarning(true);
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to post invoice');
    } finally {
      setPosting(false);
    }
  };

  // Only show button for TRANSFERRED status
  if (invoiceStatus !== 'TRANSFERRED') {
    return null;
  }

  return (
    <>
      <button
        onClick={() => handlePost(false)}
        disabled={posting}
        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {posting ? 'Posting...' : 'Post to FBR'}
      </button>

      {error && (
        <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Daily Limit Warning Dialog */}
      {showLimitWarning && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md">
            <h3 className="text-lg font-semibold mb-4">Daily Limit Reached</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              You have reached your daily posting limit. Do you want to post this invoice anyway?
            </p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setShowLimitWarning(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowLimitWarning(false);
                  handlePost(true);
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Post Anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
