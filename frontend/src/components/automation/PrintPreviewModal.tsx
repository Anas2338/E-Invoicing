'use client';

import { X, Download, ExternalLink } from 'lucide-react';

interface PrintPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoiceId: string;
  invoiceNumber: string;
  onDownload: () => void;
  onOpenInNewTab: () => void;
  isLoading?: boolean;
}

export function PrintPreviewModal({
  isOpen,
  onClose,
  invoiceId,
  invoiceNumber,
  onDownload,
  onOpenInNewTab,
  isLoading = false,
}: PrintPreviewModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-[#1a1a1a] rounded-xl shadow-xl max-w-md w-full mx-4 p-6 border border-[#e1e3e5] dark:border-[#2e2e2e]">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">
            Print Invoice
          </h3>
          <button
            onClick={onClose}
            className="text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="mb-6">
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-2">
            Invoice: <span className="font-semibold text-[#202223] dark:text-[#e3e3e3]">{invoiceNumber}</span>
          </p>
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
            Choose how you want to view the PDF:
          </p>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          <button
            onClick={onDownload}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download className="w-5 h-5" />
            <span className="font-medium">Download PDF</span>
          </button>

          <button
            onClick={onOpenInNewTab}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white dark:bg-[#2e2e2e] text-[#202223] dark:text-[#e3e3e3] border border-[#e1e3e5] dark:border-[#404040] rounded-lg hover:bg-[#f6f6f7] dark:hover:bg-[#404040] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ExternalLink className="w-5 h-5" />
            <span className="font-medium">Open in New Tab</span>
          </button>
        </div>

        {/* Help Text */}
        <div className="mt-4 pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
          <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
            <strong>Download:</strong> Save the PDF to your device
            <br />
            <strong>Open in New Tab:</strong> View the PDF in your browser
          </p>
        </div>
      </div>
    </div>
  );
}
