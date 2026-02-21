'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';
import { api, ApiError } from '@/lib/api';
import { Plus, Trash2 } from 'lucide-react';
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

export default function InvoiceHistoryPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [filteredInvoices, setFilteredInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogData, setDialogData] = useState<{
    success: boolean;
    title: string;
    message: string;
    invoiceNumber?: string;
    fbrNumber?: string;
    errors?: any[];
  }>({
    success: false,
    title: '',
    message: '',
  });

  // Filter options
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

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all invoices from backend
      const response = await api.invoices.list({ size: 100 });

      // Transform backend data to match our interface
      const transformedInvoices: Invoice[] = response.data.map((invoice: any) => {
        // Calculate total amount from items (backend uses snake_case)
        const totalAmount = invoice.items?.reduce((sum: number, item: any) =>
          sum + (item.total_values || 0), 0
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
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load invoices');
      }
      console.error('Error fetching invoices:', err);
    } finally {
      setLoading(false);
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

      // Call validation API
      const response = await api.invoices.validate(id);

      // Show result in dialog
      setDialogData({
        success: response.success,
        title: response.success ? 'Validation Successful' : 'Validation Failed',
        message: response.message || (response.success ? 'Invoice validated successfully' : 'Validation failed'),
        invoiceNumber: invoice.invoiceNumber,
        errors: response.errors || []
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
        errors: []
      });
      setDialogOpen(true);
      console.error('Error validating invoice:', err);
    }
  };

  const handlePostInvoice = async (id: string) => {
    try {
      const invoice = invoices.find(inv => inv.id === id);
      if (!invoice) return;

      if (!confirm(`Post invoice ${invoice.invoiceNumber} to FBR?\n\nThis action will submit the invoice to the Federal Board of Revenue.`)) {
        return;
      }

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

      // Show success message
      setDialogData({
        success: true,
        title: 'Invoice Deleted',
        message: `Invoice ${invoice.invoiceNumber} has been deleted successfully.`,
        invoiceNumber: invoice.invoiceNumber,
        errors: []
      });
      setDialogOpen(true);

      // Refresh the invoice list
      await fetchInvoices();
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Delete Error',
        message: err instanceof ApiError ? err.message : 'Failed to delete invoice. Please try again.',
        invoiceNumber: invoices.find(inv => inv.id === id)?.invoiceNumber,
        errors: []
      });
      setDialogOpen(true);
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

      // Show result dialog
      setDialogData({
        success: failCount === 0,
        title: failCount === 0 ? 'Bulk Delete Successful' : 'Bulk Delete Completed with Errors',
        message: `Successfully deleted ${successCount} invoice${successCount !== 1 ? 's' : ''}.${failCount > 0 ? ` Failed to delete ${failCount} invoice${failCount !== 1 ? 's' : ''}.` : ''}`,
        errors: errors.length > 0 ? errors.map(err => ({ message: err })) : []
      });
      setDialogOpen(true);

      // Clear selection and refresh
      setSelectedInvoices(new Set());
      await fetchInvoices();
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Bulk Delete Error',
        message: 'An unexpected error occurred during bulk delete.',
        errors: []
      });
      setDialogOpen(true);
      console.error('Error during bulk delete:', err);
    } finally {
      setBulkDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading invoices...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Invoice History</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading invoices</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
        <Button onClick={fetchInvoices}>Try Again</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Invoice History</h1>
          <p className="mt-2 text-sm sm:text-base text-gray-600">View and manage all your invoices</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {selectedInvoices.size > 0 && (
            <Button
              variant="destructive"
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
              className="w-full sm:w-auto"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              {bulkDeleting ? 'Deleting...' : `Delete ${selectedInvoices.size} Selected`}
            </Button>
          )}
          <Button onClick={() => router.push('/invoices/create')} className="w-full sm:w-auto">
            <Plus className="h-4 w-4 mr-2" />
            Create Invoice
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <Input
              type="text"
              placeholder="Search by invoice #, buyer, seller..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-11 text-gray-700 shadow p-4">
                <span className="text-gray-500">
                  {statusOptions.find(opt => opt.value === statusFilter)?.label || 'All'}
                </span>
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map(option => (
                  <SelectItem key={option.value} value={option.value} className="text-gray-700">
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
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total Invoices</div>
          <div className="text-2xl font-bold text-gray-900">{invoices.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Draft</div>
          <div className="text-2xl font-bold text-yellow-600">
            {invoices.filter(inv => inv.status === 'DRAFT').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Validated</div>
          <div className="text-2xl font-bold text-blue-600">
            {invoices.filter(inv => inv.status === 'VALIDATED').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Posted</div>
          <div className="text-2xl font-bold text-green-600">
            {invoices.filter(inv => inv.status === 'POSTED').length}
          </div>
        </div>
      </div>

      {/* Invoice Table */}
      <div className="bg-white rounded-lg shadow">
        <InvoiceTable
          invoices={filteredInvoices}
          selectedInvoices={selectedInvoices}
          onSelectionChange={setSelectedInvoices}
          onView={handleViewInvoice}
          onEdit={handleEditInvoice}
          onValidate={handleValidateInvoice}
          onPost={handlePostInvoice}
          onDelete={handleDeleteInvoice}
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
      />
    </div>
  );
}