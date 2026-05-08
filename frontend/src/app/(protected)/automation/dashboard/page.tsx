'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import AutomationDashboard from '@/components/automation/AutomationDashboard';
import { InvoiceTable } from '@/components/automation/InvoiceTable';
import InvoiceDetail from '@/components/automation/InvoiceDetail';
import { automationApi } from '@/services/automationApi';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/providers/auth-provider';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [retryingInvoiceId, setRetryingInvoiceId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && user && !user.automation_enabled) {
      toast.error('Automation access not enabled. Please contact your administrator.');
      router.push('/dashboard');
    }
  }, [user, authLoading, router]);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user?.automation_enabled) {
    return null;
  }
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0
  });
  const [filters, setFilters] = useState({
    status: null,
    source: null,
    date_from: null,
    date_to: null
  });

  useEffect(() => {
    loadInvoices();
  }, [pagination.page, filters]);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const response = await automationApi.getInvoiceList({
        page: pagination.page,
        page_size: pagination.page_size,
        status: filters.status || undefined,
        source: filters.source || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined
      });
      setInvoices(response.invoices);
      setPagination({
        total: response.total,
        page: response.page,
        page_size: response.page_size,
        total_pages: response.total_pages
      });
    } catch (error) {
      toast.error('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters: any) => {
    setFilters(newFilters);
    setPagination({ ...pagination, page: 1 });
  };

  const handlePageChange = (page: number) => {
    setPagination({ ...pagination, page });
  };

  const handleDownload = async (sessionId: string) => {
    try {
      const blob = await automationApi.downloadExcel(sessionId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice_session_${sessionId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      toast.success('Excel file downloaded successfully');
    } catch (error) {
      toast.error('Failed to download Excel file');
    }
  };

  const handleRetry = async (invoiceId: string) => {
    try {
      setRetryingInvoiceId(invoiceId);
      const response = await automationApi.retryInvoice(invoiceId);
      toast.success('Invoice queued for retry. AI agent will process it in the next cycle.');
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to retry invoice');
    } finally {
      setRetryingInvoiceId(null);
    }
  };

  const handleBulkDelete = async (invoiceIds: string[]) => {
    try {
      const response = await automationApi.bulkDeleteInvoices(invoiceIds);
      toast.success(`Successfully deleted ${response.deleted_count} invoice(s)`);
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete invoices');
    }
  };

  const handleBulkRetry = async (invoiceIds: string[]) => {
    try {
      const response = await automationApi.bulkRetryInvoices(invoiceIds);
      toast.success(`Successfully queued ${response.retried_count} invoice(s) for retry`);
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to retry invoices');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/automation')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Automation
        </Button>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
          Automation Dashboard
        </h1>
        <p className="text-[#6d7175] dark:text-[#8c9196]">
          Monitor invoice processing status and view detailed statistics
        </p>
      </div>

      {selectedInvoiceId ? (
        <div className="mb-8">
          <button
            onClick={() => setSelectedInvoiceId(null)}
            className="mb-4 text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold flex items-center gap-1"
          >
            ← Back to list
          </button>
          <InvoiceDetail
            invoiceId={selectedInvoiceId}
            onClose={() => setSelectedInvoiceId(null)}
            onUpdate={loadInvoices}
          />
        </div>
      ) : (
        <div className="space-y-8">
          <AutomationDashboard />
          <InvoiceTable
            invoices={invoices}
            loading={loading}
            pagination={pagination}
            filters={filters}
            onFilterChange={handleFilterChange}
            onPageChange={handlePageChange}
            onInvoiceClick={setSelectedInvoiceId}
            onDownload={handleDownload}
            onRetry={handleRetry}
            retryingInvoiceId={retryingInvoiceId}
            onBulkDelete={handleBulkDelete}
            onBulkRetry={handleBulkRetry}
          />
        </div>
      )}
    </div>
  );
}
