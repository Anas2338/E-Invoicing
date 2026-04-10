'use client';

import { useEffect, useState } from 'react';
import { automationApi, AutomationInvoice, InvoiceListResponse } from '@/services/automationApi';

interface InvoiceListProps {
  onInvoiceClick?: (invoice: AutomationInvoice) => void;
}

export default function InvoiceList({ onInvoiceClick }: InvoiceListProps) {
  const [data, setData] = useState<InvoiceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-[#fef3c7] text-[#92400e] border-[#fde68a] dark:bg-[#451a03]/30 dark:text-[#fbbf24] dark:border-[#451a03]';
      case 'validated':
        return 'bg-[#e0e7ff] text-[#3730a3] border-[#c7d2fe] dark:bg-[#312e81]/30 dark:text-[#a5b4fc] dark:border-[#312e81]';
      case 'submitted':
        return 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]';
      case 'failed':
        return 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]';
      case 'expired':
        return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
      default:
        return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
    }
  };

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
              <option value="submitted">Submitted</option>
              <option value="failed">Failed</option>
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
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
                {data.invoices.map((invoice) => (
                  <tr
                    key={invoice.id}
                    onClick={() => onInvoiceClick?.(invoice)}
                    className="hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {invoice.invoice_number}
                    </td>
                    <td className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196]">
                      {invoice.scheduled_date}
                    </td>
                    <td className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196]">
                      {invoice.scheduled_time}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-lg border ${getStatusColor(
                          invoice.status
                        )}`}
                      >
                        {invoice.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#6d7175] dark:text-[#8c9196]">
                      {invoice.invoice_data?.source || 'excel_upload'}
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
