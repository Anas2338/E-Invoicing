'use client';

import { useEffect, useState } from 'react';
import { automationApi } from '@/services/automationApi';
import { Ban, Trash2, CheckCircle } from 'lucide-react';

interface InvoiceDetailProps {
  invoiceId: string;
  onClose?: () => void;
  onUpdate?: () => void;
}

interface InvoiceDetailData {
  invoice: any;
  logs: any[];
}

export default function InvoiceDetail({ invoiceId, onClose, onUpdate }: InvoiceDetailProps) {
  const [data, setData] = useState<InvoiceDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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

  const handleBlockInvoice = async () => {
    if (!data) return;

    try {
      setActionLoading(true);
      await automationApi.blockInvoice(invoiceId, 'Blocked by user from detail view');
      await loadInvoiceDetail();
      onUpdate?.();
      alert('Invoice blocked successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to block invoice');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnblockInvoice = async () => {
    if (!data) return;

    try {
      setActionLoading(true);
      await automationApi.unblockInvoice(invoiceId);
      await loadInvoiceDetail();
      onUpdate?.();
      alert('Invoice unblocked successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unblock invoice');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteInvoice = async () => {
    if (!data) return;

    try {
      setActionLoading(true);
      await automationApi.deleteInvoice(invoiceId);
      onUpdate?.();
      onClose?.();
      alert('Invoice deleted successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete invoice');
      setActionLoading(false);
    }
  };

  const getFBRValidationMessage = (fbrResponse: any): { status: string; message: string; isValid: boolean } => {
    try {
      const validationResponse = fbrResponse?.validationResponse;
      if (!validationResponse) {
        return { status: 'Unknown', message: 'No validation response available', isValid: false };
      }

      const status = validationResponse.status || '';
      const statusCode = validationResponse.statusCode || '';
      const error = validationResponse.error || '';

      // Check if valid
      const isValid = status === 'Valid' || statusCode === '00';

      if (isValid) {
        return { status: 'Valid', message: 'Invoice validated successfully by FBR', isValid: true };
      } else {
        const errorMsg = error || 'Validation failed';
        return { status: 'Invalid', message: errorMsg, isValid: false };
      }
    } catch (e) {
      return { status: 'Error', message: 'Failed to parse FBR response', isValid: false };
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

  const canBlock = invoice.status === 'pending' || invoice.status === 'failed';
  const canUnblock = invoice.status === 'blocked';
  const canDelete = ['pending', 'failed', 'expired', 'blocked'].includes(invoice.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3]">
          Invoice Details: {invoice.invoice_number}
        </h2>
        <div className="flex items-center gap-2">
          {onClose && (
            <button
              onClick={onClose}
              className="text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3] transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        {canBlock && (
          <button
            onClick={handleBlockInvoice}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 text-sm"
          >
            <Ban className="w-4 h-4" />
            {actionLoading ? 'Blocking...' : 'Block from FBR'}
          </button>
        )}
        {canUnblock && (
          <button
            onClick={handleUnblockInvoice}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
          >
            <CheckCircle className="w-4 h-4" />
            {actionLoading ? 'Unblocking...' : 'Unblock'}
          </button>
        )}
        {canDelete && (
          showDeleteConfirm ? (
            <div className="flex items-center gap-2">
              <button
                onClick={handleDeleteInvoice}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm"
              >
                {actionLoading ? 'Deleting...' : 'Confirm Delete'}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={actionLoading}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              <Trash2 className="w-4 h-4" />
              Delete Invoice
            </button>
          )
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
              {new Date(invoice.created_at).toLocaleString('en-US', { timeZone: 'Asia/Karachi' })}
            </div>
          </div>
          {invoice.processed_at && (
            <div>
              <div className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-1">Processed At</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {new Date(invoice.processed_at).toLocaleString('en-US', { timeZone: 'Asia/Karachi' })}
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
        <div className={`border rounded-xl p-4 ${getFBRValidationMessage(invoice.fbr_response).isValid ? 'bg-[#d1fae5] dark:bg-[#064e3b]/30 border-[#a7f3d0] dark:border-[#065f46]' : 'bg-[#fee2e2] dark:bg-[#7f1d1d]/30 border-[#fecaca] dark:border-[#7f1d1d]'}`}>
          <div className="flex items-center gap-2 mb-2">
            {getFBRValidationMessage(invoice.fbr_response).isValid ? (
              <CheckCircle className="h-5 w-5 text-[#065f46] dark:text-[#34d399]" />
            ) : (
              <svg className="h-5 w-5 text-[#991b1b] dark:text-[#f87171]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <h3 className={`text-sm font-semibold ${getFBRValidationMessage(invoice.fbr_response).isValid ? 'text-[#065f46] dark:text-[#34d399]' : 'text-[#991b1b] dark:text-[#f87171]'}`}>
              FBR Validation: {getFBRValidationMessage(invoice.fbr_response).status}
            </h3>
          </div>
          <p className={`text-sm ${getFBRValidationMessage(invoice.fbr_response).isValid ? 'text-[#065f46] dark:text-[#34d399]' : 'text-[#991b1b] dark:text-[#f87171]'}`}>
            {getFBRValidationMessage(invoice.fbr_response).message}
          </p>
        </div>
      )}

      {/* Invoice Data */}
      <div className="bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl p-6">
        <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">Invoice Information</h3>

        {/* Basic Invoice Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 pb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
          <div>
            <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Invoice Type</div>
            <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.invoice_data.invoice_type || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Invoice Date</div>
            <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.invoice_data.invoice_date || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Environment</div>
            <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
              {invoice.invoice_data.environment || 'N/A'}
            </div>
          </div>
        </div>

        {/* Seller Information */}
        <div className="mb-6 pb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
          <h4 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Seller Information</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Business Name</div>
              <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.seller_business_name || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">NTN/CNIC</div>
              <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.seller_ntn_cnic || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Province</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.seller_province || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Address</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.seller_address || 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Buyer Information */}
        <div className="mb-6 pb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
          <h4 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Buyer Information</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Business Name</div>
              <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.buyer_business_name || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">NTN/CNIC</div>
              <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.buyer_ntn_cnic || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Province</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.buyer_province || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Address</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.buyer_address || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Registration Type</div>
              <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                {invoice.invoice_data.buyer_registration_type || 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Items Details */}
        {invoice.invoice_data.items && invoice.invoice_data.items.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">
              Items ({invoice.invoice_data.items.length})
            </h4>
            <div className="space-y-4">
              {invoice.invoice_data.items.map((item: any, idx: number) => (
                <div key={idx} className="bg-[#f6f6f7] dark:bg-[#2e2e2e] p-4 rounded-xl border border-[#e1e3e5] dark:border-[#404040]">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
                        {item.product_description || 'N/A'}
                      </div>
                      <div className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                        HS Code: {item.hs_code || 'N/A'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.total_values?.toLocaleString() || '0'}
                      </div>
                      <div className="text-xs text-[#6d7175] dark:text-[#8c9196]">Total Value</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 text-xs">
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Quantity</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {item.quantity || 0} {item.uom || ''}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Tax Rate</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {item.tax_rate || 0}%
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Sales Tax</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.sales_tax_applicable?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Value Excl. ST</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.value_sales_excluding_st?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">ST Withheld</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.sales_tax_withheld_at_source?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Extra Tax</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.extra_tax?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Further Tax</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.further_tax?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">FED Payable</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.fed_payable?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Discount</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.discount?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Fixed/Retail Price</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        PKR {item.fixed_notified_value_or_retail_price?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">Sale Type</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {item.sale_type || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">SRO Schedule No</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {item.sro_schedule_no || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[#6d7175] dark:text-[#8c9196]">SRO Item Serial No</div>
                      <div className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {item.sro_item_serial_no || 'N/A'}
                      </div>
                    </div>
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
                  {new Date(log.timestamp).toLocaleString('en-US', { timeZone: 'Asia/Karachi' })}
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
