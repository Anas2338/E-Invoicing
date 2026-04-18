'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { invoiceService } from '@/lib/api/api-client';
import { ArrowLeft, Edit, CheckCircle, Send } from 'lucide-react';

export default function InvoiceDetailsPage() {
  const [invoice, setInvoice] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const params = useParams();
  const invoiceId = params.id as string;

  useEffect(() => {
    fetchInvoice();
  }, [invoiceId]);

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      setError(null);

      const invoice = await invoiceService.getInvoice(invoiceId);

      if (!invoice) {
        setError('Invoice not found');
        return;
      }

      setInvoice(invoice);
    } catch (err) {
      console.error('Error fetching invoice:', err);
      setError('Failed to load invoice. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT': return 'bg-[#fef3c7] text-[#92400e] border-[#fde68a] dark:bg-[#451a03]/30 dark:text-[#fbbf24] dark:border-[#451a03]';
      case 'VALIDATED': return 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa] dark:border-[#1e3a8a]';
      case 'POSTED': return 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]';
      case 'FAILED': return 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]';
      default: return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
    }
  };

  const getEnvironmentColor = (env: string) => {
    return env === 'PRODUCTION'
      ? 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]'
      : 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa] dark:border-[#1e3a8a]';
  };

  const formatStatus = (status: string) => {
    return status.charAt(0) + status.slice(1).toLowerCase();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading invoice...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/invoices/history')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to History
          </Button>
        </div>
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-[#d72c0d] dark:text-[#ff6f59]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59]">Error</h3>
              <p className="mt-1 text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
            </div>
          </div>
        </div>
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
        <div className="flex-1">
          <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Invoice Details</h1>
          <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
            Invoice #{invoice?.external_id || invoice?.id}
          </p>
        </div>
        <div className="flex gap-2">
          {invoice?.status === 'DRAFT' && (
            <Button
              variant="outline"
              onClick={() => router.push(`/invoices/${invoiceId}/edit`)}
              className="flex-1 sm:flex-none"
            >
              <Edit className="h-4 w-4 mr-2" />
              Edit Invoice
            </Button>
          )}
        </div>
      </div>

      {/* Status and Environment */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="flex-1">
          <CardContent className="pt-6">
            <div className="text-sm text-gray-600 mb-2">Status</div>
            <Badge className={`${getStatusColor(invoice?.status)} border text-base px-3 py-1`}>
              {formatStatus(invoice?.status)}
            </Badge>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="pt-6">
            <div className="text-sm text-gray-600 mb-2">Environment</div>
            <Badge className={`${getEnvironmentColor(invoice?.environment)} border text-base px-3 py-1`}>
              {invoice?.environment}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Invoice Information */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Invoice Number</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.external_id || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Invoice Date</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">
                {invoice?.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  timeZone: 'Asia/Karachi'
                }) : 'N/A'}
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Invoice Type</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.invoice_type || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Created At</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">
                {invoice?.created_at ? new Date(invoice.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  timeZone: 'Asia/Karachi'
                }) : 'N/A'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Buyer Information */}
      <Card>
        <CardHeader>
          <CardTitle>Buyer Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Business Name</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.buyer_business_name || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">NTN/CNIC</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.buyer_ntn_cnic || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Province</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.buyer_province || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Registration Type</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.buyer_registration_type || 'N/A'}</div>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Address</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.buyer_address || 'N/A'}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Seller Information */}
      <Card>
        <CardHeader>
          <CardTitle>Seller Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Business Name</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.seller_business_name || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">NTN/CNIC</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.seller_ntn_cnic || 'N/A'}</div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Province</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.seller_province || 'N/A'}</div>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Address</label>
              <div className="text-base text-[#202223] dark:text-[#e3e3e3]">{invoice?.seller_address || 'N/A'}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Line Items */}
      <Card>
        <CardHeader>
          <CardTitle>Line Items</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto -mx-6 sm:mx-0">
            <div className="inline-block min-w-full align-middle">
              <table className="min-w-full divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
              <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Product Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    HS Code
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    UOM
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Tax Rate
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-[#1a1a1a] divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
                {invoice?.items?.map((item: any, index: number) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {item.product_description || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {item.hs_code || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {item.quantity || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {item.uom || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {item.rate || 0}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                      PKR {(item.total_values || 0).toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Totals */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice Totals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between text-base">
              <span className="text-[#6d7175] dark:text-[#8c9196]">Subtotal (Excluding Tax):</span>
              <span className="text-[#202223] dark:text-[#e3e3e3] font-semibold">
                PKR {(invoice?.items?.reduce((sum: number, item: any) =>
                  sum + (item.value_sales_excluding_st || 0), 0) || 0).toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
              </span>
            </div>
            <div className="flex justify-between text-base">
              <span className="text-[#6d7175] dark:text-[#8c9196]">Sales Tax:</span>
              <span className="text-[#202223] dark:text-[#e3e3e3] font-semibold">
                PKR {(invoice?.items?.reduce((sum: number, item: any) =>
                  sum + (item.sales_tax_applicable || 0), 0) || 0).toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
              </span>
            </div>
            <div className="flex justify-between text-base">
              <span className="text-[#6d7175] dark:text-[#8c9196]">Discount:</span>
              <span className="text-[#202223] dark:text-[#e3e3e3] font-semibold">
                PKR {(invoice?.items?.reduce((sum: number, item: any) =>
                  sum + (item.discount || 0), 0) || 0).toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
              </span>
            </div>
            <div className="border-t border-[#e1e3e5] dark:border-[#2e2e2e] pt-3 flex justify-between text-lg">
              <span className="text-[#202223] dark:text-[#e3e3e3] font-bold">Total Amount:</span>
              <span className="text-[#008060] dark:text-[#00a876] font-bold">
                PKR {(invoice?.items?.reduce((sum: number, item: any) =>
                  sum + (item.total_values || 0), 0) || 0).toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FBR Information (if posted) */}
      {invoice?.fbr_invoice_number && (
        <Card>
          <CardHeader>
            <CardTitle>FBR Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">FBR Invoice Number</label>
                <div className="text-base text-[#202223] dark:text-[#e3e3e3] font-mono">{invoice.fbr_invoice_number}</div>
              </div>
              {invoice?.fbr_posted_at && (
                <div>
                  <label className="block text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-1">Posted At</label>
                  <div className="text-base text-[#202223] dark:text-[#e3e3e3]">
                    {new Date(invoice.fbr_posted_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'Asia/Karachi'
                    })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
