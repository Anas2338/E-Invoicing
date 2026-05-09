'use client';

import { useState, useEffect } from 'react';
import { automationApi, UploadSession } from '@/services/automationApi';
import { Trash2, AlertCircle, RefreshCw, FileX } from 'lucide-react';

export default function UploadHistory() {
  const [sessions, setSessions] = useState<UploadSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [showDeleteFileConfirm, setShowDeleteFileConfirm] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await automationApi.getUploadSessions();
      setSessions(response.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load upload sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleDeleteSession = async (sessionId: string) => {
    try {
      setDeletingSessionId(sessionId);

      // Optimistic update: remove from UI immediately
      const previousSessions = [...sessions];
      setSessions(sessions.filter(s => s.id !== sessionId));
      setShowDeleteConfirm(null);

      // Call API in background
      await automationApi.deleteUploadSession(sessionId);

    } catch (err) {
      // Rollback on error: restore the session
      setError(err instanceof Error ? err.message : 'Failed to delete upload session');

      // Reload sessions to restore correct state
      await loadSessions();
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleDeleteExcelFile = async (sessionId: string) => {
    try {
      setDeletingFileId(sessionId);

      // Optimistic update: update UI immediately
      const previousSessions = [...sessions];
      setSessions(sessions.map(s =>
        s.id === sessionId
          ? { ...s, has_file: false, can_delete_file: false }
          : s
      ));
      setShowDeleteFileConfirm(null);

      // Call API in background
      await automationApi.deleteExcelFile(sessionId);

    } catch (err) {
      // Rollback on error: restore previous state
      setError(err instanceof Error ? err.message : 'Failed to delete Excel file');

      // Reload sessions to restore correct state
      await loadSessions();
    } finally {
      setDeletingFileId(null);
    }
  };

  const formatDate = (dateString: string) => {
    // Ensure the date string is treated as UTC
    // If it doesn't end with 'Z', append it to indicate UTC
    let utcDateStr = dateString;
    if (!dateString.endsWith('Z') && !dateString.includes('+')) {
      utcDateStr = dateString + 'Z';
    }

    const date = new Date(utcDateStr);

    // Use Intl.DateTimeFormat for proper timezone conversion to Pakistan time
    const formatter = new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: 'Asia/Karachi'
    });

    return formatter.format(date);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-600 dark:text-blue-400" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading upload history...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
            <button
              onClick={loadSessions}
              className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">No upload sessions found</p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
          Upload an Excel file to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Upload History ({sessions.length})
        </h2>
        <button
          onClick={loadSessions}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Upload Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Total
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Pending
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Transferred
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Failed
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Blocked
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {sessions.map((session) => (
              <tr key={session.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {formatDate(session.uploaded_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {session.total_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-600 dark:text-yellow-400">
                  {session.pending_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 dark:text-green-400">
                  {session.transferred_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 dark:text-red-400">
                  {session.failed_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                  {session.blocked_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  <div className="flex items-center justify-end gap-2">
                    {session.can_delete ? (
                      showDeleteConfirm === session.id ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleDeleteSession(session.id)}
                            disabled={deletingSessionId === session.id}
                            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 text-xs"
                          >
                            {deletingSessionId === session.id ? 'Deleting...' : 'Confirm'}
                          </button>
                          <button
                            onClick={() => setShowDeleteConfirm(null)}
                            disabled={deletingSessionId === session.id}
                            className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-xs"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setShowDeleteConfirm(session.id)}
                          className="flex items-center gap-1 px-3 py-1 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                          title="Delete session and all invoices"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete Session
                        </button>
                      )
                    ) : session.can_delete_file ? (
                      showDeleteFileConfirm === session.id ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleDeleteExcelFile(session.id)}
                            disabled={deletingFileId === session.id}
                            className="px-3 py-1 bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50 text-xs"
                          >
                            {deletingFileId === session.id ? 'Deleting...' : 'Confirm'}
                          </button>
                          <button
                            onClick={() => setShowDeleteFileConfirm(null)}
                            disabled={deletingFileId === session.id}
                            className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-xs"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setShowDeleteFileConfirm(session.id)}
                          className="flex items-center gap-1 px-3 py-1 text-orange-600 dark:text-orange-400 hover:text-orange-800 dark:hover:text-orange-300"
                          title="Delete Excel file only (keeps session and invoice records)"
                        >
                          <FileX className="w-4 h-4" />
                          Delete Excel File
                        </button>
                      )
                    ) : (
                      <span className="text-gray-400 dark:text-gray-600 text-xs">
                        {session.has_file ? 'Cannot delete (has non-transferred invoices)' : 'No file to delete'}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
