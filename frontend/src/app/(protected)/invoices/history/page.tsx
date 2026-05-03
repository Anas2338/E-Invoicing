'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';
import { api, ApiError } from '@/lib/api';
import { Plus, Trash2, ArrowLeft, CheckCircle, RefreshCw } from 'lucide-react';
import { toast } from 'react-toastify';

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

export default function InvoiceHistoryPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [filteredInvoices, setFilteredInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkValidating, setBulkValidating] = useState(false);
  const [validatingInvoiceId, setValidatingInvoiceId] = useState<string | null>(null);
  const [postingInvoiceId, setPostingInvoiceId] = useState<string | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date>(new Date());

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogData, setDialogData] = useState<{
    success: boolean;
    title: string;
    message: string;
    invoiceNumber?: string;
    fbrNumber?: string;
    errors?: any[];
    invoiceId?: string;
  }>({
    success: false,
    title: '',
    message: '',
  });

  const statusOptions = [
    { value: 'all', label: 'All' },
    { value: 'DRAFT', label: 'Draft' },
    { value: 'VALIDATED', label: 'Validated' },
    { value: 'POSTED', label: 'Posted' },
    { value: 'FAILED', label: 'Failed' },
  ];

  useEffect(() => {
    fetchInvoices();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [invoices, searchTerm, statusFilter]);

  const fetchInvoices = async (isBackgroundRefresh = false, showRefreshIndicator = false) => {
    try {
      if (!isBackgroundRefresh) {
        setLoading(true);
      } else if (showRefreshIndicator) {
        setRefreshing(true);
      }
      setError(null);

      // Fetch unified invoices from backend (manual + automated)
      const response = await api.invoices.getUnifiedHistory({ page_size: 100 });

      // Transform backend data to match our interface
      const transformedInvoices: Invoice[] = response.invoices
        .map((invoice: any) => ({
          id: invoice.id,
          source: invoice.source,
          invoiceNumber: invoice.invoice_number || 'N/A',
          date: invoice.invoice_date || new Date(invoice.created_at).toISOString().split('T')[0],
          buyerName: invoice.buyer_business_name || 'N/A',
          sellerName: invoice.seller_business_name || 'N/A',
          totalAmount: invoice.total_amount || 0,
          status: invoice.status,
          environment: invoice.environment || '',
          invoiceType: invoice.invoice_type || 'Sale Invoice',
          createdAt: invoice.created_at,
          scheduledDate: invoice.scheduled_date,
          scheduledTime: invoice.scheduled_time,
        }));

      // Smart update: Only update state if data actually changed
      if (isBackgroundRefresh) {
        const hasChanges = JSON.stringify(transformedInvoices) !== JSON.stringify(invoices);
        if (hasChanges) {
          setInvoices(transformedInvoices);
          setLastRefreshTime(new Date());
        }
      } else {
        // Initial load or manual refresh - always update
        setInvoices(transformedInvoices);
        setLastRefreshTime(new Date());
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load invoices');
      }
      console.error('Error fetching invoices:', err);
    } finally {
      if (!isBackgroundRefresh) {
        setLoading(false);
      } else if (showRefreshIndicator) {
        setRefreshing(false);
      }
    }
  };

  const applyFilters = () => {
    let result = [...invoices];

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(invoice =>
        invoice.invoiceNumber.toLowerCase().includes(term) ||
        invoice.buyerName.toLowerCase().includes(term) ||
        invoice.sellerName.toLowerCase().includes(term) ||
        invoice.totalAmount.toString().includes(term)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(invoice => invoice.status === statusFilter);
    }

    setFilteredInvoices(result);
  };

  const handleViewInvoice = (id: string) => {
    router.push(`/invoices/${id}` as any);
  };

  const handleEditInvoice = (id: string) => {
    router.push(`/invoices/${id}/edit` as any);
  };

  const handleValidateInvoice = async (id: string) => {
    try {
      const invoice = invoices.find(inv => inv.id === id);
      if (!invoice) return;

      if (!confirm(`Validate invoice ${invoice.invoiceNumber} with FBR?`)) {
        return;
      }

      setValidatingInvoiceId(id);

      // Call validation API
      const response = await api.invoices.validate(id);

      // Show result in dialog
      setDialogData({
        success: response.success,
        title: response.success ? 'Validation Successful' : 'Validation Failed',
        message: response.message || (response.success ? 'Invoice validated successfully' : 'Validation failed'),
        invoiceNumber: invoice.invoiceNumber,
        errors: response.errors || [],
        invoiceId: id
      });
      setDialogOpen(true);

      // Refresh the invoice list if successful
      if (response.success) {
        await fetchInvoices();
      }
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Validation Error',
        message: err instanceof ApiError ? err.message : 'Failed to validate invoice. Please try again.',
        invoiceNumber: invoices.find(inv => inv.id === id)?.invoiceNumber,
        errors: [],
        invoiceId: id
      });
      setDialogOpen(true);
      console.error('Error validating invoice:', err);
    } finally {
      setValidatingInvoiceId(null);
    }
  };

  const handlePostInvoice = async (id: string) => {
    try {
      const invoice = invoices.find(inv => inv.id === id);
      if (!invoice) return;

      if (!confirm(`Post invoice ${invoice.invoiceNumber} to FBR?\n\nThis action will submit the invoice to the Federal Board of Revenue.`)) {
        return;
      }

      setPostingInvoiceId(id);

      // Call posting API
      const response = await api.invoices.post(id);

      // Show result in dialog
      setDialogData({
        success: response.success,
        title: response.success ? 'Invoice Posted Successfully' : 'Posting Failed',
        message: response.message || (response.success ? 'Invoice posted successfully' : 'Posting failed'),
        invoiceNumber: invoice.invoiceNumber,
        fbrNumber: response.fbr_invoice_number,
        errors: []
      });
      setDialogOpen(true);

      // Refresh the invoice list if successful
      if (response.success) {
        await fetchInvoices();
      }
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Posting Error',
        message: err instanceof ApiError ? err.message : 'Failed to post invoice. Please try again.',
        invoiceNumber: invoices.find(inv => inv.id === id)?.invoiceNumber,
        errors: []
      });
      setDialogOpen(true);
      console.error('Error posting invoice:', err);
    } finally {
      setPostingInvoiceId(null);
    }
  };

  const handleDeleteInvoice = async (id: string) => {
    try {
      const invoice = invoices.find(inv => inv.id === id);
      if (!invoice) return;

      if (!confirm(`Delete invoice ${invoice.invoiceNumber}?\n\nThis action cannot be undone.`)) {
        return;
      }

      // Call delete API
      await api.invoices.delete(id);

      // Show success toast
      toast.success(`Invoice ${invoice.invoiceNumber} deleted successfully`);

      // Refresh the invoice list
      await fetchInvoices();
    } catch (err) {
      // Show error toast
      toast.error(err instanceof ApiError ? err.message : 'Failed to delete invoice. Please try again.');
      console.error('Error deleting invoice:', err);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedInvoices.size === 0) return;

    const count = selectedInvoices.size;
    if (!confirm(`Delete ${count} selected invoice${count > 1 ? 's' : ''}?\n\nThis action cannot be undone.`)) {
      return;
    }

    setBulkDeleting(true);
    let successCount = 0;
    let failCount = 0;
    const errors: string[] = [];

    try {
      // Delete each selected invoice
      for (const invoiceId of Array.from(selectedInvoices)) {
        try {
          await api.invoices.delete(invoiceId);
          successCount++;
        } catch (err) {
          failCount++;
          const invoice = invoices.find(inv => inv.id === invoiceId);
          errors.push(`${invoice?.invoiceNumber || invoiceId}: ${err instanceof ApiError ? err.message : 'Failed'}`);
        }
      }

      // Show result toast
      if (failCount === 0) {
        toast.success(`Successfully deleted ${successCount} invoice${successCount !== 1 ? 's' : ''}`);
      } else {
        toast.warning(`Deleted ${successCount} invoice${successCount !== 1 ? 's' : ''}. Failed to delete ${failCount} invoice${failCount !== 1 ? 's' : ''}.`);
        // Log errors to console for debugging
        if (errors.length > 0) {
          console.error('Bulk delete errors:', errors);
        }
      }

      // Clear selection and refresh
      setSelectedInvoices(new Set());
      await fetchInvoices();
    } catch (err) {
      toast.error('An unexpected error occurred during bulk delete.');
      console.error('Error during bulk delete:', err);
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleBulkValidate = async () => {
    if (selectedInvoices.size === 0) return;

    // Filter to only include DRAFT and FAILED invoices
    const selectedInvoicesList = Array.from(selectedInvoices);
    const validatableInvoices = selectedInvoicesList.filter(id => {
      const invoice = invoices.find(inv => inv.id === id);
      return invoice?.status === 'DRAFT' || invoice?.status === 'FAILED';
    });

    const skippedCount = selectedInvoicesList.length - validatableInvoices.length;

    // If no validatable invoices, show message
    if (validatableInvoices.length === 0) {
      setDialogData({
        success: false,
        title: 'No Validatable Invoices Selected',
        message: 'All selected invoices are already validated or posted. Only DRAFT and FAILED invoices can be validated.',
        errors: []
      });
      setDialogOpen(true);
      return;
    }

    // Show confirmation with info about skipped invoices
    const confirmMessage = skippedCount > 0
      ? `Validate ${validatableInvoices.length} invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?\n\n${skippedCount} already validated/posted invoice${skippedCount > 1 ? 's' : ''} will be skipped.\n\nThis will validate each invoice one by one.`
      : `Validate ${validatableInvoices.length} selected invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?\n\nThis will validate each invoice one by one.`;

    if (!confirm(confirmMessage)) {
      return;
    }

    setBulkValidating(true);
    let successCount = 0;
    let failCount = 0;
    const errors: string[] = [];

    try {
      // Validate each DRAFT or FAILED invoice one by one
      for (const invoiceId of validatableInvoices) {
        const invoice = invoices.find(inv => inv.id === invoiceId);

        try {
          setValidatingInvoiceId(invoiceId);
          const response = await api.invoices.validate(invoiceId);

          if (response.success) {
            successCount++;
          } else {
            failCount++;
            errors.push(`${invoice?.invoiceNumber || invoiceId}: ${response.message || 'Validation failed'}`);
          }
        } catch (err) {
          failCount++;
          errors.push(`${invoice?.invoiceNumber || invoiceId}: ${err instanceof ApiError ? err.message : 'Failed'}`);
        }
      }

      // Show result dialog
      const skippedMessage = skippedCount > 0 ? ` ${skippedCount} invoice${skippedCount > 1 ? 's were' : ' was'} skipped (already validated/posted).` : '';
      setDialogData({
        success: failCount === 0,
        title: failCount === 0 ? 'Bulk Validation Successful' : 'Bulk Validation Completed with Errors',
        message: `Successfully validated ${successCount} invoice${successCount !== 1 ? 's' : ''}.${failCount > 0 ? ` Failed to validate ${failCount} invoice${failCount !== 1 ? 's' : ''}.` : ''}${skippedMessage}`,
        errors: errors.length > 0 ? errors.map(err => ({ message: err })) : []
      });
      setDialogOpen(true);

      // Clear selection and refresh
      setSelectedInvoices(new Set());
      await fetchInvoices();
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Bulk Validation Error',
        message: 'An unexpected error occurred during bulk validation.',
        errors: []
      });
      setDialogOpen(true);
      console.error('Error during bulk validation:', err);
    } finally {
      setBulkValidating(false);
      setValidatingInvoiceId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading invoices...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Invoice History</h1>
        </div>
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-[#d72c0d] dark:text-[#ff6f59]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59]">Error loading invoices</h3>
              <p className="mt-1 text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
            </div>
          </div>
        </div>
        <Button onClick={() => fetchInvoices()}>Try Again</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Back to Dashboard Button */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Invoice History</h1>
          <div className="flex items-center gap-2 mt-2">
            <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">View and manage your invoices</p>
            {refreshing && (
              <span className="flex items-center gap-1 text-xs text-[#008060] dark:text-[#00a876]">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Updating...
              </span>
            )}
          </div>
          <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
            Last updated: {lastRefreshTime.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="outline"
            onClick={() => fetchInvoices(true, true)}
            disabled={refreshing}
            className="w-full sm:w-auto"
            title="Refresh invoice list"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {selectedInvoices.size > 0 && (
            <>
              <Button
                variant="outline"
                onClick={handleBulkValidate}
                disabled={bulkValidating}
                className="w-full sm:w-auto border-[#008060] text-[#008060] hover:bg-[#008060] hover:text-white"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                {bulkValidating ? 'Validating...' : `Validate ${selectedInvoices.size} Selected`}
              </Button>
              <Button
                variant="destructive"
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="w-full sm:w-auto"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {bulkDeleting ? 'Deleting...' : `Delete ${selectedInvoices.size} Selected`}
              </Button>
            </>
          )}
          <Button onClick={() => router.push('/invoices/create')} className="w-full sm:w-auto">
            <Plus className="h-4 w-4 mr-2" />
            Create Invoice
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">Search</label>
            <Input
              type="text"
              placeholder="Search by invoice #, buyer, seller..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2">Status</label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-11 text-[#202223] dark:text-[#e3e3e3] shadow p-4">
                <span className="text-[#6d7175] dark:text-[#8c9196]">
                  {statusOptions.find(opt => opt.value === statusFilter)?.label || 'All'}
                </span>
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map(option => (
                  <SelectItem key={option.value} value={option.value} className="text-[#202223] dark:text-[#e3e3e3]">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button
              variant="outline"
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
              }}
              className="w-full"
            >
              Reset Filters
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-4">
          <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">Total Invoices</div>
          <div className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3]">{invoices.length}</div>
        </div>
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-4">
          <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">Draft</div>
          <div className="text-2xl font-bold text-[#92400e] dark:text-[#fbbf24]">
            {invoices.filter(inv => inv.status === 'DRAFT').length}
          </div>
        </div>
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-4">
          <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">Validated</div>
          <div className="text-2xl font-bold text-[#1e40af] dark:text-[#60a5fa]">
            {invoices.filter(inv => inv.status === 'VALIDATED').length}
          </div>
        </div>
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-4">
          <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">Posted</div>
          <div className="text-2xl font-bold text-[#065f46] dark:text-[#34d399]">
            {invoices.filter(inv => inv.status === 'POSTED').length}
          </div>
        </div>
      </div>

      {/* Invoice Table */}
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm">
        <InvoiceTable
          invoices={filteredInvoices}
          selectedInvoices={selectedInvoices}
          onSelectionChange={setSelectedInvoices}
          onView={handleViewInvoice}
          onEdit={handleEditInvoice}
          onValidate={handleValidateInvoice}
          onPost={handlePostInvoice}
          onDelete={handleDeleteInvoice}
          validatingInvoiceId={validatingInvoiceId}
          postingInvoiceId={postingInvoiceId}
        />
      </div>

      {/* Validation/Posting Result Dialog */}
      <ValidationResultDialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        success={dialogData.success}
        title={dialogData.title}
        message={dialogData.message}
        invoiceNumber={dialogData.invoiceNumber}
        fbrNumber={dialogData.fbrNumber}
        errors={dialogData.errors}
        invoiceId={dialogData.invoiceId}
        onRetry={dialogData.invoiceId ? () => handleValidateInvoice(dialogData.invoiceId!) : undefined}
      />
    </div>
  );
}