'use client';

import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

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

  const handleDownload = async () => {
    setIsGenerating(true);

    try {
      // Generate PDF with attachment disposition
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1'}/invoices/${invoiceId}/pdf?disposition=attachment`,
        {
          credentials: 'include', // Send httpOnly cookies
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate PDF');
      }

      const pdfBlob = await response.blob();
      const url = window.URL.createObjectURL(pdfBlob);
      const sanitizedNumber = invoiceNumber.replace(/\//g, '_');
      const filename = `invoice_${sanitizedNumber}.pdf`;

      // Detect mobile: iOS Safari ignores the download attribute on anchor clicks
      const isMobile = /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent);

      if (isMobile) {
        // On mobile, open PDF in a new tab — the native PDF viewer provides
        // share/save options so the user can download or print
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
          toast.error('Please allow pop-ups to view the invoice PDF');
        } else {
          toast.success('Invoice PDF opened — use share/save to download');
        }
      } else {
        // On desktop, trigger a direct download
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success('Invoice PDF downloaded successfully');
      }

      // Cleanup blob URL after a delay (new tab needs it still alive)
      if (isMobile) {
        setTimeout(() => window.URL.revokeObjectURL(url), 3000);
      } else {
        window.URL.revokeObjectURL(url);
      }
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
    <Button
      variant="outline"
      size="sm"
      onClick={handleDownload}
      disabled={isGenerating}
      className={className}
      title={status === 'POSTED' ? 'Download invoice with FBR data' : 'Download invoice PDF'}
    >
      {isGenerating ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Download className="h-4 w-4" />
      )}
    </Button>
  );
}
