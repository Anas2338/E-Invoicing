'use client';

import { useEffect, useState } from 'react';
import { automationApi, AutomationInvoice, InvoiceListResponse } from '@/services/automationApi';
import { Ban, CheckSquare, Square, Trash2, RefreshCw } from 'lucide-react';

interface InvoiceListProps {
  onInvoiceClick?: (invoice: AutomationInvoice) => void;
}

export default function InvoiceList({ onInvoiceClick }: InvoiceListProps) {
  const [data, setData] = useState<InvoiceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [retryingInvoiceId, setRetryingInvoiceId] = useState<string | null>(null);

  // Filters
  const [status, setStatus] = useState<string>('');
  const [source, setSource] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadInvoices();
  }, [status, source, dateFrom, dateTo, page]);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await automationApi.getInvoiceList({
        status: status || undefined,
        source: source || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: 20,
      });
      setData(response);
      setSelectedInvoices(new Set()); // Clear selection on reload
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const resetFilters = () => {
    setStatus('');
    setSource('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  const toggleSelectAll = () => {
    if (!data) return;

    if (selectedInvoices.size === data.invoices.length) {
      setSelectedInvoices(new Set());
    } else {
      setSelectedInvoices(new Set(data.invoices.map(inv => inv.id)));
    }
  };

  const toggleSelectInvoice = (invoiceId: string) => {
    const newSelected = new Set(selectedInvoices);
    if (newSelected.has(invoiceId)) {
      newSelected.delete(invoiceId);
    } else {
      newSelected.add(invoiceId);
    }
    setSelectedInvoices(newSelected);
  };

  const handleBulkBlock = async () => {
    if (selectedInvoices.size === 0) return;

    try {
      setBulkActionLoading(true);
      await automationApi.bulkBlockInvoices(Array.from(selectedInvoices));
      await loadInvoices();
      alert(`Successfully blocked ${selectedInvoices.size} invoice(s)`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to block invoices');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleRetry = async (invoiceId: string) => {
    try {
      setRetryingInvoiceId(invoiceId);
      await automationApi.retryInvoice(invoiceId);
      await loadInvoices();
      alert('Invoice has been reset to pending status and will be retried by the AI Agent');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to retry invoice');
    } finally {
      setRetryingInvoiceId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-[#fef3c7] text-[#92400e] border-[#fde68a] dark:bg-[#451a03]/30 dark:text-[#fbbf24] dark:border-[#451a03]';
      case 'validated':
        return 'bg-[#e0e7ff] text-[#3730a3] border-[#c7d2fe] dark:bg-[#312e81]/30 dark:text-[#a5b4fc] dark:border-[#312e81]';
      case 'transferred':
        return 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]';
      case 'transfer_failed':
        return 'bg-[#ffedd5] text-[#7c2d12] border-[#fed7aa] dark:bg-[#431407]/30 dark:text-[#fb923c] dark:border-[#431407]';
      case 'failed':
        return 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]';
      case 'expired':
        return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
      case 'blocked':
        return 'bg-[#ffedd5] text-[#7c2d12] border-[#fed7aa] dark:bg-[#431407]/30 dark:text-[#fb923c] dark:border-[#431407]';
      default:
        return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
    }
  };

  const canBulkBlock = selectedInvoices.size > 0 && data?.invoices.some(inv =>
    selectedInvoices.has(inv.id) && inv.status === 'pending'
  );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="validated">Validated</option>
              <option value="transferred">Transferred</option>
              <option value="transfer_failed">Transfer Failed</option>
              <option value="failed">Failed</option>
              <option value="blocked">Blocked</option>
              <option value="expired">Expired</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
            >
              <option value="">All</option>
              <option value="excel_upload">Excel Upload</option>
              <option value="api">API</option>
              <option value="recurring">Recurring</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
            />
          </div>

          <div>
            <label className="block text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
            />
          </div>
        </div>

        <div className="mt-3 flex justify-end">
          <button
            onClick={resetFilters}
            className="text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedInvoices.size > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-900 dark:text-blue-200">
              {selectedInvoices.size} invoice(s) selected
            </span>
            <div className="flex gap-2">
              {canBulkBlock && (
                <button
                  onClick={handleBulkBlock}
                  disabled={bulkActionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 text-sm"
                >
                  <Ban className="w-4 h-4" />
                  {bulkActionLoading ? 'Blocking...' : 'Block Selected'}
                </button>
              )}
              <button
                onClick={() => setSelectedInvoices(new Set())}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
              >
                Clear Selection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invoice List */}
      {loading ? (
        <div className="flex items-center justify-center p-8">
          <div className="text-[#6d7175] dark:text-[#8c9196]">Loading invoices...</div>
        </div>
      ) : error ? (
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <p className="text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
          <button
            onClick={loadInvoices}
            className="mt-2 text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] underline font-semibold"
          >
            Retry
          </button>
        </div>
      ) : !data || data.invoices.length === 0 ? (
        <div className="bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#404040] rounded-xl p-8 text-center">
          <p className="text-[#6d7175] dark:text-[#8c9196]">No invoices found</p>
        </div>
      ) : (
        <>
          <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e] border-b border-[#e1e3e5] dark:border-[#404040]">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <button
                      onClick={toggleSelectAll}
                      className="flex items-center justify-center"
                    >
                      {selectedInvoices.size === data.invoices.length ? (
                        <CheckSquare className="w-5 h-5 text-[#008060] dark:text-[#00a876]" />
                      ) : (
                        <Square className="w-5 h-5 text-[#6d7175] dark:text-[#8c9196]" />
                      )}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Invoice Number
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Scheduled Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Scheduled Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Source
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
                {data.invoices.map((invoice) => (
                  <tr
                    key={invoice.id}
                    className="hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSelectInvoice(invoice.id);
                        }}
                        className="flex items-center justify-center"
                      >
                        {selectedInvoices.has(invoice.id) ? (
                          <CheckSquare className="w-5 h-5 text-[#008060] dark:text-[#00a876]" />
                        ) : (
                          <Square className="w-5 h-5 text-[#6d7175] dark:text-[#8c9196]" />
                        )}
                      </button>
                    </td>
                    <td
                      onClick={() => onInvoiceClick?.(invoice)}
                      className="px-4 py-3 text-sm text-[#202223] dark:text-[#e3e3e3] cursor-pointer"
                    >
                      {invoice.invoice_number}
                    </td>
                    <td
                      onClick={() => onInvoiceClick?.(invoice)}
                      className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196] cursor-pointer"
                    >
                      {invoice.scheduled_date}
                    </td>
                    <td
                      onClick={() => onInvoiceClick?.(invoice)}
                      className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196] cursor-pointer"
                    >
                      {invoice.scheduled_time}
                    </td>
                    <td
                      onClick={() => onInvoiceClick?.(invoice)}
                      className="px-4 py-3 cursor-pointer"
                    >
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-lg border ${getStatusColor(
                          invoice.status
                        )}`}
                      >
                        {invoice.status}
                      </span>
                    </td>
                    <td
                      onClick={() => onInvoiceClick?.(invoice)}
                      className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196] cursor-pointer"
                    >
                      {invoice.invoice_data?.source || 'excel_upload'}
                    </td>
                    <td className="px-4 py-3">
                      {invoice.status === 'pending' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRetry(invoice.id);
                          }}
                          disabled={retryingInvoiceId === invoice.id}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#0070f3] hover:text-white hover:bg-[#0070f3] border border-[#0070f3] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <RefreshCw className={`w-3 h-3 ${retryingInvoiceId === invoice.id ? 'animate-spin' : ''}`} />
                          {retryingInvoiceId === invoice.id ? 'Retrying...' : 'Retry'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">
              Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, data.total)} of{' '}
              {data.total} invoices
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-3 py-1 text-sm border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.total_pages}
                className="px-3 py-1 text-sm border-2 border-[#c9cccf] dark:border-[#2e2e2e] bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
