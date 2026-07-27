'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SaleInvoiceForm } from '@/components/invoices/sale-invoice-form';
import { invoiceService } from '@/lib/api/api-client';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'react-toastify';

export default function EditInvoicePage() {
  const [invoice, setInvoice] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const router = useRouter();
  const params = useParams();
  const invoiceId = params.id as string;

  useEffect(() => {
    fetchInvoice();
  }, [invoiceId]);

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch invoice data from backend using the getInvoice method
      const invoice = await invoiceService.getInvoice(invoiceId);

      if (!invoice) {
        setError('Invoice not found');
        return;
      }

      // If invoice is POSTED, show in read-only mode instead of error
      if (invoice.status === 'POSTED') {
        setIsReadOnly(true);
      } else if (invoice.status !== 'DRAFT' && invoice.status !== 'VALIDATED' && invoice.status !== 'FAILED') {
        setError('Only draft, validated, or failed invoices can be edited. This invoice has status: ' + invoice.status);
        return;
      }

      setInvoice(invoice);
    } catch (err) {
      console.error('Error fetching invoice:', err);
      setError('Failed to load invoice. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (data: any) => {
    if (isReadOnly) return;
    setIsSubmitting(true);
    try {
      const response = await invoiceService.updateInvoice(invoiceId, data);
      if (response.success) {
        toast.success('Invoice updated successfully!');
        // Redirect to invoice history
        router.push('/invoices/history');
      } else {
        toast.error('Failed to update invoice.');
      }
    } catch (error) {
      console.error('Error updating invoice:', error);
      toast.error('Failed to update invoice. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    router.push('/invoices/history');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading invoice...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/invoices/history')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to History
          </Button>
        </div>
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-[#d72c0d] dark:text-[#ff6f59]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59]">Error</h3>
              <p className="mt-1 text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
          <SaleInvoiceForm
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isSubmitting={isSubmitting}
            initialData={invoice}
            isEditMode={!isReadOnly}
            isReadOnly={isReadOnly}
          />
    </div>
  );
}
