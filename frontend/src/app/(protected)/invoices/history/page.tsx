'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';
import { api, ApiError } from '@/lib/api';
import { Trash2, CheckCircle, RefreshCw, Printer, Loader2, Send } from 'lucide-react';
import { toast } from 'react-toastify';
import { useBulkOperation } from '@/contexts/BulkOperationContext';

interface Invoice {
  id: string;
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: string;
  environment: string;
  invoiceType: string;
  fbrReferenceNumber?: string;
  createdAt: string;
  scheduledDate?: string;
  scheduledTime?: string;
}

export default function InvoiceHistoryPage() {
  const router = useRouter();
  const { startOperation, hasActiveOperation, processingInvoiceIds } = useBulkOperation();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [filteredInvoices, setFilteredInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoiceNumberFilter, setInvoiceNumberFilter] = useState('');
  const [dateFromFilter, setDateFromFilter] = useState('');
  const [dateToFilter, setDateToFilter] = useState('');
  const [buyerNameFilter, setBuyerNameFilter] = useState('');
  const [amountFilter, setAmountFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('DRAFT');
  const [fbrRefFilter, setFbrRefFilter] = useState('');
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkValidating, setBulkValidating] = useState(false);
  const [bulkPosting, setBulkPosting] = useState(false);
  const [bulkPrinting, setBulkPrinting] = useState(false);
  const [validatingInvoiceId, setValidatingInvoiceId] = useState<string | null>(null);
  const [postingInvoiceId, setPostingInvoiceId] = useState<string | null>(null);
  const [deletingInvoiceId, setDeletingInvoiceId] = useState<string | null>(null);
  const [retryingLoad, setRetryingLoad] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date>(new Date());

  // Pagination state
  const PAGE_SIZE = 50;
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(filteredInvoices.length / PAGE_SIZE));
  const paginatedInvoices = filteredInvoices.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

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

  useEffect(() => {
    applyFilters();
    setCurrentPage(1);
  }, [invoices, invoiceNumberFilter, dateFromFilter, dateToFilter, buyerNameFilter, amountFilter, statusFilter, fbrRefFilter]);

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async (isBackgroundRefresh = false, showRefreshIndicator = false) => {
    try {
      if (!isBackgroundRefresh) {
        setLoading(true);
      } else if (showRefreshIndicator) {
        setRefreshing(true);
      }
      setError(null);

      // Fetch all invoices (no limit — loads everything)
      const response = await api.invoices.getUnifiedHistory({ page_size: 100000 });

      // Transform backend data to match our interface
      const transformedInvoices: Invoice[] = response.invoices
        .map((invoice: any) => ({
          id: invoice.id,
          invoiceNumber: invoice.invoice_number || 'N/A',
          date: invoice.invoice_date || new Date(invoice.created_at).toISOString().split('T')[0],
          buyerName: invoice.buyer_business_name || 'N/A',
          sellerName: invoice.seller_business_name || 'N/A',
          totalAmount: invoice.total_amount || 0,
          status: invoice.status,
          environment: invoice.environment || '',
          invoiceType: invoice.invoice_type || 'Sale Invoice',
          fbrReferenceNumber: invoice.fbr_reference_number || '',
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

    // Apply invoice number filter
    if (invoiceNumberFilter) {
      const term = invoiceNumberFilter.toLowerCase();
      result = result.filter(invoice =>
        invoice.invoiceNumber.toLowerCase().includes(term)
      );
    }

    // Apply date range filter (only when both From and To are selected)
    if (dateFromFilter && dateToFilter) {
      result = result.filter(invoice => invoice.date >= dateFromFilter && invoice.date <= dateToFilter);
    }

    // Apply buyer name filter
    if (buyerNameFilter) {
      const term = buyerNameFilter.toLowerCase();
      result = result.filter(invoice =>
        invoice.buyerName.toLowerCase().includes(term)
      );
    }

    // Apply amount filter
    if (amountFilter) {
      const term = amountFilter.toLowerCase();
      result = result.filter(invoice =>
        invoice.totalAmount.toString().includes(term)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(invoice => invoice.status === statusFilter);
    }

    // Apply income tax filter
    // Apply FBR reference filter
    if (fbrRefFilter) {
      const term = fbrRefFilter.toLowerCase();
      result = result.filter(invoice =>
        invoice.fbrReferenceNumber?.toLowerCase().includes(term)
      );
    }

    setFilteredInvoices(result);
  };

  const handleViewInvoice = (id: string) => {
    const invoice = invoices.find(inv => inv.id === id);
    if (invoice?.status === 'POSTED') {
      router.push(`/invoices/${id}` as any);
    } else {
      router.push(`/invoices/${id}/edit` as any);
    }
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

      // Log the exact FBR request payload to browser console
      console.group(`FBR Validation — ${invoice.invoiceNumber}`);
      console.log('FBR Request Payload:', JSON.stringify(response.fbr_request_payload, null, 2));
      console.log('FBR Response:', JSON.stringify(response.validation_result, null, 2));
      console.groupEnd();

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

      setDeletingInvoiceId(id);
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
    } finally {
      setDeletingInvoiceId(null);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedInvoices.size === 0) return;

    const count = selectedInvoices.size;
    if (!confirm(`Delete ${count} selected invoice${count > 1 ? 's' : ''}?\n\nThis action cannot be undone.`)) {
      return;
    }

    setBulkDeleting(true);

    try {
      // Single API call to delete all selected invoices at once
      const result = await api.invoices.bulkDelete(Array.from(selectedInvoices));

      // Show result toast
      if (result.failed && result.failed.length > 0) {
        toast.warning(`Deleted ${result.deleted_count} invoice${result.deleted_count !== 1 ? 's' : ''}. Failed: ${result.failed.length}.`);
        if (result.not_found_ids?.length > 0) {
          console.error('Bulk delete - not found:', result.not_found_ids);
        }
      } else if (result.deleted_count === 0) {
        toast.error('No invoices were deleted. They may have already been removed.');
      } else {
        toast.success(`Successfully deleted ${result.deleted_count} invoice${result.deleted_count !== 1 ? 's' : ''}`);
      }

      // Clear selection and refresh
      setSelectedInvoices(new Set());
      await fetchInvoices();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to delete invoices. Please try again.');
      console.error('Error during bulk delete:', err);
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleBulkValidate = async () => {
    if (selectedInvoices.size === 0) return;

    // Filter to include DRAFT and FAILED invoices (allows retry for failed ones)
    const selectedInvoicesList = Array.from(selectedInvoices);
    const validatableInvoices = selectedInvoicesList.filter(id => {
      const invoice = invoices.find(inv => inv.id === id);
      return invoice?.status === 'DRAFT' || invoice?.status === 'FAILED';
    });

    const skippedCount = selectedInvoicesList.length - validatableInvoices.length;

    // If no validatable invoices, show message
    if (validatableInvoices.length === 0) {
      toast.error('No DRAFT or FAILED invoices selected for validation.');
      return;
    }

    // Show confirmation with info about skipped invoices
    const confirmMessage = skippedCount > 0
      ? `Validate ${validatableInvoices.length} invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?\n\n${skippedCount} non-draft invoice${skippedCount > 1 ? 's' : ''} will be skipped.`
      : `Validate ${validatableInvoices.length} selected invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?`;

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      const response = await api.invoices.bulkValidateBackground(validatableInvoices);
      startOperation(response.task_id, 'bulk_validate', validatableInvoices.length, validatableInvoices);
      setSelectedInvoices(new Set());
      toast.success(`Validation started for ${validatableInvoices.length} invoice(s).`, { autoClose: 3000 });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to start validation.');
    }
  };

  const handleBulkPost = async () => {
    if (selectedInvoices.size === 0) return;

    // Only post VALIDATED invoices
    const selectedIds = Array.from(selectedInvoices);
    const postableInvoices = selectedIds.filter(id => {
      const invoice = invoices.find(inv => inv.id === id);
      return invoice?.status === 'VALIDATED' || invoice?.status === 'TRANSFERRED';
    });

    if (postableInvoices.length === 0) {
      toast.error('No validated invoices selected for posting');
      return;
    }

    // Determine environment from first postable invoice
    const firstInvoice = invoices.find(inv => inv.id === postableInvoices[0]);
    const environment = firstInvoice?.environment || 'SANDBOX';

    if (!confirm(`Post ${postableInvoices.length} validated invoice${postableInvoices.length > 1 ? 's' : ''} to FBR?\n\nEnvironment: ${environment}`)) {
      return;
    }

    try {
      const response = await api.invoices.bulkPostBackground(postableInvoices, environment);
      startOperation(response.task_id, 'bulk_post', postableInvoices.length, postableInvoices);
      setSelectedInvoices(new Set());
      toast.success(`Posting started for ${postableInvoices.length} invoice(s) to ${environment}.`, { autoClose: 3000 });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to start posting.');
    }
  };

  const handleBulkPrint = async () => {
    if (selectedInvoices.size === 0) return;

    const selectedInvoicesList = Array.from(selectedInvoices);

    if (!confirm(`Generate PDF for ${selectedInvoicesList.length} selected invoice${selectedInvoicesList.length > 1 ? 's' : ''}?`)) {
      return;
    }

    setBulkPrinting(true);

    try {
      // Helper function to get cookie value by name
      const getCookie = (name: string): string | null => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
          return parts.pop()?.split(';').shift() || null;
        }
        return null;
      };

      // Get CSRF token
      const csrfToken = getCookie('csrf_token') || sessionStorage.getItem('csrf_token');

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // Add CSRF token for POST request
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      // Call bulk PDF endpoint
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1'}/invoices/bulk-pdf`,
        {
          method: 'POST',
          headers,
          credentials: 'include', // Important: send httpOnly cookies
          body: JSON.stringify(selectedInvoicesList),
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

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.download = `invoices_bulk_${timestamp}.pdf`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      toast.success(`Successfully generated PDF for ${selectedInvoicesList.length} invoice${selectedInvoicesList.length > 1 ? 's' : ''}`);

      // Clear selection
      setSelectedInvoices(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate PDF');
      console.error('Error during bulk print:', err);
    } finally {
      setBulkPrinting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
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
        <Button onClick={async () => { setRetryingLoad(true); await fetchInvoices(); setRetryingLoad(false); }} disabled={retryingLoad}>
          {retryingLoad ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-2 sm:space-y-3">
      {/* Table + Actions Sidebar */}
      <div className="flex gap-0 flex-1 min-h-0">
        {/* Action Bar — vertical, left of table */}
        <div className="flex flex-col items-center gap-1 sm:gap-1.5 pt-2 sm:pt-32 pr-1 sm:pr-1.5 flex-shrink-0">
          {(() => {
            const selectedIds = Array.from(selectedInvoices);
            const selectedData = selectedIds
              .map(id => invoices.find(inv => inv.id === id))
              .filter((inv): inv is Invoice => inv !== undefined);

            const statusSet = new Set(selectedData.map(inv => inv.status));
            const hasSelection = selectedInvoices.size > 0;

            // Pure status sets (all selected invoices have the same status)
            const allDraft = hasSelection && statusSet.size === 1 && statusSet.has('DRAFT');
            const allValidated = hasSelection && statusSet.size === 1 && statusSet.has('VALIDATED');
            const allPosted = hasSelection && statusSet.size === 1 && statusSet.has('POSTED');

            // Mixed selection checks
            const hasDraft = statusSet.has('DRAFT');
            const hasValidated = statusSet.has('VALIDATED');
            const hasPosted = statusSet.has('POSTED');
            const hasFailed = statusSet.has('FAILED');

            // Conditional button visibility
            const showValidate = !hasSelection || (!allPosted && !allValidated && (allDraft || hasDraft || hasFailed));
            const showPost = hasSelection && allValidated;
            const showDelete = !hasSelection || (!allPosted && !hasPosted);

            return (
              <>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => fetchInvoices(true, true)}
                  disabled={refreshing}
                  className="h-8 w-8 border-orange-200"
                  title="Refresh"
                >
                  {refreshing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
                {showValidate && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleBulkValidate}
                    disabled={hasActiveOperation || selectedInvoices.size === 0}
                    className="h-8 w-8 border border-green-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    title={hasActiveOperation ? 'Operation in progress' : 'Validate selected'}
                  >
                    {bulkValidating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                  </Button>
                )}
                {showPost && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleBulkPost}
                    disabled={hasActiveOperation || selectedInvoices.size === 0}
                    className="h-8 w-8 border border-blue-300 text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    title={hasActiveOperation ? 'Operation in progress' : 'Post selected to FBR'}
                  >
                    {bulkPosting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleBulkPrint}
                  disabled={bulkPrinting || selectedInvoices.size === 0}
                  className="h-8 w-8 border-[#1e40af] text-[#1e40af] border-blue-300"
                  title="Print selected"
                >
                  {bulkPrinting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Printer className="h-4 w-4" />
                  )}
                </Button>
                {showDelete && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleBulkDelete}
                    disabled={bulkDeleting || selectedInvoices.size === 0}
                    className="h-8 w-8 text-red-500 border-red-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Delete selected"
                  >
                    {bulkDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </Button>
                )}
              </>
            );
          })()}
          {selectedInvoices.size > 0 && (
            <span className="text-[10px] text-[#6d7175] dark:text-[#8c9196] text-center">
              {selectedInvoices.size}
            </span>
          )}
        </div>

        {/* Invoice Table */}
        <div className="rounded-2xl flex flex-col gap-2 flex-1 min-h-0">
          <div className="flex-1 min-h-0">
            <InvoiceTable
            invoices={paginatedInvoices}
            totalFilteredCount={filteredInvoices.length}
            allFilteredSelectableIds={filteredInvoices
              .filter(inv => ['DRAFT', 'VALIDATED', 'FAILED', 'TRANSFERRED', 'POSTED'].includes(inv.status))
              .map(inv => inv.id)}
            selectedInvoices={selectedInvoices}
            onSelectionChange={setSelectedInvoices}
            onView={handleViewInvoice}
            onEdit={handleEditInvoice}
            onValidate={handleValidateInvoice}
            onPost={handlePostInvoice}
            onDelete={handleDeleteInvoice}
            validatingInvoiceId={validatingInvoiceId}
            postingInvoiceId={postingInvoiceId}
            deletingInvoiceId={deletingInvoiceId}
            processingInvoiceIds={processingInvoiceIds}
            invoiceNumberFilter={invoiceNumberFilter}
            onInvoiceNumberFilterChange={setInvoiceNumberFilter}
            dateFromFilter={dateFromFilter}
            onDateFromFilterChange={setDateFromFilter}
            dateToFilter={dateToFilter}
            onDateToFilterChange={setDateToFilter}
            buyerNameFilter={buyerNameFilter}
            onBuyerNameFilterChange={setBuyerNameFilter}
            amountFilter={amountFilter}
            onAmountFilterChange={setAmountFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            fbrRefFilter={fbrRefFilter}
            onFbrRefFilterChange={setFbrRefFilter}
            />
          </div>
          <div>
            {/* Pagination Controls */}
            {filteredInvoices.length > PAGE_SIZE && (
              <div className="flex items-center justify-between px-2 py-2 border-2 border-blue-600 rounded-4xl">
                <span className="text-xs text-black dark:text-neutral-400">
                  Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredInvoices.length)} of{' '}
                  {filteredInvoices.length} invoices
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}
                    className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-blue-600 text-blue-600 hover:bg-blue-100  disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Prev
                  </button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    // Show pages around current page
                    let pageNum: number;
                    if (totalPages <= 7) {
                      pageNum = i + 1;
                    } else if (currentPage <= 4) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 3) {
                      pageNum = totalPages - 6 + i;
                    } else {
                      pageNum = currentPage - 3 + i;
                    }
                    return (
                      <button
                        key={pageNum}
                        type="button"
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-7 h-7 text-xs font-semibold rounded-lg transition-colors ${
                          currentPage === pageNum
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-black hover:bg-blue-200 border border-blue-400'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  <button
                    type="button"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-blue-600 text-blue-600 hover:bg-blue-100  disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pagination Controls
      {filteredInvoices.length > PAGE_SIZE && (
        <div className="flex items-center justify-between px-2 py-2 border-2 border-blue-600 rounded-4xl">
          <span className="text-xs text-slate-500 dark:text-neutral-400">
            Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredInvoices.length)} of{' '}
            {filteredInvoices.length} invoices
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-neutral-700 text-slate-600 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              // Show pages around current page
              let pageNum: number;
              if (totalPages <= 7) {
                pageNum = i + 1;
              } else if (currentPage <= 4) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 3) {
                pageNum = totalPages - 6 + i;
              } else {
                pageNum = currentPage - 3 + i;
              }
              return (
                <button
                  key={pageNum}
                  type="button"
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-7 h-7 text-xs font-semibold rounded-lg transition-colors ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-600 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-800'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-neutral-700 text-slate-600 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )} */}

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
