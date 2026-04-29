'use client';

import { useState } from 'react';
import { Download } from 'lucide-react';
import { automationApi } from '@/services/automationApi';
import { toast } from 'sonner';
import { PrintPreviewModal } from './PrintPreviewModal';

interface PrintInvoiceButtonProps {
  invoiceId: string;
  invoiceNumber: string;
  status: string;
  className?: string;
}

export function PrintInvoiceButton({
  invoiceId,
  invoiceNumber,
  status,
  className = '',
}: PrintInvoiceButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  // Only transferred invoices can be printed
  const isDisabled = status !== 'transferred';

  const handlePrintClick = () => {
    if (isDisabled) {
      toast.error('Only transferred invoices can be printed');
      return;
    }

    // Show preview modal
    setShowPreviewModal(true);
  };

  const handleDownload = async () => {
    setIsGenerating(true);
    setShowPreviewModal(false);

    try {
      // Generate PDF with attachment disposition
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001'}/api/v1/automation/invoices/${invoiceId}/pdf?disposition=attachment`,
        {
          credentials: 'include', // Send httpOnly cookies
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate PDF');
      }

      const pdfBlob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename: invoice_<invoice_number>.pdf
      const sanitizedNumber = invoiceNumber.replace(/\//g, '_');
      link.download = `invoice_${sanitizedNumber}.pdf`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      toast.success('Invoice PDF downloaded successfully');
    } catch (error) {
      console.error('PDF generation failed:', error);

      const errorMessage = error instanceof Error
        ? error.message
        : 'Failed to generate PDF';

      toast.error(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleOpenInNewTab = async () => {
    setIsGenerating(true);
    setShowPreviewModal(false);

    try {
      // Open PDF in new tab with inline disposition
      const url = `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001'}/api/v1/automation/invoices/${invoiceId}/pdf?disposition=inline`;

      // Open in new tab with authorization
      const newWindow = window.open('', '_blank');
      if (newWindow) {
        newWindow.document.write('<html><body>Loading PDF...</body></html>');

        // Fetch with credentials (httpOnly cookies)
        const response = await fetch(url, {
          credentials: 'include',
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to generate PDF');
        }

        const pdfBlob = await response.blob();
        const pdfUrl = window.URL.createObjectURL(pdfBlob);

        newWindow.location.href = pdfUrl;
      } else {
        toast.error('Please allow pop-ups to open PDF in new tab');
      }

      toast.success('Invoice PDF opened in new tab');
    } catch (error) {
      console.error('PDF generation failed:', error);

      const errorMessage = error instanceof Error
        ? error.message
        : 'Failed to generate PDF';

      toast.error(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <>
      <button
        onClick={handlePrintClick}
        disabled={isDisabled || isGenerating}
        className={`
          inline-flex items-center gap-2 px-4 py-2 rounded-md
          text-sm font-medium transition-colors
          ${
            isDisabled
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : isGenerating
              ? 'bg-blue-400 text-white cursor-wait'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }
          ${className}
        `}
        title={
          isDisabled
            ? 'Only transferred invoices can be printed'
            : isGenerating
            ? 'Generating PDF...'
            : 'Print invoice'
        }
      >
        <Download className="w-4 h-4" />
        {isGenerating ? 'Generating...' : 'Print Invoice'}
      </button>

      <PrintPreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        invoiceId={invoiceId}
        invoiceNumber={invoiceNumber}
        onDownload={handleDownload}
        onOpenInNewTab={handleOpenInNewTab}
        isLoading={isGenerating}
      />
    </>
  );
}
