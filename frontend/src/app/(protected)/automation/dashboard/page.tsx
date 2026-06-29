'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { InvoiceTable } from '@/components/automation/InvoiceTable';
import InvoiceDetail from '@/components/automation/InvoiceDetail';
import { automationApi } from '@/services/automationApi';
import { toast } from 'sonner';
import { useAuth } from '@/providers/auth-provider';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [retryingInvoiceId, setRetryingInvoiceId] = useState<string | null>(null);
  const [pausingInvoiceId, setPausingInvoiceId] = useState<string | null>(null);
  const [resumingInvoiceId, setResumingInvoiceId] = useState<string | null>(null);

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
  const [filters, setFilters] = useState<{
    status: string | null;
    source: string | null;
    date_from: string | null;
    date_to: string | null;
    amount?: string | null;
    invoice_number?: string | null;
    customer?: string | null;
  }>({
    status: null,
    source: null,
    date_from: null,
    date_to: null,
  });

  useEffect(() => {
    loadInvoices();
  }, [pagination.page, filters]);

  const computeTotalAmount = (invoiceData: Record<string, any> | undefined | null): number => {
    if (!invoiceData) return 0;
    if (invoiceData.total_amount !== undefined && invoiceData.total_amount !== null) {
      return Number(invoiceData.total_amount);
    }
    const items = invoiceData.items;
    if (!items || !Array.isArray(items) || items.length === 0) return 0;
    return items.reduce((sum: number, item: any) => {
      const valueExclST = parseFloat(item.value_sales_excluding_st) || 0;
      const salesTax = parseFloat(item.sales_tax_applicable) || 0;
      const extraTax = parseFloat(item.extra_tax) || 0;
      const furtherTax = parseFloat(item.further_tax) || 0;
      const fedPayable = parseFloat(item.fed_payable) || 0;
      const discount = parseFloat(item.discount) || 0;
      return sum + valueExclST + salesTax + extraTax + furtherTax + fedPayable - discount;
    }, 0);
  };

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const response = await automationApi.getInvoiceList({
        page: pagination.page,
        page_size: pagination.page_size,
        status: filters.status || undefined,
        source: filters.source || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        invoice_number: filters.invoice_number || undefined,
        customer: filters.customer || undefined
      });

      let filteredInvoices = response.invoices;

      // Client-side amount filter (total_amount is computed from items, not stored in DB)
      if (filters.amount) {
        const term = filters.amount.toLowerCase();
        filteredInvoices = filteredInvoices.filter((inv: any) => {
          const amt = computeTotalAmount(inv.invoice_data);
          return amt.toString().includes(term) || amt.toLocaleString('en-US').includes(term);
        });
      }

      setInvoices(filteredInvoices);
      setPagination({
        total: filteredInvoices.length,
        page: pagination.page,
        page_size: pagination.page_size,
        total_pages: Math.ceil(filteredInvoices.length / pagination.page_size)
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

  const handlePause = async (invoiceId: string) => {
    try {
      setPausingInvoiceId(invoiceId);
      await automationApi.pauseInvoice(invoiceId);
      toast.success('Invoice paused. It will not be transferred until resumed.');
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to pause invoice');
    } finally {
      setPausingInvoiceId(null);
    }
  };

  const handleResume = async (invoiceId: string) => {
    try {
      setResumingInvoiceId(invoiceId);
      await automationApi.resumeInvoice(invoiceId);
      toast.success('Invoice resumed. It will be transferred in the next AI agent cycle.');
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to resume invoice');
    } finally {
      setResumingInvoiceId(null);
    }
  };

  const handleBulkPause = async (invoiceIds: string[]) => {
    try {
      const response = await automationApi.bulkPauseInvoices(invoiceIds);
      toast.success(`Successfully paused ${response.paused_count} invoice(s)`);
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to pause invoices');
    }
  };

  const handleBulkResume = async (invoiceIds: string[]) => {
    try {
      const response = await automationApi.bulkResumeInvoices(invoiceIds);
      toast.success(`Successfully resumed ${response.resumed_count} invoice(s)`);
      loadInvoices();
    } catch (error: any) {
      toast.error(error.message || 'Failed to resume invoices');
    }
  };

  const handleBulkDelete = async (invoiceIds: string[]) => {
    try {
      const response = await automationApi.bulkDeleteInvoices(invoiceIds);
      if (response.deleted_count > 0) {
        toast.success(`Successfully deleted ${response.deleted_count} invoice(s)`);
      } else {
        toast.error('No invoices were deleted.');
      }
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
    <div className="h-full flex flex-col pt-1 pb-2 max-w-[1600px] overflow-hidden">

      {/* <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
          Automation Dashboard
        </h1>
        <p className="text-[#6d7175] dark:text-[#8c9196]">
          Monitor invoice processing status and view detailed statistics
        </p>
      </div> */}

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
        <div className="flex-1 min-h-0">
          <InvoiceTable
            invoices={invoices}
            loading={loading}
            pagination={pagination}
            filters={filters}
            onFilterChange={handleFilterChange}
            onPageChange={handlePageChange}
            onInvoiceClick={setSelectedInvoiceId}
            onBack={() => router.push('/automation')}
            onRetry={handleRetry}
            retryingInvoiceId={retryingInvoiceId}
            onPause={handlePause}
            pausingInvoiceId={pausingInvoiceId}
            onResume={handleResume}
            resumingInvoiceId={resumingInvoiceId}
            onBulkDelete={handleBulkDelete}
            onBulkRetry={handleBulkRetry}
            onBulkPause={handleBulkPause}
            onBulkResume={handleBulkResume}
          />
        </div>
      )}
    </div>
  );
}
