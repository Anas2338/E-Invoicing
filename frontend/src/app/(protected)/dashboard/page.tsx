'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { SummaryCard } from '@/components/dashboard/summary-card';
import { RecentInvoices } from '@/components/dashboard/recent-invoices';
import { SaleInvoiceForm } from '@/components/invoices/sale-invoice-form';
import ManualExcelUploadForm from '@/components/invoices/ManualExcelUploadForm';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { api, ApiError } from '@/lib/api';
import { useAuth } from '@/providers/auth-provider';
import { invoiceService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import {
  FileSpreadsheet,
  ArrowLeft,
  ShoppingCart,
  Package,
  Settings,
  FileText,
  Layers,
  FileCheck,
  Send,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invoiceType, setInvoiceType] = useState<'sale' | 'purchase' | 'excel' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validatingInvoiceId, setValidatingInvoiceId] = useState<string | null>(null);

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

  const [invoiceStats, setInvoiceStats] = useState({
    draft: 0,
    validated: 0,
    posted: 0,
    failed: 0,
  });

  const [recentInvoices, setRecentInvoices] = useState<Array<{
    id: string;
    number: string;
    date: string;
    fbrInvoiceNumber?: string;
    amount: number;
    status: 'draft' | 'validated' | 'posted' | 'failed';
    buyerName: string;
  }>>([]);

  const [fbrNtn, setFbrNtn] = useState('');
  const [fbrBusinessName, setFbrBusinessName] = useState('');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await api.dashboard.getStats();

        setInvoiceStats({
          draft: data.manual_stats.draft || 0,
          validated: data.manual_stats.validated || 0,
          posted: data.manual_stats.posted || 0,
          failed: data.manual_stats.failed || 0,
        });

        setRecentInvoices((data.recent_invoices || []).slice(0, 4));
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Failed to load dashboard data');
        }
      } finally {
        setLoading(false);
      }
    };

    const fetchFbrCredentials = async () => {
      try {
        const fbrData = await api.auth.getFbrCredentials();
        setFbrNtn(fbrData.fbr_seller_ntn || '');
        setFbrBusinessName(fbrData.fbr_business_name || '');
      } catch {
        // Silently fail — credentials are non-critical for dashboard
      }
    };

    fetchDashboardData();
    fetchFbrCredentials();
  }, []);

  const handleSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      const response = await invoiceService.createInvoice(data);
      if (response.success) {
        toast.success('Invoice created successfully!');
        router.push('/invoices/history');
      }
    } catch (error) {
      console.error('Error creating invoice:', error);
      toast.error('Failed to create invoice. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const refreshRecentInvoices = async () => {
    try {
      const data = await api.dashboard.getStats();
      setRecentInvoices((data.recent_invoices || []).slice(0, 4));
      setInvoiceStats({
        draft: data.manual_stats.draft || 0,
        validated: data.manual_stats.validated || 0,
        posted: data.manual_stats.posted || 0,
        failed: data.manual_stats.failed || 0,
      });
    } catch {
      // Silently fail on background refresh
    }
  };

  const handleViewInvoice = (id: string) => {
    router.push(`/invoices/${id}` as any);
  };

  const handleValidateInvoice = async (id: string) => {
    const invoice = recentInvoices.find(inv => inv.id === id);
    if (!invoice) return;

    if (!confirm(`Validate invoice ${invoice.number} with FBR?`)) return;

    setValidatingInvoiceId(id);
    try {
      const response = await api.invoices.validate(id);

      console.group(`FBR Validation — ${invoice.number}`);
      console.log('FBR Request Payload:', JSON.stringify(response.fbr_request_payload, null, 2));
      console.log('FBR Response:', JSON.stringify(response.validation_result, null, 2));
      console.groupEnd();

      setDialogData({
        success: response.success,
        title: 'Validation Successful',
        message: response.message || (response.success ? 'Invoice validated successfully' : 'Validation failed'),
        invoiceNumber: invoice.number,
        errors: response.errors || [],
        invoiceId: id,
      });
      setDialogOpen(true);

      if (response.success) await refreshRecentInvoices();
    } catch (err) {
      setDialogData({
        success: false,
        title: 'Validation Error',
        message: err instanceof ApiError ? err.message : 'Failed to validate invoice. Please try again.',
        invoiceNumber: invoice.number,
        errors: [],
        invoiceId: id,
      });
      setDialogOpen(true);
    } finally {
      setValidatingInvoiceId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="text-center space-y-6">
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 animate-pulse" />
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-emerald-600 dark:border-t-emerald-400 animate-spin" />
          </div>
          <p className="text-base sm:text-lg md:text-xl font-black text-neutral-600 dark:text-neutral-300 tracking-wide">Loading dashboard</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-4xl mx-auto mt-10 px-4">
        <div className="bg-red-50/50 dark:bg-red-950/20 border-2 border-red-200 dark:border-red-900/50 rounded-2xl sm:rounded-3xl p-4 sm:p-6 md:p-8 backdrop-blur-sm shadow-2xl">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-5 items-center sm:items-start text-center sm:text-left">
            <div className="flex-shrink-0 p-3 sm:p-4 bg-red-100 dark:bg-red-900/40 rounded-xl sm:rounded-2xl h-12 w-12 sm:h-16 sm:w-16 flex items-center justify-center shadow-inner">
              <AlertTriangle className="h-6 w-6 sm:h-8 sm:w-8 text-red-600 dark:text-red-400" />
            </div>
            <div className="space-y-1 sm:space-y-2">
              <h3 className="text-xl sm:text-2xl md:text-3xl font-black text-neutral-900 dark:text-neutral-100 tracking-tight">System Gateway Error</h3>
              <p className="text-sm sm:text-base md:text-lg font-semibold text-neutral-600 dark:text-neutral-400 leading-relaxed">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (invoiceType === 'sale') {
    return (
      <div className="space-y-6 w-full max-w-[1600px] mx-auto px-4 md:px-6">
        <SaleInvoiceForm
          onSubmit={handleSubmit}
          onCancel={() => { window.location.reload(); }}
          isLoading={isSubmitting}
        />
      </div>
    );
  }

  if (invoiceType === 'excel') {
    return (
      <div className="container mx-auto px-4 py-3">
        <div className="max-w-3xl lg:max-w-6xl mx-auto flex gap-3">
          <div className="flex flex-col items-center gap-1.5 flex-shrink-0 pt-1">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setInvoiceType(null)}
              className="h-10 lg:h-12 w-10 lg:w-12 border-slate-500 text-slate-600"
              title="Back to Dashboard"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex-1 min-w-0">
            <ManualExcelUploadForm />
          </div>
        </div>
      </div>
    );
  }

  if (invoiceType === 'purchase') {
    return (
      <div className="space-y-6 w-full max-w-[1600px] mx-auto px-4 md:px-6 py-4">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setInvoiceType(null)}
          className="flex items-center gap-3 text-lg font-black text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors px-0 hover:bg-transparent"
        >
          <ArrowLeft className="h-6 w-6 stroke-[3]" />
          Back to Dashboard
        </Button>
        <Card className="border-2 border-neutral-200 dark:border-neutral-800 bg-white/50 dark:bg-neutral-900/50 backdrop-blur-md rounded-3xl shadow-2xl">
          <CardContent className="flex flex-col items-center justify-center py-32 text-center px-6">
            <div className="h-24 w-24 rounded-3xl bg-orange-500/10 dark:bg-orange-500/20 flex items-center justify-center mb-8 ring-8 ring-orange-500/5 shadow-lg">
              <ShoppingCart className="h-12 w-12 text-orange-600 dark:text-orange-400" />
            </div>
            <h2 className="text-3xl md:text-4xl font-black text-neutral-900 dark:text-neutral-100 tracking-tight">Purchase Logs Incoming</h2>
            <p className="text-lg md:text-xl font-medium text-neutral-500 dark:text-neutral-400 max-w-xl mt-4 leading-relaxed">
              The Procurement & Purchase portal is under deep integration parameters. Rest assured, you can continuously manage Sale entries without systemic friction.
            </p>
            <Button
              variant="outline"
              size="lg"
              onClick={() => setInvoiceType(null)}
              className="mt-10 rounded-2xl border-2 border-neutral-300 dark:border-neutral-700 font-black px-10 py-7 text-lg shadow-xl hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-all transform hover:-translate-y-0.5"
            >
              Return safely
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-2 sm:space-y-3 lg:space-y-4 pt-1 pb-2 px-3 sm:px-4 md:px-6 lg:px-8 w-full max-w-[1600px] mx-auto overflow-auto">

      {/* SECTION 1: Responsive Grid Setup for Actions & Gateways */}
      <div className="flex-shrink-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-5 xl:grid-cols-6 gap-3">

          {/* Sale Invoice */}
          <div className="relative group h-28 sm:h-32 lg:h-36 p-[1.5px] rounded-2xl sm:rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(37,99,235,0.5)]">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400 via-blue-500 to-indigo-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <button
              onClick={() => setInvoiceType('sale')}
              className="relative h-full w-full flex flex-col items-center justify-center gap-1.5 sm:gap-2 lg:gap-3 rounded-[22px] bg-gradient-to-b from-blue-400 to-blue-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-1 focus-visible:ring-offset-blue-500"
            >
              <div className="h-9 w-9 sm:h-10 sm:w-10 lg:h-12 lg:w-12 rounded-xl lg:rounded-2xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <FileText className="h-5 w-5 lg:h-6 lg:w-6 text-white stroke-[2.5]" />
              </div>
              <span className="text-xs sm:text-sm lg:text-base font-black tracking-wide text-white drop-shadow-md">
                Sale Invoice
              </span>
            </button>
          </div>

          {/* Purchase Invoice */}
          <div className="relative group h-28 sm:h-32 lg:h-36 p-[1.5px] rounded-2xl sm:rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(234,88,12,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(234,88,12,0.5)]">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-400 via-orange-500 to-red-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <button
              onClick={() => setInvoiceType('purchase')}
              className="relative h-full w-full flex flex-col items-center justify-center gap-1.5 sm:gap-2 lg:gap-3 rounded-[22px] bg-gradient-to-b from-orange-400 to-orange-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-1 focus-visible:ring-offset-orange-500"
            >
              <div className="h-9 w-9 sm:h-10 sm:w-10 lg:h-12 lg:w-12 rounded-xl lg:rounded-2xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <ShoppingCart className="h-5 w-5 lg:h-6 lg:w-6 text-white stroke-[2.5]" />
              </div>
              <span className="text-xs sm:text-sm lg:text-base font-black tracking-wide text-white drop-shadow-md">Purchase Invoice</span>
            </button>
          </div>

          {/* Upload via Excel */}
          <div className="relative group h-28 sm:h-32 lg:h-36 p-[1.5px] rounded-2xl sm:rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(22,163,74,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(22,163,74,0.5)]">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 via-green-500 to-teal-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <button
              onClick={() => setInvoiceType('excel')}
              className="relative h-full w-full flex flex-col items-center justify-center gap-1.5 sm:gap-2 lg:gap-3 rounded-[22px] bg-gradient-to-b from-emerald-400 to-emerald-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-1 focus-visible:ring-offset-emerald-500"
            >
              <div className="h-9 w-9 sm:h-10 sm:w-10 lg:h-12 lg:w-12 rounded-xl lg:rounded-2xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <FileSpreadsheet className="h-5 w-5 lg:h-6 lg:w-6 text-white stroke-[2.5]" />
              </div>
              <span className="text-xs sm:text-sm lg:text-base font-black tracking-wide text-white drop-shadow-md">Excel Upload</span>
            </button>
          </div>

          {/* Products */}
          <div className="relative group h-28 sm:h-32 lg:h-36 p-[1.5px] rounded-2xl sm:rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(124,58,237,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(124,58,237,0.5)]">
            <div className="absolute inset-0 bg-gradient-to-br from-violet-400 via-purple-500 to-fuchsia-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <button
              onClick={() => router.push('/products')}
              className="relative h-full w-full flex flex-col items-center justify-center gap-1.5 sm:gap-2 lg:gap-3 rounded-[22px] bg-gradient-to-b from-purple-400 to-indigo-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-1 focus-visible:ring-offset-purple-500"
            >
              <div className="h-9 w-9 sm:h-10 sm:w-10 lg:h-12 lg:w-12 rounded-xl lg:rounded-2xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <Package className="h-5 w-5 lg:h-6 lg:w-6 text-white stroke-[2.5]" />
              </div>
              <span className="text-xs sm:text-sm lg:text-base font-black tracking-wide text-white drop-shadow-md">Items</span>
            </button>
          </div>

          {/* Credentials & Dynamic Account Settings Card */}
          <div className="relative group sm:col-span-2 md:col-span-2 lg:col-span-1 xl:col-span-2 h-28 sm:h-32 lg:h-36 p-[1.5px] rounded-2xl sm:rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_35px_rgba(0,128,96,0.35)] focus-within:-translate-y-1 focus-within:shadow-[0_0_35px_rgba(0,128,96,0.35)]">
            <div className="absolute inset-0 bg-gradient-to-r from-[#008060] via-[#00a876] to-[#3f51b5] opacity-50 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <div className="relative h-full w-full flex flex-col rounded-[22px] bg-[#008060] dark:bg-[#161616]/95 backdrop-blur-md transition-colors">
              <div className="flex-1 flex flex-col items-center justify-center gap-0.5 lg:gap-0.5 xl:gap-1 px-3 lg:px-2 xl:px-5 z-10 text-center">
                {fbrBusinessName ? (
                  <span className="text-[11px] lg:text-[13px] xl:text-base font-black tracking-wide text-white dark:text-neutral-50 truncate max-w-full drop-shadow-sm leading-tight">
                    {fbrBusinessName.toUpperCase()}
                  </span>
                ) : (
                  <span className="text-[11px] lg:text-[11px] xl:text-base font-bold italic text-neutral-400 dark:text-neutral-500">No gateway name</span>
                )}
                {fbrNtn && (
                  <span className="text-[10px] lg:text-[12px] xl:text-xs font-mono font-black text-[#FFFFFF] dark:text-[#00a876] bg-[#008060]/10 dark:bg-[#00a876]/10 border border-[#008060]/20 dark:border-[#00a876]/20 px-1.5 lg:px-1.5 xl:px-3 py-0.5 rounded-full shadow-inner tracking-wider">
                    NTN: {fbrNtn}
                  </span>
                )}
              </div>
              <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-neutral-200 dark:via-neutral-800 to-transparent" />

              {/* Dynamic Action Trigger Zone */}
              <div className="h-10 sm:h-12 lg:h-10 xl:h-14 flex overflow-hidden rounded-b-[22px]">
                <button
                  onClick={() => router.push('/settings')}
                  className="flex items-center justify-center gap-1 lg:gap-1 xl:gap-3 flex-1 bg-gradient-to-b from-neutral-50/50 to-neutral-100/80 dark:from-neutral-900/40 dark:to-neutral-900/90 border-t border-neutral-100 dark:border-neutral-800/50 transition-all duration-300 cursor-pointer px-2 lg:px-1 xl:px-4 group/btn focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-1 focus-visible:ring-offset-[#008060]"
                >
                  <div className="relative h-5 w-5 lg:h-5 lg:w-5 xl:h-7 xl:w-7 rounded-lg lg:rounded-lg xl:rounded-xl bg-gradient-to-br from-[#008060] to-[#00a876] flex items-center justify-center transform transition-all duration-500 shadow-md shadow-emerald-600/20">
                    <div className="absolute inset-0 rounded-lg lg:rounded-lg xl:rounded-xl bg-emerald-400/40 animate-pulse opacity-0 group-hover/btn:opacity-100 group-focus-visible/btn:opacity-100 transition-opacity duration-300 scale-125" />
                    <Settings className="h-3 w-3 lg:h-3 lg:w-3 xl:h-4 xl:w-4 text-white relative z-10" />
                  </div>
                  <span className="text-[10px] lg:text-[12px] xl:text-xs font-black tracking-tight text-neutral-800 dark:text-neutral-200 transition-colors duration-200">
                    Account Settings
                  </span>
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* SECTION 2: Metric Performance Overview */}
      <div className="flex-shrink-0">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
          <SummaryCard
            title="Draft"
            count={invoiceStats.draft}
            icon={<Layers className="h-4 w-4 sm:h-5 sm:w-5 text-white" />}
            color="bg-blue-600 dark:bg-blue-500 shadow-xl shadow-blue-500/30"
            bg="bg-white dark:bg-[#1a1a1a] border-2 border-blue-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl"
            className="text-xl font-black"
          />
          <SummaryCard
            title="Validated"
            count={invoiceStats.validated}
            icon={<FileCheck className="h-4 w-4 sm:h-5 sm:w-5 text-white" />}
            color="bg-emerald-600 dark:bg-emerald-500 shadow-xl shadow-emerald-500/30"
            bg="bg-white dark:bg-[#1a1a1a] border-2 border-green-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl"
            className="text-xl font-black"
          />
          <SummaryCard
            title="Posted"
            count={invoiceStats.posted}
            icon={<Send className="h-4 w-4 sm:h-5 sm:w-5 text-white" />}
            color="bg-purple-600 dark:bg-purple-500 shadow-xl shadow-purple-500/30"
            bg="bg-white dark:bg-[#1a1a1a] border-2 border-purple-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl"
            className="text-xl font-black"
          />
          <SummaryCard
            title="Failed"
            count={invoiceStats.failed}
            icon={<AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-white" />}
            color="bg-rose-600 dark:bg-rose-500 shadow-xl shadow-rose-500/30"
            bg="bg-white dark:bg-[#1a1a1a] border-2 border-red-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl"
            className="text-xl font-black"
          />
        </div>
      </div>

      {/* SECTION 3: Main Ledger Stream Records Header & Lists */}
      <div className="flex-1 flex flex-col min-h-0">



        <div className="flex-1 min-h-0 overflow-auto">
          {recentInvoices.length > 0 ? (
            /* 🌟 Added light blue heading classes with explicit text colors for both theme layers */
            <RecentInvoices
              invoices={recentInvoices}
              onView={handleViewInvoice}
            />
          ) : (
            <div className="bg-white dark:bg-[#161616] rounded-2xl sm:rounded-3xl border-2 border-neutral-200 dark:border-neutral-800/80 shadow-xl py-8 sm:py-10 lg:py-12 text-center max-w-3xl mx-auto space-y-3 sm:space-y-4 px-4 sm:px-6">
              <div className="mx-auto h-10 w-10 sm:h-12 sm:w-12 text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-900 rounded-xl sm:rounded-2xl flex items-center justify-center border-2 border-neutral-200 dark:border-neutral-800 shadow-inner">
                <FileText className="h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base sm:text-lg md:text-xl font-black text-neutral-900 dark:text-neutral-100 tracking-tight">No Transactions Detected</h3>
                <p className="text-xs sm:text-sm font-semibold text-neutral-500 dark:text-neutral-400 max-w-md mx-auto leading-relaxed">
                  Your systemic queue is currently pristine. Trigger live manual invoices or file transfers above to spin up the pipeline.
                </p>
              </div>
            </div>
          )}
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
