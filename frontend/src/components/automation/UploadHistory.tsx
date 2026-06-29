'use client';

import { useState, useEffect } from 'react';
import { automationApi, UploadSession } from '@/services/automationApi';
import { Trash2, AlertCircle, RefreshCw, FileX } from 'lucide-react';

interface UploadHistoryProps {
  refreshKey?: number;
  onLoading?: (loading: boolean) => void;
}

export default function UploadHistory({ refreshKey = 0, onLoading }: UploadHistoryProps) {
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
      onLoading?.(true);
      setError(null);
      const response = await automationApi.getUploadSessions();
      setSessions(response.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load upload sessions');
    } finally {
      setLoading(false);
      onLoading?.(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [refreshKey]);

  const handleDeleteSession = async (sessionId: string) => {
    try {
      setDeletingSessionId(sessionId);
      await automationApi.deleteUploadSession(sessionId);

      // Remove from local state
      setSessions(sessions.filter(s => s.id !== sessionId));
      setShowDeleteConfirm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete upload session');
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleDeleteExcelFile = async (sessionId: string) => {
    try {
      setDeletingFileId(sessionId);
      await automationApi.deleteExcelFile(sessionId);

      // Update local state to reflect file deletion
      setSessions(sessions.map(s =>
        s.id === sessionId
          ? { ...s, has_file: false, can_delete_file: false }
          : s
      ));
      setShowDeleteFileConfirm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete Excel file');
    } finally {
      setDeletingFileId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      processing: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-800 dark:text-blue-300', label: 'Processing' },
      completed: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-800 dark:text-green-300', label: 'Completed' },
      failed: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-800 dark:text-red-300', label: 'Failed' },
      uploading: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-800 dark:text-gray-300', label: 'Uploading' },
    };
    const badge = badges[status] || { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-800 dark:text-gray-300', label: status };
    return (
      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    );
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
    <div className="overflow-x-auto rounded-2xl flex-1 min-h-0">
      <div className="min-w-[830px] flex flex-col gap-2 h-full">
        {/* Table 1: Column Headers (blue header) */}
        <table className="w-full table-fixed bg-[#7c97f0] rounded-4xl flex-shrink-0 border-separate border-spacing-0">
          <thead>
            <tr>
              <th className="border-r-2 border-[#FFFFFF] w-[15%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Upload Date
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[12%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Status
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[10%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Total
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[10%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Pending
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[12%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Transferred
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[10%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Failed
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[10%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Blocked
              </th>
              <th className="w-[21%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Actions
              </th>
            </tr>
          </thead>
        </table>

        {/* Table 2: Body — scrollable */}
        <div className="flex-1 min-h-0 flex flex-col items-start">
          <div className="w-full max-h-full overflow-y-auto overflow-x-hidden rounded-4xl bg-blue-50 border-2 border-blue-600">
            <table className="w-full table-fixed border-separate border-spacing-0">
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id} className="group transition-colors duration-150 hover:bg-slate-50/60">
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm text-gray-900 dark:text-white w-[15%] text-center">
                      {formatDate(session.uploaded_at)}
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-center w-[12%]">
                      <div className="flex justify-center">
                        {getStatusBadge(session.processing_status)}
                      </div>
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm font-semibold text-gray-900 dark:text-white w-[10%] text-center">
                      {session.total_count}
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm font-semibold text-amber-600 dark:text-amber-400 w-[10%] text-center">
                      {session.pending_count}
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm font-semibold text-emerald-600 dark:text-emerald-400 w-[12%] text-center">
                      {session.transferred_count}
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm font-semibold text-red-600 dark:text-red-400 w-[10%] text-center">
                      {session.failed_count}
                    </td>
                    <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle text-xs lg:text-sm font-semibold text-gray-600 dark:text-gray-400 w-[10%] text-center">
                      {session.blocked_count}
                    </td>
                    <td className="border-b-1 border-blue-200 px-3.5 py-4 align-middle text-center w-[21%]">
                      <div className="flex items-center justify-center gap-1.5">
                        {session.can_delete ? (
                          showDeleteConfirm === session.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleDeleteSession(session.id)}
                                disabled={deletingSessionId === session.id}
                                className="px-2 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 text-[10px] font-semibold"
                              >
                                {deletingSessionId === session.id ? '...' : 'Confirm'}
                              </button>
                              <button
                                onClick={() => setShowDeleteConfirm(null)}
                                disabled={deletingSessionId === session.id}
                                className="px-2 py-1 bg-gray-200 dark:bg-neutral-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-neutral-600 text-[10px] font-semibold"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setShowDeleteConfirm(session.id)}
                              className="inline-flex items-center gap-1 px-2 py-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors text-[10px] font-semibold"
                              title="Delete session and all invoices"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Delete
                            </button>
                          )
                        ) : session.can_delete_file ? (
                          showDeleteFileConfirm === session.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleDeleteExcelFile(session.id)}
                                disabled={deletingFileId === session.id}
                                className="px-2 py-1 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 text-[10px] font-semibold"
                              >
                                {deletingFileId === session.id ? '...' : 'Confirm'}
                              </button>
                              <button
                                onClick={() => setShowDeleteFileConfirm(null)}
                                disabled={deletingFileId === session.id}
                                className="px-2 py-1 bg-gray-200 dark:bg-neutral-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-neutral-600 text-[10px] font-semibold"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setShowDeleteFileConfirm(session.id)}
                              className="inline-flex items-center gap-1 px-2 py-1 text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-md transition-colors text-[10px] font-semibold"
                              title="Delete Excel file only"
                            >
                              <FileX className="w-3.5 h-3.5" />
                              Delete File
                            </button>
                          )
                        ) : (
                          <span className="text-gray-400 dark:text-neutral-600 text-[10px]">
                            {session.has_file ? 'Locked' : 'N/A'}
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
      </div>
    </div>
  );
}
