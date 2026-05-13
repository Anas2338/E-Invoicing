'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { invoiceService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';

interface UploadResult {
  total_created: number;
  total_failed: number;
  invoices: Array<{
    id: string;
    external_id: string;
    invoice_type: string;
    status: string;
  }>;
  errors?: Array<{
    invoice_number: string;
    error: string;
  }>;
}

export default function ManualExcelUploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  const handleDownloadTemplate = async () => {
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
    } catch (err) {
      toast.error('Failed to download template. Please try again.');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.xlsx')) {
        setError('Please select a valid Excel file (.xlsx)');
        setFile(null);
        return;
      }

      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10 MB limit');
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError(null);
      setResult(null);
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
    setResult(null);

    try {
      const data = await invoiceService.uploadManualExcel(file);

      setResult(data);
      setFile(null);

      // Reset file input
      const fileInput = document.getElementById('manual-excel-file-input') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }

      if (data.total_created > 0) {
        toast.success(`Successfully created ${data.total_created} invoice(s)!`);
      }
      if (data.total_failed > 0) {
        toast.warning(`${data.total_failed} invoice(s) failed to create.`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-6">
      {/* Info banner */}
      <div className="mb-6 p-4 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl">
        <p className="text-sm text-[#065f46] dark:text-[#34d399]">
          Upload an Excel file to create multiple invoices at once. Each row becomes a draft invoice.
          Invoice dates must be today or a previous date — future dates are not allowed.
        </p>
      </div>

      {/* Download Template Section */}
      <div className="mb-8 pb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
        <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">Step 1: Download Template</h2>
        <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
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
        <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-3">Step 2: Upload Filled Excel</h2>
        <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
          Fill the template with your invoice data and upload it here. Invoices will be created as drafts.
        </p>

        <form onSubmit={handleUpload} className="space-y-4">
          {/* File Input */}
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
              className="block w-full text-sm text-[#6d7175] dark:text-[#8c9196] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-[#f1f8f5] file:text-[#008060] hover:file:bg-[#e3f1eb] dark:file:bg-[#0d3d2f]/30 dark:file:text-[#00a876] dark:hover:file:bg-[#0d3d2f]/40 file:transition-colors file:duration-150"
              disabled={uploading}
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

          {/* Upload Result */}
          {result && (
            <div className="bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl p-4 space-y-3">
              <div className="flex">
                <svg className="w-5 h-5 text-[#065f46] dark:text-[#34d399] mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm text-[#065f46] dark:text-[#34d399] font-medium">
                    Created {result.total_created} invoice(s) successfully.
                  </p>
                  {result.total_failed > 0 && (
                    <p className="text-sm text-[#d72c0d] dark:text-[#ff6f59] mt-1">
                      {result.total_failed} invoice(s) failed.
                    </p>
                  )}
                </div>
              </div>

              {/* Created Invoices List */}
              {result.invoices.length > 0 && (
                <div className="mt-2">
                  <h4 className="text-xs font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2">Created Invoices:</h4>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {result.invoices.map((inv) => (
                      <div key={inv.id} className="text-xs text-[#6d7175] dark:text-[#8c9196] flex justify-between">
                        <span>{inv.external_id} ({inv.invoice_type})</span>
                        <span className="text-[#065f46] dark:text-[#34d399]">{inv.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Errors List */}
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2">
                  <h4 className="text-xs font-semibold text-[#d72c0d] dark:text-[#ff6f59] mb-2">Errors:</h4>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {result.errors.map((err, idx) => (
                      <div key={idx} className="text-xs text-[#d72c0d] dark:text-[#ff6f59]">
                        <span className="font-medium">{err.invoice_number}:</span> {err.error}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={() => router.push('/invoices/history')}
                className="text-sm text-[#008060] dark:text-[#00a876] hover:underline font-medium mt-2"
              >
                View in Invoice History →
              </button>
            </div>
          )}

          {/* Upload Button */}
          <button
            type="submit"
            disabled={!file || uploading}
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
