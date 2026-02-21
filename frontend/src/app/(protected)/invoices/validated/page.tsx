'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';

interface Invoice {
  id: string;
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: 'DRAFT' | 'VALIDATED' | 'POSTED' | 'FAILED';
  environment: 'SANDBOX' | 'PRODUCTION';
  invoiceType: string;
  createdAt: string;
}

export default function ValidatedInvoicesPage() {
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
      <div className="flex items-center justify-center min-h-screen">
        <p>Loading validated invoices...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Validated Invoices</h1>
          <p className="mt-2 text-gray-600">Manage your validated invoices ready for posting</p>
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