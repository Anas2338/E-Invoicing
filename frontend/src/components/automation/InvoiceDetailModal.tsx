'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { X, RefreshCw, CheckCircle, XCircle, Clock, FileText } from 'lucide-react';

interface Log {
  id: string;
  action: string;
  status: string;
  details: any;
  timestamp: string;
}

interface Invoice {
  invoice: {
    id: string;
    invoice_number: string;
    invoice_data: any;
    scheduled_date: string;
    scheduled_time: string;
    status: string;
    validation_errors?: string;
    fbr_response?: any;
    created_at: string;
    processed_at?: string;
  };
  logs: Log[];
}

interface InvoiceDetailModalProps {
  invoice: Invoice;
  onClose: () => void;
  onRetry: (invoiceId: string) => void;
}

export function InvoiceDetailModal({ invoice, onClose, onRetry }: InvoiceDetailModalProps) {
  const { invoice: inv, logs } = invoice;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'submitted':
        return <CheckCircle className="h-5 w-5 text-[#065f46] dark:text-[#34d399]" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-[#991b1b] dark:text-[#f87171]" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-[#92400e] dark:text-[#fbbf24]" />;
      case 'validated':
        return <CheckCircle className="h-5 w-5 text-[#3730a3] dark:text-[#a5b4fc]" />;
      default:
        return <FileText className="h-5 w-5 text-[#6d7175] dark:text-[#8c9196]" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      pending: { label: 'Pending', className: 'bg-[#fef3c7] text-[#92400e] dark:bg-[#451a03]/30 dark:text-[#fbbf24]' },
      validated: { label: 'Validated', className: 'bg-[#e0e7ff] text-[#3730a3] dark:bg-[#312e81]/30 dark:text-[#a5b4fc]' },
      submitted: { label: 'Submitted', className: 'bg-[#d1fae5] text-[#065f46] dark:bg-[#064e3b]/30 dark:text-[#34d399]' },
      failed: { label: 'Failed', className: 'bg-[#fee2e2] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:text-[#f87171]' },
      expired: { label: 'Expired', className: 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]' }
    };

    const config = statusConfig[status] || { label: status, className: 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]' };

    return (
      <span className={`px-3 py-1 text-sm font-semibold rounded-full ${config.className}`}>
        {config.label}
      </span>
    );
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Karachi'
    });
  };

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      validate: 'Validation',
      submit: 'FBR Submission',
      update_excel: 'Excel Update',
      retry: 'Retry'
    };
    return labels[action] || action;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-[#e1e3e5] dark:border-[#2e2e2e]">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-[#1a1a1a] border-b border-[#e1e3e5] dark:border-[#2e2e2e] px-6 py-4 flex items-center justify-between rounded-t-2xl">
          <div className="flex items-center gap-3">
            {getStatusIcon(inv.status)}
            <div>
              <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">{inv.invoice_number}</h2>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">Invoice Details</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {inv.status === 'pending' && (
              <Button onClick={() => onRetry(inv.id)} size="sm" variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            )}
            <button
              onClick={onClose}
              className="text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196] transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status and Dates */}
          <Card className="p-4">
            <h3 className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3] mb-4">Status Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Current Status</p>
                {getStatusBadge(inv.status)}
              </div>
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Scheduled For</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                  {new Date(inv.scheduled_date).toLocaleDateString()} {inv.scheduled_time}
                </p>
              </div>
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Created At</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">{formatDateTime(inv.created_at)}</p>
              </div>
              {inv.processed_at && (
                <div>
                  <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Processed At</p>
                  <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                    {formatDateTime(inv.processed_at)}
                  </p>
                </div>
              )}
            </div>
          </Card>

          {/* Invoice Data */}
          <Card className="p-4">
            <h3 className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3] mb-4">Invoice Data</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Customer Name</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                  {inv.invoice_data?.customer_name || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Items</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                  {inv.invoice_data?.items || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Amount</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                  PKR {inv.invoice_data?.amount?.toLocaleString() || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Tax</p>
                <p className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">
                  PKR {inv.invoice_data?.tax?.toLocaleString() || 'N/A'}
                </p>
              </div>
            </div>
          </Card>

          {/* Validation Errors */}
          {inv.validation_errors && (
            <Card className="p-4 bg-[#fef3f2] dark:bg-[#3d1e1e] border-[#fecdca] dark:border-[#5c2b2b]">
              <h3 className="text-lg font-bold text-[#d72c0d] dark:text-[#ff6f59] mb-2">Validation Errors</h3>
              <p className="text-sm text-[#d72c0d] dark:text-[#ff6f59]">{inv.validation_errors}</p>
            </Card>
          )}

          {/* FBR Response */}
          {inv.fbr_response && (
            <Card className="p-4 bg-[#d1fae5] dark:bg-[#064e3b]/30 border-[#a7f3d0] dark:border-[#065f46]">
              <h3 className="text-lg font-bold text-[#065f46] dark:text-[#34d399] mb-2">FBR Response</h3>
              <pre className="text-sm text-[#065f46] dark:text-[#34d399] overflow-x-auto">
                {JSON.stringify(inv.fbr_response, null, 2)}
              </pre>
            </Card>
          )}

          {/* Activity Logs */}
          <Card className="p-4">
            <h3 className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3] mb-4">Activity Log</h3>
            {logs.length === 0 ? (
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">No activity logs yet</p>
            ) : (
              <div className="space-y-3">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-start gap-3 p-3 bg-[#f6f6f7] dark:bg-[#2e2e2e] rounded-xl"
                  >
                    <div className="flex-shrink-0 mt-1">
                      {log.status === 'success' ? (
                        <CheckCircle className="h-5 w-5 text-[#065f46] dark:text-[#34d399]" />
                      ) : (
                        <XCircle className="h-5 w-5 text-[#991b1b] dark:text-[#f87171]" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                          {getActionLabel(log.action)}
                        </p>
                        <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">{formatDateTime(log.timestamp)}</p>
                      </div>
                      <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mt-1">
                        Status: <span className="font-medium">{log.status}</span>
                      </p>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <details className="mt-2">
                          <summary className="text-xs text-[#6d7175] dark:text-[#8c9196] cursor-pointer hover:text-[#202223] dark:hover:text-[#e3e3e3]">
                            View details
                          </summary>
                          <pre className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-2 overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
