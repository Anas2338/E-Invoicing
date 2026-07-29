'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { invoiceService } from '@/lib/api/api-client';
import { useExcelStaging } from '@/contexts/ExcelStagingContext';
import ExcelStagingGrid from '@/components/invoices/ExcelStagingGrid';
import { toast } from 'react-toastify';

type UploadState = 'IDLE' | 'PARSING' | 'REVIEW' | 'COMMITTING' | 'COMPLETED';

export default function ManualExcelUploadForm() {
  const router = useRouter();
  const {
    activeSessions,
    isProcessing,
    error,
    processingText,
    uploadFile,
    refreshSession,
    clearSession,
  } = useExcelStaging();

  const [state, setState] = useState<UploadState>('IDLE');
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [commitInfo, setCommitInfo] = useState<{
    total_committed: number;
    total_failed: number;
  } | null>(null);

  // -----------------------------------------------------------------------
  // Session recovery on mount — if there's an active session, jump to REVIEW
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (activeSessions.length > 0 && state === 'IDLE') {
      setState('REVIEW');
    }
  }, [activeSessions, state]);

  // -----------------------------------------------------------------------
  // Track isProcessing changes for state transitions
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (state === 'PARSING' && !isProcessing && error) {
      setState('IDLE');
    }
  }, [isProcessing, error, state]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  const handleDownloadTemplate = useCallback(async () => {
    try {
      const blob = await invoiceService.downloadManualExcelTemplate();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'bulk_invoice_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      toast.error('Failed to download template. Please try again.');
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.xlsx')) {
        setLocalError('Please select a valid Excel file (.xlsx)');
        setFile(null);
        return;
      }
      if (selectedFile.size > 10 * 1024 * 1024) {
        setLocalError('File size exceeds 10 MB limit');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setLocalError(null);
    }
  }, []);

  const handleUpload = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setLocalError('Please select a file to upload');
      return;
    }

    setLocalError(null);
    setState('PARSING');

    try {
      await uploadFile(file);
      setFile(null);
      // Reset file input
      const fileInput = document.getElementById('manual-excel-file-input') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }
      setState('REVIEW');
    } catch {
      setState('IDLE');
    }
  }, [file, uploadFile]);

  const handleBackToUpload = useCallback(() => {
    clearSession();
    setState('IDLE');
    setCommitInfo(null);
    setLocalError(null);
  }, [clearSession]);

  const handleCommitComplete = useCallback((result: any) => {
    setCommitInfo({
      total_committed: result.total_committed || 0,
      total_failed: 0,
    });
    setState('COMPLETED');
  }, []);

  // -----------------------------------------------------------------------
  // Render — IDLE state (file picker + upload button)
  // -----------------------------------------------------------------------

  if (state === 'IDLE') {
    return (
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border-2 border-blue-600 dark:border-[#2e2e2e] shadow-sm p-4 sm:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Download Template */}
          <div className="pb-6 lg:pb-0 border-b lg:border-b-0 border-blue-600 dark:border-[#2e2e2e] lg:border-r lg:pr-6">
            <h2 className="text-lg sm:text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">Step 1: Download Template</h2>
            <p className="text-xs sm:text-sm text-[#6d7175] dark:text-[#8c9196] mb-4">
              Download the Excel template with predefined columns for manual invoice data.
              Includes income tax column (236G/236H).
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center h-10 px-4 py-2 bg-[#008060] text-white rounded-xl hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] transition-all duration-150 shadow-sm hover:shadow-md font-semibold"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download Template
            </button>
          </div>

          {/* Upload Section */}
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">
              {activeSessions.length > 0
                ? 'Continue Existing Upload'
                : 'Step 2: Upload Filled Excel'}
            </h2>
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              {activeSessions.length > 0
                ? 'You have an in-progress Excel upload. Click below to resume.'
                : 'Fill the template with your invoice data and upload it here. Errors can be fixed inline.'}
            </p>

            {activeSessions.length > 0 ? (
              <div className="space-y-3">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-3">
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Active session: {activeSessions[0].original_filename} —{' '}
                    {activeSessions[0].valid_rows}/{activeSessions[0].total_rows} valid
                  </p>
                </div>
                <button
                  onClick={() => setState('REVIEW')}
                  className="w-full inline-flex justify-center items-center h-12 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all duration-150 shadow-sm font-semibold"
                >
                  Resume Upload
                </button>
                <button
                  onClick={handleBackToUpload}
                  className="w-full inline-flex justify-center items-center h-10 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Dismiss & Start New
                </button>
              </div>
            ) : (
              <form onSubmit={handleUpload} className="space-y-4">
                <div>
                  <label
                    htmlFor="manual-excel-file-input"
                    className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2"
                  >
                    Select Excel File (.xlsx)
                  </label>
                  <input
                    id="manual-excel-file-input"
                    type="file"
                    accept=".xlsx"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-[#6d7175] dark:text-[#8c9196] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-[#f1f8f5] file:text-[#008060] hover:file:bg-[#e3f1eb] dark:file:bg-[#0d3d2f]/30 dark:file:text-[#00a876] dark:hover:file:bg-[#0d3d2f]/40"
                    disabled={isProcessing}
                  />
                  {file && (
                    <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
                      Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
                    </p>
                  )}
                </div>

                {localError && (
                  <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
                    <p className="text-sm text-[#d72c0d] dark:text-[#ff6f59]">{localError}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!file || isProcessing}
                  className="w-full inline-flex justify-center items-center h-12 px-4 py-2 bg-[#008060] text-white rounded-xl hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] transition-all duration-150 disabled:bg-[#c9cccf] disabled:cursor-not-allowed disabled:text-[#8c9196] shadow-sm hover:shadow-md font-semibold"
                >
                  {isProcessing ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render — PARSING state
  // -----------------------------------------------------------------------

  if (state === 'PARSING') {
    return (
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm p-4 sm:p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400 mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400 font-medium">Parsing your Excel file...</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{processingText || 'Processing all rows'}</p>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render — REVIEW state
  // -----------------------------------------------------------------------

  if (state === 'REVIEW') {
    return (
      <div className="flex flex-col flex-1 min-h-0 gap-2">
        <div className="flex items-center justify-between">
          <h4 className="text-lg sm:text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">
            Review & Fix Invoices
          </h4>
        </div>
        <ExcelStagingGrid
          onBackToUpload={handleBackToUpload}
          onCommitComplete={handleCommitComplete}
        />
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render — COMPLETED state
  // -----------------------------------------------------------------------

  if (state === 'COMPLETED') {
    return (
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border-2 border-blue-600 dark:border-gray-700 shadow-sm p-4 sm:p-8">
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-16 h-16 bg-green-100 border-2 border-green-600 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
            All Invoices Created!
          </h2>
          <p className="text-[#6d7175] dark:text-[#8c9196] mb-2">
            {commitInfo?.total_committed || 0} invoice(s) created as DRAFT.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4">
            <button
              onClick={() => router.push('/invoices/history')}
              className="w-full sm:w-auto px-6 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-sm"
            >
              View in Invoice History →
            </button>
            <button
              onClick={handleBackToUpload}
              className="w-full sm:w-auto px-6 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Upload Another File
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Fallback - should not reach here
  return null;
}
