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
