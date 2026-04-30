'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { ArrowLeft } from 'lucide-react';

interface Invoice {
  id: string;
  source: 'manual' | 'automated';
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: string;
  environment: string;
  invoiceType: string;
  createdAt: string;
  scheduledDate?: string;
  scheduledTime?: string;
}

export default function ValidatedInvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);

  useEffect(() => {
    fetchValidatedInvoices();
  }, []);

  const fetchValidatedInvoices = async () => {
    try {
      setLoading(true);
      // Fetch only validated invoices
      const response = await api.invoices.list({
        status: 'VALIDATED',
        size: 50
      });

      // Transform backend data to match our interface
      const transformedInvoices: Invoice[] = response.data.map((invoice: any) => {
        const totalAmount = invoice.items?.reduce((sum: number, item: any) =>
          sum + (item.totalValues || 0), 0
        ) || 0;

        return {
          id: invoice.id,
          source: 'manual' as const,
          invoiceNumber: invoice.external_id || 'N/A',
          date: invoice.invoice_date || new Date(invoice.created_at).toISOString().split('T')[0],
          buyerName: invoice.buyer_business_name || 'N/A',
          sellerName: invoice.seller_business_name || 'N/A',
          totalAmount: totalAmount,
          status: invoice.status,
          environment: invoice.environment,
          invoiceType: invoice.invoice_type || 'Sale Invoice',
          createdAt: invoice.created_at,
        };
      });

      setInvoices(transformedInvoices);
    } catch (error) {
      console.error('Error fetching validated invoices:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkPost = async () => {
    if (selectedInvoices.length === 0) return;

    try {
      // Post each selected invoice
      const results = await Promise.allSettled(
        selectedInvoices.map(id => api.invoices.post(id))
      );

      const successCount = results.filter(r => r.status === 'fulfilled').length;

      // Refresh the list after bulk action
      await fetchValidatedInvoices();

      // Show success message
      toast.success(`${successCount} out of ${selectedInvoices.length} invoices posted successfully`);
      setSelectedInvoices([]);
    } catch (error) {
      console.error('Error posting invoices:', error);
      toast.error('Failed to post invoices. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading validated invoices...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Back to History Button */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/invoices/history')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to History
        </Button>
      </div>

      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Validated Invoices</h1>
          <p className="mt-2 text-[#6d7175] dark:text-[#8c9196]">Manage your validated invoices ready for posting</p>
        </div>
        <div>
          {selectedInvoices.length > 0 && (
            <Button onClick={handleBulkPost}>
              Bulk Post ({selectedInvoices.length})
            </Button>
          )}
        </div>
      </div>

      <InvoiceTable
        invoices={invoices}
      />
    </div>
  );
}