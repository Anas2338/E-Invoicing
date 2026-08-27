'use client';

import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { toast } from 'react-toastify';
import { Button } from '@/components/ui/button';

interface ReportDownloadButtonProps {
  dateFrom: string;
  dateTo: string;
  className?: string;
  disabled?: boolean;
}

/**
 * Downloads the invoice report PDF for the already-searched date range.
 * Mirrors PrintInvoiceButton's fetch + blob + anchor mechanism; GET needs
 * no CSRF header, credentials are included so the httpOnly cookie travels.
 */
export function ReportDownloadButton({ dateFrom, dateTo, className = '', disabled = false }: ReportDownloadButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleDownload = async () => {
    setIsGenerating(true);

    try {
      const queryParams = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1'}/reports/invoices/pdf?${queryParams.toString()}`,
        {
          credentials: 'include', // Send httpOnly cookies
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || 'Failed to generate report PDF');
      }

      const pdfBlob = await response.blob();
      const url = window.URL.createObjectURL(pdfBlob);
      const filename = `invoice_report_${dateFrom}_${dateTo}.pdf`;

      // Detect mobile: iOS Safari ignores the download attribute on anchor clicks
      const isMobile = /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent);

      if (isMobile) {
        // On mobile, open PDF in a new tab — the native PDF viewer provides
        // share/save options so the user can download or print
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
          toast.error('Please allow pop-ups to view the report PDF');
        } else {
          toast.success('Report PDF opened — use share/save to download');
        }
      } else {
        // On desktop, trigger a direct download
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success('Report PDF downloaded successfully');
      }

      // Cleanup blob URL after a delay (new tab needs it still alive)
      if (isMobile) {
        setTimeout(() => window.URL.revokeObjectURL(url), 3000);
      } else {
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Report PDF generation failed:', error);

      const errorMessage = error instanceof Error ? error.message : 'Failed to generate report PDF';
      toast.error(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      size="default"
      onClick={handleDownload}
      disabled={isGenerating || disabled}
      className={className}
      title={`Download report PDF (${dateFrom} to ${dateTo})`}
    >
      {isGenerating ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating…
        </>
      ) : (
        <>
          <Download className="h-4 w-4" />
          Download PDF
        </>
      )}
    </Button>
  );
}
