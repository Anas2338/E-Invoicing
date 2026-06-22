'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';
import { api, ApiError } from '@/lib/api';
import { Trash2, CheckCircle, RefreshCw, Printer, Loader2 } from 'lucide-react';
import { toast } from 'react-toastify';

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
  const [statusFilter, setStatusFilter] = useState('all');
  const [fbrRefFilter, setFbrRefFilter] = useState('');
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkValidating, setBulkValidating] = useState(false);
  const [bulkPrinting, setBulkPrinting] = useState(false);
  const [validatingInvoiceId, setValidatingInvoiceId] = useState<string | null>(null);
  const [postingInvoiceId, setPostingInvoiceId] = useState<string | null>(null);
  const [deletingInvoiceId, setDeletingInvoiceId] = useState<string | null>(null);
  const [retryingLoad, setRetryingLoad] = useState(false);
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

  useEffect(() => {
    applyFilters();
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

      // Fetch all invoices (max page_size = 100 per backend limit)
      const response = await api.invoices.getUnifiedHistory({ page_size: 100 });

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

    // Filter to only include DRAFT invoices (skip VALIDATED, FAILED, POSTED)
    const selectedInvoicesList = Array.from(selectedInvoices);
    const validatableInvoices = selectedInvoicesList.filter(id => {
      const invoice = invoices.find(inv => inv.id === id);
      return invoice?.status === 'DRAFT';
    });

    const skippedCount = selectedInvoicesList.length - validatableInvoices.length;

    // If no validatable invoices, show message
    if (validatableInvoices.length === 0) {
      setDialogData({
        success: false,
        title: 'No Validatable Invoices Selected',
        message: 'Only DRAFT invoices can be validated.',
        errors: []
      });
      setDialogOpen(true);
      return;
    }

    // Show confirmation with info about skipped invoices
    const confirmMessage = skippedCount > 0
      ? `Validate ${validatableInvoices.length} invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?\n\n${skippedCount} non-draft invoice${skippedCount > 1 ? 's' : ''} will be skipped.\n\nThis will validate each invoice one by one.`
      : `Validate ${validatableInvoices.length} selected invoice${validatableInvoices.length > 1 ? 's' : ''} with FBR?\n\nThis will validate each invoice one by one.`;

    if (!confirm(confirmMessage)) {
      return;
    }

    setBulkValidating(true);
    let successCount = 0;
    let failCount = 0;
    const errors: string[] = [];

    try {
      // Validate each DRAFT invoice one by one
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
            const hasPostedSelected = selectedInvoices.size > 0 && Array.from(selectedInvoices).some(
              id => invoices.find(inv => inv.id === id)?.status === 'POSTED'
            );
            return (
              <>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => fetchInvoices(true, true)}
                  disabled={refreshing || hasPostedSelected}
                  className="h-8 w-8 border-orange-200"
                  title="Refresh"
                >
                  {refreshing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleBulkValidate}
                  disabled={bulkValidating || selectedInvoices.size === 0 || hasPostedSelected}
                  className="h-8 w-8 border border-green-300 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="Validate selected"
                >
                  {bulkValidating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                </Button>
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
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleBulkDelete}
                  disabled={bulkDeleting || selectedInvoices.size === 0 || hasPostedSelected}
                  className="h-8 w-8 text-red-500 border-red-300 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="Delete selected"
                >
                  {bulkDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                </Button>
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
        <div className="rounded-2xl flex-1 min-h-0 overflow-auto">
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
          deletingInvoiceId={deletingInvoiceId}
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
