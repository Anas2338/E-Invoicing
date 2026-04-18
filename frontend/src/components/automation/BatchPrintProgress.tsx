'use client';

interface BatchPrintProgressProps {
  isGenerating: boolean;
  invoiceCount: number;
}

export function BatchPrintProgress({
  isGenerating,
  invoiceCount,
}: BatchPrintProgressProps) {
  if (!isGenerating) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Progress Modal */}
      <div className="relative bg-white dark:bg-[#1a1a1a] rounded-xl shadow-xl max-w-md w-full mx-4 p-6 border border-[#e1e3e5] dark:border-[#2e2e2e]">
        {/* Header */}
        <div className="text-center mb-4">
          <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2">
            Generating Batch PDF
          </h3>
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
            Processing {invoiceCount} invoice{invoiceCount !== 1 ? 's' : ''}...
          </p>
        </div>

        {/* Spinner */}
        <div className="flex justify-center mb-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>

        {/* Progress Message */}
        <div className="text-center">
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
            This may take a moment for large batches.
            <br />
            Please do not close this window.
          </p>
        </div>

        {/* Progress Bar (Indeterminate) */}
        <div className="mt-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div className="h-full bg-blue-600 rounded-full animate-pulse" style={{ width: '100%' }}></div>
        </div>
      </div>
    </div>
  );
}
