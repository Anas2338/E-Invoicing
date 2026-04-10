'use client';

import { useEffect, useState } from 'react';
import { automationApi } from '@/services/automationApi';

interface InvoiceDetailProps {
  invoiceId: string;
  onClose?: () => void;
}

interface InvoiceDetailData {
  invoice: any;
  logs: any[];
}

export default function InvoiceDetail({ invoiceId, onClose }: InvoiceDetailProps) {
  const [data, setData] = useState<InvoiceDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInvoiceDetail();
  }, [invoiceId]);

  const loadInvoiceDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await automationApi.getInvoiceDetail(invoiceId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load invoice details');
    } finally {
      setLoading(false);
    }
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

  const getActionColor = (action: string) => {
    switch (action) {
      case 'validate':
        return 'text-[#3730a3] dark:text-[#a5b4fc]';
      case 'submit':
        return 'text-[#1e40af] dark:text-[#60a5fa]';
      case 'retry':
        return 'text-[#c2410c] dark:text-[#fb923c]';
      default:
        return 'text-[#6d7175] dark:text-[#8c9196]';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-[#6d7175] dark:text-[#8c9196]">Loading invoice details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
        <p className="text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
        <button
          onClick={loadInvoiceDetail}
          className="mt-2 text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] underline font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { invoice, logs } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3]">
          Invoice Details: {invoice.invoice_number}
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3] transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* Status Card */}
      <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Status</div>
            <span
              className={`inline-flex px-3 py-1 text-sm font-semibold rounded-lg border ${getStatusColor(
                invoice.status
              )}`}
            >
              {invoice.status}
            </span>
          </div>
          <div>
            <div className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Scheduled Date & Time</div>
            <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.scheduled_date} at {invoice.scheduled_time}
            </div>
          </div>
          <div>
            <div className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Created At</div>
            <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
              {new Date(invoice.created_at).toLocaleString()}
            </div>
          </div>
          {invoice.processed_at && (
            <div>
              <div className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Processed At</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {new Date(invoice.processed_at).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Validation Errors */}
      {invoice.validation_errors && (
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <h3 className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59] mb-2">Validation Errors</h3>
          <p className="text-sm text-[#991b1b] dark:text-[#f87171]">{invoice.validation_errors}</p>
        </div>
      )}

      {/* FBR Response */}
      {invoice.fbr_response && (
        <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-6">
          <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">FBR Response</h3>
          <pre className="text-xs text-[#202223] dark:text-[#e3e3e3] bg-[#f6f6f7] dark:bg-[#2e2e2e] p-4 rounded-xl overflow-x-auto">
            {JSON.stringify(invoice.fbr_response, null, 2)}
          </pre>
        </div>
      )}

      {/* Invoice Data */}
      <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-6">
        <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Invoice Data</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-[#6d7175] dark:text-[#8c9196]">Seller</div>
            <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.invoice_data.seller_business_name}
            </div>
            <div className="text-[#6d7175] dark:text-[#8c9196] text-xs">
              NTN: {invoice.invoice_data.seller_ntn_cnic}
            </div>
          </div>
          <div>
            <div className="text-[#6d7175] dark:text-[#8c9196]">Buyer</div>
            <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.invoice_data.buyer_business_name}
            </div>
            <div className="text-[#6d7175] dark:text-[#8c9196] text-xs">
              NTN: {invoice.invoice_data.buyer_ntn_cnic}
            </div>
          </div>
        </div>

        {invoice.invoice_data.items && invoice.invoice_data.items.length > 0 && (
          <div className="mt-4">
            <div className="text-[#6d7175] dark:text-[#8c9196] mb-2">Items</div>
            <div className="space-y-2">
              {invoice.invoice_data.items.map((item: any, idx: number) => (
                <div key={idx} className="bg-[#f6f6f7] dark:bg-[#2e2e2e] p-3 rounded-xl">
                  <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                    {item.product_description}
                  </div>
                  <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Quantity: {item.quantity} {item.uom} | Total: PKR{' '}
                    {item.total_values?.toLocaleString()} | Tax: PKR{' '}
                    {item.sales_tax_applicable?.toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Activity Logs */}
      <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-6">
        <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Activity Logs</h3>
        {logs.length === 0 ? (
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">No activity logs yet</p>
        ) : (
          <div className="space-y-3">
            {logs.map((log: any) => (
              <div key={log.id} className="border-l-2 border-[#e1e3e5] dark:border-[#404040] pl-4">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${getActionColor(log.action)}`}>
                    {log.action}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-lg border ${
                      log.status === 'success'
                        ? 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]'
                        : 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]'
                    }`}
                  >
                    {log.status}
                  </span>
                </div>
                <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                  {new Date(log.timestamp).toLocaleString()}
                </div>
                {log.details && (
                  <div className="text-xs text-[#202223] dark:text-[#e3e3e3] mt-1 bg-[#f6f6f7] dark:bg-[#2e2e2e] p-2 rounded-xl">
                    {typeof log.details === 'string'
                      ? log.details
                      : JSON.stringify(log.details, null, 2)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
