'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronLeft, ChevronRight, Download, Eye, RefreshCw, Printer, FileText } from 'lucide-react';
import { automationApi } from '@/services/automationApi';
import { toast } from 'sonner';
import { BatchPrintProgress } from './BatchPrintProgress';
import { PrintInvoiceButton } from './PrintInvoiceButton';

interface Invoice {
  id: string;
  invoice_number: string;
  invoice_data: any;
  scheduled_date: string;
  scheduled_time: string;
  status: string;
  source?: string;
  validation_errors?: string;
  created_at: string;
  processed_at?: string;
  excel_upload_session_id: string;
}

interface InvoiceTableProps {
  invoices: Invoice[];
  loading: boolean;
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  filters: {
    status: string | null;
    source: string | null;
    date_from: string | null;
    date_to: string | null;
  };
  onFilterChange: (filters: any) => void;
  onPageChange: (page: number) => void;
  onInvoiceClick: (invoiceId: string) => void;
  onDownload: (sessionId: string) => void;
  onRetry?: (invoiceId: string) => void;
}

export function InvoiceTable({
  invoices,
  loading,
  pagination,
  filters,
  onFilterChange,
  onPageChange,
  onInvoiceClick,
  onDownload,
  onRetry
}: InvoiceTableProps) {
  const [localFilters, setLocalFilters] = useState(filters);
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [isPrintingBatch, setIsPrintingBatch] = useState(false);

  const handleApplyFilters = () => {
    onFilterChange(localFilters);
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      status: null,
      source: null,
      date_from: null,
      date_to: null
    };
    setLocalFilters(clearedFilters);
    onFilterChange(clearedFilters);
  };

  // Checkbox selection handlers
  const handleSelectAll = () => {
    if (selectedInvoices.size === transferredInvoices.length) {
      // Deselect all
      setSelectedInvoices(new Set());
    } else {
      // Select all transferred invoices
      setSelectedInvoices(new Set(transferredInvoices.map(inv => inv.id)));
    }
  };

  const handleSelectInvoice = (invoiceId: string) => {
    const newSelection = new Set(selectedInvoices);
    if (newSelection.has(invoiceId)) {
      newSelection.delete(invoiceId);
    } else {
      newSelection.add(invoiceId);
    }
    setSelectedInvoices(newSelection);
  };

  // Filter transferred invoices (only transferred invoices can be printed)
  const transferredInvoices = invoices.filter(inv => inv.status === 'transferred');

  // Batch print handler
  const handleBatchPrint = async () => {
    if (selectedInvoices.size === 0) {
      toast.error('Please select at least one invoice to print');
      return;
    }

    if (selectedInvoices.size > 50) {
      toast.error('Cannot print more than 50 invoices at once');
      return;
    }

    setIsPrintingBatch(true);

    try {
      // Convert Set to Array (preserves selection order)
      const invoiceIds = Array.from(selectedInvoices);

      // Generate batch PDF
      const pdfBlob = await automationApi.printBatchInvoices(invoiceIds);

      // Create download link
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.download = `batch_invoices_${selectedInvoices.size}_${timestamp}.pdf`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      toast.success(`Batch PDF with ${selectedInvoices.size} invoices downloaded successfully`);

      // Clear selection after successful download
      setSelectedInvoices(new Set());
    } catch (error) {
      console.error('Batch PDF generation failed:', error);

      const errorMessage = error instanceof Error
        ? error.message
        : 'Failed to generate batch PDF';

      toast.error(errorMessage);
    } finally {
      setIsPrintingBatch(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      pending: { label: 'Pending', className: 'bg-[#fef3c7] text-[#92400e] dark:bg-[#451a03]/30 dark:text-[#fbbf24]' },
      validated: { label: 'Validated', className: 'bg-[#e0e7ff] text-[#3730a3] dark:bg-[#312e81]/30 dark:text-[#a5b4fc]' },
      transferred: { label: 'Transferred', className: 'bg-[#d1fae5] text-[#065f46] dark:bg-[#064e3b]/30 dark:text-[#34d399]' },
      transfer_failed: { label: 'Transfer Failed', className: 'bg-[#ffedd5] text-[#7c2d12] dark:bg-[#431407]/30 dark:text-[#fb923c]' },
      failed: { label: 'Failed', className: 'bg-[#fee2e2] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:text-[#f87171]' },
      blocked: { label: 'Blocked', className: 'bg-[#ffedd5] text-[#7c2d12] dark:bg-[#431407]/30 dark:text-[#fb923c]' },
      expired: { label: 'Expired', className: 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]' }
    };

    const config = statusConfig[status] || { label: status, className: 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]' };

    return (
      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${config.className}`}>
        {config.label}
      </span>
    );
  };

  const getSourceBadge = (source: string) => {
    const sourceConfig: Record<string, { label: string; className: string; icon: string }> = {
      excel_upload: { label: 'Excel', className: 'bg-[#dbeafe] text-[#1e40af] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa]', icon: '📊' },
      api: { label: 'API', className: 'bg-[#e0e7ff] text-[#3730a3] dark:bg-[#312e81]/30 dark:text-[#a5b4fc]', icon: '🔌' },
      recurring: { label: 'Recurring', className: 'bg-[#ccfbf1] text-[#115e59] dark:bg-[#134e4a]/30 dark:text-[#5eead4]', icon: '🔄' }
    };

    const config = sourceConfig[source] || { label: source, className: 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]', icon: '📄' };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${config.className}`}>
        <span>{config.icon}</span>
        {config.label}
      </span>
    );
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'Asia/Karachi'
    });
  };

  const formatTime = (timeStr: string) => {
    // Handle time format like "10:00:00"
    const [hours, minutes] = timeStr.split(':');
    return `${hours}:${minutes}`;
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
              Status
            </label>
            <Select
              value={localFilters.status || 'all'}
              onValueChange={(value) =>
                setLocalFilters({ ...localFilters, status: value === 'all' ? null : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="validated">Validated</SelectItem>
                <SelectItem value="transferred">Transferred</SelectItem>
                <SelectItem value="transfer_failed">Transfer Failed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
              Source
            </label>
            <Select
              value={localFilters.source || 'all'}
              onValueChange={(value) =>
                setLocalFilters({ ...localFilters, source: value === 'all' ? null : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                <SelectItem value="excel_upload">Excel Upload</SelectItem>
                <SelectItem value="api">API</SelectItem>
                <SelectItem value="recurring">Recurring</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
              Date From
            </label>
            <Input
              type="date"
              value={localFilters.date_from || ''}
              onChange={(e) =>
                setLocalFilters({ ...localFilters, date_from: e.target.value || null })
              }
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
              Date To
            </label>
            <Input
              type="date"
              value={localFilters.date_to || ''}
              onChange={(e) =>
                setLocalFilters({ ...localFilters, date_to: e.target.value || null })
              }
            />
          </div>

          <div className="flex gap-2">
            <Button onClick={handleApplyFilters} size="sm">
              Apply
            </Button>
            <Button onClick={handleClearFilters} variant="outline" size="sm">
              Clear
            </Button>
          </div>
        </div>

        {/* Batch Print Button - Only show when invoices are selected */}
        {selectedInvoices.size > 0 && (
          <div className="flex items-center justify-between bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <div className="text-sm text-blue-900 dark:text-blue-100">
              <span className="font-semibold">
                {selectedInvoices.size} invoice{selectedInvoices.size !== 1 ? 's' : ''} selected
              </span>
            </div>
            <Button
              onClick={handleBatchPrint}
              disabled={isPrintingBatch}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Printer className="h-4 w-4 mr-2" />
              {isPrintingBatch ? 'Generating...' : 'Print Selected'}
            </Button>
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="text-center py-8 text-[#6d7175] dark:text-[#8c9196]">Loading invoices...</div>
          ) : invoices.length === 0 ? (
            <div className="text-center py-8 text-[#6d7175] dark:text-[#8c9196]">No invoices found</div>
          ) : (
            <table className="min-w-full divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
              <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e]">
                <tr>
                  {transferredInvoices.length > 0 && (
                    <th className="px-6 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selectedInvoices.size === transferredInvoices.length && transferredInvoices.length > 0}
                        onChange={handleSelectAll}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        title="Select all transferred invoices"
                      />
                    </th>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Invoice Number
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Scheduled
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-[#1a1a1a] divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
                {invoices.map((invoice) => {
                  const isTransferred = invoice.status === 'transferred';
                  const isSelected = selectedInvoices.has(invoice.id);

                  return (
                    <tr key={invoice.id} className="hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors duration-150">
                      {transferredInvoices.length > 0 && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          {isTransferred ? (
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleSelectInvoice(invoice.id)}
                              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                          ) : (
                            <div className="w-4 h-4" />
                          )}
                        </td>
                      )}
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {invoice.invoice_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-[#6d7175] dark:text-[#8c9196]">
                        {invoice.invoice_data?.customer_name || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-[#6d7175] dark:text-[#8c9196]">
                        {formatDate(invoice.scheduled_date)} {formatTime(invoice.scheduled_time)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getSourceBadge(invoice.source || 'excel_upload')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(invoice.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-[#6d7175] dark:text-[#8c9196]">
                        <div className="flex gap-2">
                          <Button
                            onClick={() => onInvoiceClick(invoice.id)}
                            variant="ghost"
                            size="sm"
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                          {invoice.status === 'pending' && onRetry && (
                            <Button
                              onClick={() => onRetry(invoice.id)}
                              variant="ghost"
                              size="sm"
                              className="text-[#0070f3] hover:text-[#0070f3] hover:bg-[#0070f3]/10"
                            >
                              <RefreshCw className="h-4 w-4 mr-1" />
                              Retry
                            </Button>
                          )}
                          {invoice.status === 'transferred' && (
                            <PrintInvoiceButton
                              invoiceId={invoice.id}
                              invoiceNumber={invoice.invoice_number}
                              status={invoice.status}
                            />
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {!loading && invoices.length > 0 && (
          <div className="flex items-center justify-between border-t border-[#e1e3e5] dark:border-[#2e2e2e] pt-4">
            <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">
              Showing {(pagination.page - 1) * pagination.page_size + 1} to{' '}
              {Math.min(pagination.page * pagination.page_size, pagination.total)} of{' '}
              {pagination.total} results
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => onPageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                variant="outline"
                size="sm"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
              </div>
              <Button
                onClick={() => onPageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.total_pages}
                variant="outline"
                size="sm"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Batch Print Progress Indicator (for 20+ invoices) */}
      {selectedInvoices.size >= 20 && (
        <BatchPrintProgress
          isGenerating={isPrintingBatch}
          invoiceCount={selectedInvoices.size}
        />
      )}
    </Card>
  );
}
