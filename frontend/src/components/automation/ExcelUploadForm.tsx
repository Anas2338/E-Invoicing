'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
}

export default function ExcelUploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [polling, setPolling] = useState(false);

  // Poll for upload status
  useEffect(() => {
    if (!progress || !polling) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await automationApi.getUploadStatus(progress.sessionId);

        setProgress({
          sessionId: status.session_id,
          status: status.status,
          processedRows: status.processed_rows,
          totalRows: status.total_rows,
          validatedCount: status.validated_count || 0,
          failedCount: status.failed_count || 0,
          expiredCount: status.expired_count || 0,
          pendingCount: status.pending_count || 0,
          progressPercentage: status.progress_percentage || 0,
          errorMessage: status.error_message
        });

        // Stop polling when completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          setPolling(false);

          if (status.status === 'completed') {
            // Redirect to dashboard after 3 seconds
            setTimeout(() => {
              router.push('/automation/dashboard');
            }, 3000);
          }
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [progress, polling, router]);

  const handleDownloadTemplate = async () => {
    try {
      const blob = await automationApi.downloadTemplate();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'invoice_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to download template. Please try again.');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      if (!selectedFile.name.endsWith('.xlsx')) {
        setError('Please select a valid Excel file (.xlsx)');
        setFile(null);
        return;
      }

      // Validate file size (10 MB)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10 MB limit');
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError(null);
      setSuccess(null);
      setProgress(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    setProgress(null);

    try {
      const data = await automationApi.uploadExcel(file);

      setSuccess(data.message);
      setFile(null);

      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }

      // Start tracking progress
      setProgress({
        sessionId: data.session_id,
        status: 'processing',
        processedRows: 0,
        totalRows: data.total_rows,
        validatedCount: 0,
        failedCount: 0,
        expiredCount: 0,
        pendingCount: data.total_rows,
        progressPercentage: 0
      });
      setPolling(true);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-6">
      {/* Download Template Section */}
      <div className="mb-8 pb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
        <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">Step 1: Download Template</h2>
        <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
          Download the Excel template with predefined columns for invoice data.
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
        <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">Step 2: Upload Filled Excel</h2>
        <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
          Fill the template with your invoice data and upload it here.
        </p>

        <form onSubmit={handleUpload} className="space-y-4">
          {/* File Input */}
          <div>
            <label
              htmlFor="file-input"
              className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2"
            >
              Select Excel File (.xlsx)
            </label>
            <input
              id="file-input"
              type="file"
              accept=".xlsx"
              onChange={handleFileChange}
              className="block w-full text-sm text-[#6d7175] dark:text-[#8c9196] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-[#f1f8f5] file:text-[#008060] hover:file:bg-[#e3f1eb] dark:file:bg-[#0d3d2f]/30 dark:file:text-[#00a876] dark:hover:file:bg-[#0d3d2f]/40 file:transition-colors file:duration-150"
              disabled={uploading || polling}
            />
            {file && (
              <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
                Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
              </p>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
              <div className="flex">
                <svg className="w-5 h-5 text-[#d72c0d] dark:text-[#ff6f59] mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
              </div>
            </div>
          )}

          {/* Success Message */}
          {success && !progress && (
            <div className="bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl p-4">
              <div className="flex">
                <svg className="w-5 h-5 text-[#065f46] dark:text-[#34d399] mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-[#065f46] dark:text-[#34d399] font-medium">{success}</p>
              </div>
            </div>
          )}

          {/* Progress Tracking */}
          {progress && (
            <div className="bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                  {progress.status === 'processing' ? 'Validating Invoices...' :
                   progress.status === 'completed' ? 'Validation Complete!' :
                   'Validation Failed'}
                </h3>
                <span className="text-sm font-medium text-[#008060] dark:text-[#00a876]">
                  {progress.progressPercentage.toFixed(0)}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-[#e3f1eb] dark:bg-[#0d3d2f] rounded-full h-2">
                <div
                  className="bg-[#008060] dark:bg-[#00a876] h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progressPercentage}%` }}
                />
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Processed:</span>
                  <span className="font-medium text-[#202223] dark:text-[#e3e3e3]">
                    {progress.processedRows} / {progress.totalRows}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Validated:</span>
                  <span className="font-medium text-[#065f46] dark:text-[#34d399]">
                    {progress.validatedCount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Failed:</span>
                  <span className="font-medium text-[#d72c0d] dark:text-[#ff6f59]">
                    {progress.failedCount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Expired:</span>
                  <span className="font-medium text-[#f59e0b] dark:text-[#fbbf24]">
                    {progress.expiredCount}
                  </span>
                </div>
              </div>

              {progress.status === 'completed' && (
                <p className="text-xs text-[#065f46] dark:text-[#34d399] mt-2">
                  Redirecting to dashboard...
                </p>
              )}

              {progress.errorMessage && (
                <p className="text-xs text-[#d72c0d] dark:text-[#ff6f59] mt-2">
                  {progress.errorMessage}
                </p>
              )}
            </div>
          )}

          {/* Upload Button */}
          <button
            type="submit"
            disabled={!file || uploading || polling}
            className="w-full inline-flex justify-center items-center h-12 px-4 py-2 bg-[#008060] text-white rounded-xl hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] transition-all duration-150 disabled:bg-[#c9cccf] disabled:cursor-not-allowed disabled:text-[#8c9196] shadow-sm hover:shadow-md font-semibold"
          >
            {uploading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading...
              </>
            ) : polling ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Validating...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Excel File
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
