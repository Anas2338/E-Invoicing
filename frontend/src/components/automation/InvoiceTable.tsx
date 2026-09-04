'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Eye, RefreshCw, Loader2, Trash2, Pause, Play, Calendar, ArrowLeft } from 'lucide-react';
import { automationApi } from '@/services/automationApi';
import { toast } from 'sonner';

interface Invoice {
  id: string;
  // null until the transfer job assigns the number at the scheduled time
  invoice_number: string | null;
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
    amount?: string | null;
    invoice_number?: string | null;
    customer?: string | null;
  };
  onFilterChange: (filters: any) => void;
  onPageChange: (page: number) => void;
  onInvoiceClick: (invoiceId: string) => void;
  onBack?: () => void;
  onRetry?: (invoiceId: string) => void;
  retryingInvoiceId?: string | null;
  onPause?: (invoiceId: string) => void;
  pausingInvoiceId?: string | null;
  onResume?: (invoiceId: string) => void;
  resumingInvoiceId?: string | null;
  onBulkDelete?: (invoiceIds: string[]) => void;
  onBulkRetry?: (invoiceIds: string[]) => void;
  onBulkPause?: (invoiceIds: string[]) => void;
  onBulkResume?: (invoiceIds: string[]) => void;
}

export function InvoiceTable({
  invoices,
  loading,
  pagination,
  filters,
  onFilterChange,
  onPageChange,
  onInvoiceClick,
  onBack,
  onRetry,
  retryingInvoiceId,
  onPause,
  pausingInvoiceId,
  onResume,
  resumingInvoiceId,
  onBulkDelete,
  onBulkRetry,
  onBulkPause,
  onBulkResume
}: InvoiceTableProps) {
  const [localFilters, setLocalFilters] = useState(filters);
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [selectAllLoading, setSelectAllLoading] = useState(false);
  const [allSelected, setAllSelected] = useState(false);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [mobileVisibleCount, setMobileVisibleCount] = useState(10);
  const [datePopoverOpen, setDatePopoverOpen] = useState(false);
  const datePopoverRef = useRef<HTMLDivElement>(null);
  const [scrollbarWidth, setScrollbarWidth] = useState(0);
  const bodyScrollRef = useRef<HTMLDivElement>(null);
  const isFirstRender = useRef(true);

  // Debounced real-time filtering — skip initial render
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    const timer = setTimeout(() => {
      onFilterChange(localFilters);
    }, 400);
    return () => clearTimeout(timer);
  }, [localFilters]);

  const activeFilterCount = [
    localFilters.status, localFilters.amount, localFilters.date_from, localFilters.date_to,
    localFilters.invoice_number, localFilters.customer,
  ].filter(v => v !== null && v !== undefined && v !== '').length;

  const hasDateFilter = localFilters.date_from || localFilters.date_to;

  // Reset mobile visible count when invoices change (new page / filter)
  useEffect(() => {
    setMobileVisibleCount(10);
  }, [invoices]);

  // Close date popover on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (datePopoverRef.current && !datePopoverRef.current.contains(e.target as Node)) {
        setDatePopoverOpen(false);
      }
    };
    if (datePopoverOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [datePopoverOpen]);

  // Sync scrollbar width to header tables — keeps columns aligned when body scrollbar appears
  useEffect(() => {
    const el = bodyScrollRef.current;
    if (!el) return;
    const measure = () => setScrollbarWidth(el.offsetWidth - el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [invoices]);

  const handleSelectAll = async (checked: boolean) => {
    if (checked) {
      setSelectAllLoading(true);
      try {
        const result = await automationApi.getAllInvoiceIds({
          status: filters.status || undefined,
          source: filters.source || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
          invoice_number: filters.invoice_number || undefined,
          customer: filters.customer || undefined,
        });
        setSelectedInvoices(result.invoice_ids);
        setAllSelected(true);
      } catch {
        // Fallback: select only visible invoices
        setSelectedInvoices(invoices.map(inv => inv.id));
        setAllSelected(false);
      } finally {
        setSelectAllLoading(false);
      }
    } else {
      setSelectedInvoices([]);
      setAllSelected(false);
    }
  };

  const handleSelectInvoice = (invoiceId: string, checked: boolean) => {
    if (checked) {
      setSelectedInvoices([...selectedInvoices, invoiceId]);
    } else {
      setSelectedInvoices(selectedInvoices.filter(id => id !== invoiceId));
      setAllSelected(false);
    }
  };

  /** Filter `selectedInvoices` to only those whose status is in `validStatuses`. */
  const filterEligible = (validStatuses: string[]) =>
    selectedInvoices.filter(id => validStatuses.includes(
      invoices.find(inv => inv.id === id)?.status ?? ''
    ));

  const handleBulkDelete = async () => {
    if (selectedInvoices.length === 0 || !onBulkDelete) return;

    const eligible = filterEligible(['pending', 'failed', 'expired', 'blocked', 'validated']);
    if (eligible.length === 0) return;

    if (!confirm(`Are you sure you want to delete ${eligible.length} invoice(s)?`)) {
      return;
    }

    setBulkActionLoading(true);
    try {
      await onBulkDelete(eligible);
      setSelectedInvoices([]);
      setAllSelected(false);
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkRetry = async () => {
    if (selectedInvoices.length === 0 || !onBulkRetry) return;

    const eligible = filterEligible(['pending', 'failed', 'transfer_failed']);
    if (eligible.length === 0) return;

    setBulkActionLoading(true);
    try {
      await onBulkRetry(eligible);
      setSelectedInvoices([]);
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkPause = async () => {
    if (selectedInvoices.length === 0 || !onBulkPause) return;

    const eligible = filterEligible(['validated']);
    if (eligible.length === 0) return;

    setBulkActionLoading(true);
    try {
      await onBulkPause(eligible);
      setSelectedInvoices([]);
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkResume = async () => {
    if (selectedInvoices.length === 0 || !onBulkResume) return;

    const eligible = filterEligible(['paused']);
    if (eligible.length === 0) return;

    setBulkActionLoading(true);
    try {
      await onBulkResume(eligible);
      setSelectedInvoices([]);
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      status: null,
      source: null,
      amount: null,
      date_from: null,
      date_to: null,
      invoice_number: null,
      customer: null
    };
    setLocalFilters(clearedFilters);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      pending: { label: 'Pending', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-blue-400 via-blue-500 to-blue-600 border border-blue-400/40 shadow-[0_5px_12px_-3px_rgba(59,130,246,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      validated: { label: 'Validated', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-sky-400 via-sky-500 to-sky-600 border border-sky-400/40 shadow-[0_5px_12px_-3px_rgba(14,165,233,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      transferred: { label: 'Transferred', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-emerald-400 via-emerald-500 to-emerald-600 border border-emerald-400/40 shadow-[0_5px_12px_-3px_rgba(16,185,129,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      transfer_failed: { label: 'Transfer Failed', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-rose-400 via-rose-500 to-rose-600 border border-rose-400/40 shadow-[0_5px_12px_-3px_rgba(244,63,94,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      failed: { label: 'Failed', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-rose-400 via-rose-500 to-rose-600 border border-rose-400/40 shadow-[0_5px_12px_-3px_rgba(244,63,94,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      blocked: { label: 'Blocked', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-orange-400 via-orange-500 to-orange-600 border border-orange-400/40 shadow-[0_5px_12px_-3px_rgba(249,115,22,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      paused: { label: 'Paused', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-amber-400 via-amber-500 to-amber-600 border border-amber-400/40 shadow-[0_5px_12px_-3px_rgba(245,158,11,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' },
      expired: { label: 'Expired', className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-slate-400 via-slate-500 to-slate-600 border border-slate-400/40 shadow-[0_5px_12px_-3px_rgba(100,116,139,0.3),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]' }
    };

    const config = statusConfig[status] || { label: status, className: 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-gray-400 to-gray-500' };

    return config;
  };

  const formatStatus = (status: string) => {
    switch (status) {
      case 'pending': return 'Pending';
      case 'validated': return 'Valid';
      case 'transferred': return 'Transferred';
      case 'transfer_failed': return 'Transfer Failed';
      case 'failed': return 'Failed';
      case 'blocked': return 'Blocked';
      case 'paused': return 'Paused';
      case 'expired': return 'Expired';
      default: return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  };

  const formatTime = (timeStr: string) => {
    // Handle time format like "10:00:00"
    const [hours, minutes] = timeStr.split(':');
    const h = parseInt(hours, 10);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const displayHour = h % 12 || 12;
    return `${String(displayHour).padStart(2, '0')}-${minutes} ${ampm}`;
  };

  const formatAmount = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null) return '0.00';
    return `${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const computeTotalAmount = (invoiceData: Record<string, any> | undefined | null): number => {
    if (!invoiceData) return 0;
    // If total_amount is already present, use it
    if (invoiceData.total_amount !== undefined && invoiceData.total_amount !== null) {
      return Number(invoiceData.total_amount);
    }
    // Otherwise compute from items
    const items = invoiceData.items;
    if (!items || !Array.isArray(items) || items.length === 0) return 0;
    return items.reduce((sum: number, item: any) => {
      const valueExclST = parseFloat(item.value_sales_excluding_st) || 0;
      const salesTax = parseFloat(item.sales_tax_applicable) || 0;
      const extraTax = parseFloat(item.extra_tax) || 0;
      const furtherTax = parseFloat(item.further_tax) || 0;
      const fedPayable = parseFloat(item.fed_payable) || 0;
      const discount = parseFloat(item.discount) || 0;
      return sum + valueExclST + salesTax + extraTax + furtherTax + fedPayable - discount;
    }, 0);
  };

  const isSelectable = (status: string) =>
    ['pending', 'validated', 'transferred', 'transfer_failed', 'failed', 'blocked', 'paused'].includes(status);

  // High-performance focused input styling with adjusted colors and clean borders
  const filterInputClass = "w-full h-8 text-xs px-2.5 py-1 border border-blue-600 dark:border-neutral-800 rounded-lg bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-150 shadow-sm";

  const selectableInvoices = invoices.filter(inv => isSelectable(inv.status));
  const allSelectableSelected = selectableInvoices.length > 0 &&
    selectableInvoices.every(inv => selectedInvoices.includes(inv.id));
  const someSelectableSelected = selectableInvoices.some(inv => selectedInvoices.includes(inv.id));

  const EmptyStateContent = () => (
    <div className="text-center py-12 sm:py-16">
      <svg
        className="mx-auto h-12 w-12 sm:h-14 sm:w-14 text-slate-300 dark:text-neutral-700 stroke-[1.5]"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <h3 className="mt-4 text-sm sm:text-base font-semibold text-slate-900 dark:text-neutral-100 tracking-tight">No invoices found</h3>
      <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-neutral-400 max-w-xs mx-auto">
        Try adjusting your filters or upload new invoices.
      </p>
    </div>
  );

  // Bulk Actions Sidebar
  const BulkActionsSidebar = () => {
    const hasSelection = selectedInvoices.length > 0;

    // Derive the statuses of selected invoices to smart-enable/disable each action
    const selectedStatuses = new Set(
      invoices
        .filter(inv => selectedInvoices.includes(inv.id))
        .map(inv => inv.status)
    );

    // Each action is enabled only when the selection includes at least one
    // invoice in a status that backend will accept for that operation
    const canRetry  = hasSelection && ['pending', 'failed', 'transfer_failed'].some(s => selectedStatuses.has(s));
    const canPause  = hasSelection && ['validated'].some(s => selectedStatuses.has(s));
    const canResume = hasSelection && ['paused'].some(s => selectedStatuses.has(s));
    const canDelete = hasSelection && ['pending', 'failed', 'expired', 'blocked', 'validated'].some(s => selectedStatuses.has(s));

    return (
      <div className="flex flex-col items-center gap-1.5 pr-2 flex-shrink-0 mt-24 xl:mt-28">
        {onBack && (
            <Button
              variant="outline"
              size="icon"
              onClick={onBack}
              className="h-10 lg:h-12 w-10 lg:w-12 border-slate-500 text-slate-600"
              title="Back to Automation"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
        {onBulkRetry && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleBulkRetry}
            disabled={!canRetry || bulkActionLoading}
            className="h-10 lg:h-12 w-10 lg:w-12 border-blue-500 text-blue-600 disabled:border-blue-300 disabled:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Retry selected"
          >
            {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        )}
        {onBulkPause && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleBulkPause}
            disabled={!canPause || bulkActionLoading}
            className="h-10 lg:h-12 w-10 lg:w-12 border-amber-500 text-amber-600 disabled:border-amber-300 disabled:text-amber-300 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Pause selected"
          >
            {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
          </Button>
        )}
        {onBulkResume && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleBulkResume}
            disabled={!canResume || bulkActionLoading}
            className="h-10 lg:h-12 w-10 lg:w-12 border-green-500 text-green-600 disabled:border-green-300 disabled:text-green-300 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Resume selected"
          >
            {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          </Button>
        )}
        {onBulkDelete && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleBulkDelete}
            disabled={!canDelete || bulkActionLoading}
            className="h-10 lg:h-12 w-10 lg:w-12 border-red-500 text-red-600 disabled:border-red-300 disabled:text-red-300 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Delete selected"
          >
            {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </Button>
        )}
        <span className={`text-[10px] text-center font-semibold ${hasSelection ? 'text-[#6d7175] dark:text-[#8c9196]' : 'text-slate-300 dark:text-neutral-700'}`}>
          {selectedInvoices.length}
        </span>
      </div>
    );
  };

  // Responsive pagination bar — same design as invoices history page
  const PaginationBar = () => {
    if (pagination.total_pages <= 1) return null;

    const { page, total_pages, total } = pagination;
    const startItem = (page - 1) * pagination.page_size + 1;
    const endItem = Math.min(page * pagination.page_size, total);

    const totalPages = total_pages;
    const currentPage = page;

    return (
      <div className="sticky bottom-0 z-10 rounded-4xl bg-[#f5f5f4] dark:bg-[#0a0a0a]">
        <div className="flex flex-wrap items-center justify-between gap-2 px-2 py-2 border-2 border-blue-600 rounded-4xl">
          <span className="hidden sm:inline text-xs text-black dark:text-neutral-400">
            Showing {startItem}–{endItem} of{' '}
            {total} invoices
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-blue-600 text-blue-600 hover:bg-blue-100  disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              // Show pages around current page
              let pageNum: number;
              if (totalPages <= 7) {
                pageNum = i + 1;
              } else if (currentPage <= 4) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 3) {
                pageNum = totalPages - 6 + i;
              } else {
                pageNum = currentPage - 3 + i;
              }
              return (
                <button
                  key={pageNum}
                  type="button"
                  onClick={() => onPageChange(pageNum)}
                  className={`w-7 h-7 text-xs font-semibold rounded-lg transition-colors ${
                    i >= 3 ? 'hidden sm:inline-flex items-center justify-center' : ''
                  } ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-black hover:bg-blue-200 border border-blue-400'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-blue-600 text-blue-600 hover:bg-blue-100  disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Show full-page spinner only on initial load (no data yet)
  if (loading && invoices.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading invoices...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Subtle loading bar for background refreshes
      {loading && invoices.length > 0 && (
        <div className="w-full h-0.5 bg-blue-100 dark:bg-neutral-800 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }}></div>
        </div>
      )} */}

      {/* Mobile/Tablet Card View */}
      <div className="block lg:hidden flex flex-col flex-1 min-h-0">

        {/* Sidebar + Card Content (same pattern as invoices history) */}
        <div className="flex gap-0 flex-1 min-h-0">
          {/* Mobile Sidebar — vertical action buttons */}
          <div className="flex flex-col items-center gap-1 pt-1 pr-1.5 flex-shrink-0">
            {(() => {
              const hasSelection = selectedInvoices.length > 0;
              const selectedStatuses = new Set(
                invoices
                  .filter(inv => selectedInvoices.includes(inv.id))
                  .map(inv => inv.status)
              );
              const canRetry  = hasSelection && ['pending', 'failed', 'transfer_failed'].some(s => selectedStatuses.has(s));
              const canPause  = hasSelection && ['validated'].some(s => selectedStatuses.has(s));
              const canResume = hasSelection && ['paused'].some(s => selectedStatuses.has(s));
              const canDelete = hasSelection && ['pending', 'failed', 'expired', 'blocked', 'validated'].some(s => selectedStatuses.has(s));

              return (
                <>
                  {onBulkRetry && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleBulkRetry}
                      disabled={!canRetry || bulkActionLoading}
                      className="h-8 w-8 border-blue-500 text-blue-600 disabled:border-blue-300 disabled:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Retry selected"
                    >
                      {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                    </Button>
                  )}
                  {onBulkPause && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleBulkPause}
                      disabled={!canPause || bulkActionLoading}
                      className="h-8 w-8 border-amber-500 text-amber-600 disabled:border-amber-300 disabled:text-amber-300 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Pause selected"
                    >
                      {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
                    </Button>
                  )}
                  {onBulkResume && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleBulkResume}
                      disabled={!canResume || bulkActionLoading}
                      className="h-8 w-8 border-green-500 text-green-600 disabled:border-green-300 disabled:text-green-300 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Resume selected"
                    >
                      {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    </Button>
                  )}
                  {onBulkDelete && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleBulkDelete}
                      disabled={!canDelete || bulkActionLoading}
                      className="h-8 w-8 border-red-500 text-red-600 disabled:border-red-300 disabled:text-red-300 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Delete selected"
                    >
                      {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                    </Button>
                  )}
                  {selectedInvoices.length > 0 && (
                    <span className="text-[10px] text-[#6d7175] dark:text-[#8c9196] text-center font-semibold">
                      {selectedInvoices.length}
                    </span>
                  )}
                </>
              );
            })()}
          </div>

          {/* Card Content */}
          <div className="flex-1 min-h-0 flex flex-col">
            {/* Mobile Filter Toggle & Panel — fixed at top */}
            <div className="flex-shrink-0 mb-2 sm:mb-3">
              <button
                type="button"
                onClick={() => setShowMobileFilters(!showMobileFilters)}
                className={`w-full flex items-center justify-between gap-2 px-3 sm:px-4 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all duration-200 ${
                  showMobileFilters
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-white dark:bg-neutral-900 border-2 border-blue-600 text-blue-600 dark:text-blue-400'
                }`}
              >
                <span className="flex items-center gap-2">
                  <svg className="h-3.5 w-3.5 sm:h-4 sm:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  <span>Filters</span>
                </span>
                {activeFilterCount > 0 && (
                  <span className="bg-red-500 text-white text-xs font-black px-2 py-0.5 rounded-full leading-none">
                    {activeFilterCount}
                  </span>
                )}
              </button>

              {showMobileFilters && (
                <div className="mt-2 bg-white dark:bg-neutral-950 rounded-2xl border border-slate-200 dark:border-neutral-800 p-2 sm:p-3 shadow-sm space-y-2">
                  <div className="grid grid-cols-1 max-sm:grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Invoice #..."
                      value={localFilters.invoice_number || ''}
                      onChange={(e) => setLocalFilters({ ...localFilters, invoice_number: e.target.value || null })}
                      className={filterInputClass}
                    />
                    <Select
                      value={localFilters.status || 'all'}
                      onValueChange={(value) => setLocalFilters({ ...localFilters, status: value === 'all' ? null : value })}
                    >
                      <SelectTrigger className="text-xs" style={{ height: '32px', padding: '4px 10px', borderRadius: '8px', fontSize: '12px', borderWidth: '1px', borderColor: '#2563eb' }}>
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
                        <SelectItem value="all" className="text-xs rounded-md">All</SelectItem>
                        <SelectItem value="pending" className="text-xs rounded-md">Pending</SelectItem>
                        <SelectItem value="validated" className="text-xs rounded-md">Validated</SelectItem>
                        <SelectItem value="transferred" className="text-xs rounded-md">Transferred</SelectItem>
                        <SelectItem value="transfer_failed" className="text-xs rounded-md">Tr. Failed</SelectItem>
                        <SelectItem value="failed" className="text-xs rounded-md">Failed</SelectItem>
                        <SelectItem value="blocked" className="text-xs rounded-md">Blocked</SelectItem>
                        <SelectItem value="paused" className="text-xs rounded-md">Paused</SelectItem>
                        <SelectItem value="expired" className="text-xs rounded-md">Expired</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-1 max-sm:grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Customer..."
                      value={localFilters.customer || ''}
                      onChange={(e) => setLocalFilters({ ...localFilters, customer: e.target.value || null })}
                      className={filterInputClass}
                    />
                    <input
                      type="text"
                      placeholder="Amount..."
                      value={localFilters.amount || ''}
                      onChange={(e) => setLocalFilters({ ...localFilters, amount: e.target.value || null })}
                      className={filterInputClass}
                    />
                  </div>
                  <div className="grid grid-cols-1 max-sm:grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="relative">
                      <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                      <input
                        type="date"
                        value={localFilters.date_from || ''}
                        onChange={(e) => setLocalFilters({ ...localFilters, date_from: e.target.value || null })}
                        placeholder="From date"
                        className={`${filterInputClass} pl-7 sm:pl-8`}
                      />
                    </div>
                    <div className="relative">
                      <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                      <input
                        type="date"
                        value={localFilters.date_to || ''}
                        onChange={(e) => setLocalFilters({ ...localFilters, date_to: e.target.value || null })}
                        placeholder="To date"
                        className={`${filterInputClass} pl-7 sm:pl-8`}
                      />
                    </div>
                  </div>
                  <div className="flex justify-end pt-1">
                    {activeFilterCount > 0 && (
                      <button
                        type="button"
                        onClick={handleClearFilters}
                        className="text-xs font-semibold text-red-500 hover:text-red-600 transition-colors px-3 py-1"
                      >
                        Clear all filters
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="overflow-y-auto flex-1 min-h-0">
            {invoices.length === 0 ? (
              <div className="bg-white dark:bg-neutral-950 rounded-2xl border border-slate-100 dark:border-neutral-900 shadow-sm">
                <EmptyStateContent />
              </div>
            ) : (
          <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 sm:gap-3 md:gap-4">
            {invoices.slice(0, mobileVisibleCount).map((invoice) => {
              const isSelected = selectedInvoices.includes(invoice.id);
              const statusCfg = getStatusBadge(invoice.status);

              return (
                <div
                  key={invoice.id}
                  className={`bg-white dark:bg-neutral-950 rounded-2xl border transition-all duration-200 shadow-sm hover:shadow-md ${
                    isSelected
                      ? 'border-emerald-500 ring-1 ring-emerald-500/30 bg-emerald-50/10 dark:bg-emerald-500/[0.02]'
                      : 'border-slate-200/80 dark:border-neutral-900 hover:border-slate-300 dark:hover:border-neutral-800'
                  }`}
                >
                  <div className="p-3 sm:p-4">
                    {/* Header with checkbox and invoice number */}
                    <div className="flex items-start justify-between mb-3 sm:mb-4">
                      <div className="flex items-start gap-2 sm:gap-3 flex-1 min-w-0">
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                          disabled={!isSelectable(invoice.status)}
                          aria-label={`Select invoice ${invoice.invoice_number}`}
                          className="mt-1 shrink-0 data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-bold text-slate-900 dark:text-neutral-100 tracking-tight truncate">{invoice.invoice_number || '—'}</div>
                          <div className="text-xs font-medium text-slate-400 dark:text-neutral-500 mt-0.5">Automation Invoice</div>
                        </div>
                      </div>
                      <Badge className={`${statusCfg.className} shrink-0 ml-2 px-2 sm:px-2.5 py-0.5 text-[10px] sm:text-xs font-semibold tracking-wide rounded-full shadow-sm`}>
                        {statusCfg.label}
                      </Badge>
                    </div>

                    {/* Invoice Details */}
                    <div className="space-y-2 mb-3 sm:mb-4 text-[11px] sm:text-xs font-medium">
                      <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50">
                        <span className="text-slate-400 dark:text-neutral-500 shrink-0 mr-2">Customer</span>
                        <span className="text-slate-800 dark:text-neutral-200 truncate font-semibold text-right max-w-[55%] sm:max-w-[65%]">
                          {invoice.invoice_data?.buyer_business_name || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50 gap-2">
                        <span className="text-slate-400 dark:text-neutral-500 shrink-0">Scheduled</span>
                        <span className="text-slate-700 dark:text-neutral-300 font-semibold text-right whitespace-nowrap text-[10px] sm:text-xs">
                          {formatDate(invoice.scheduled_date)} {formatTime(invoice.scheduled_time)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50">
                        <span className="text-slate-400 dark:text-neutral-500 shrink-0 mr-2">Amount</span>
                        <span className="text-slate-800 dark:text-neutral-200 font-semibold tabular-nums">
                          {formatAmount(computeTotalAmount(invoice.invoice_data))}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-1.5 sm:gap-2 pt-3 border-t border-slate-100 dark:border-neutral-900">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onInvoiceClick(invoice.id)}
                        className="flex-1 min-w-[70px] sm:min-w-[80px] h-8 sm:h-9 text-[10px] sm:text-xs rounded-xl font-semibold border-slate-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-800"
                      >
                        <Eye className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5 opacity-80" />
                        View
                      </Button>
                      {invoice.status === 'validated' && onPause && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onPause(invoice.id)}
                          disabled={pausingInvoiceId === invoice.id}
                          className="flex-1 min-w-[70px] sm:min-w-[80px] h-8 sm:h-9 text-[10px] sm:text-xs rounded-xl font-semibold border-amber-200 text-amber-700 bg-amber-50/50 hover:bg-amber-50 dark:border-amber-500/30 dark:text-amber-400 dark:bg-amber-500/5 dark:hover:bg-amber-500/10"
                        >
                          {pausingInvoiceId === invoice.id ? (
                            <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5 animate-spin" />
                          ) : (
                            <Pause className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5" />
                          )}
                          {pausingInvoiceId === invoice.id ? 'Pausing...' : 'Pause'}
                        </Button>
                      )}
                      {invoice.status === 'paused' && onResume && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onResume(invoice.id)}
                          disabled={resumingInvoiceId === invoice.id}
                          className="flex-1 min-w-[70px] sm:min-w-[80px] h-8 sm:h-9 text-[10px] sm:text-xs rounded-xl font-semibold border-green-300 text-green-700 bg-green-50/50 hover:bg-green-50 dark:border-green-500/30 dark:text-green-400 dark:bg-green-500/5 dark:hover:bg-green-500/10"
                        >
                          {resumingInvoiceId === invoice.id ? (
                            <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5 animate-spin" />
                          ) : (
                            <Play className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5" />
                          )}
                          {resumingInvoiceId === invoice.id ? 'Resuming...' : 'Resume'}
                        </Button>
                      )}
                      {(invoice.status === 'pending' || invoice.status === 'transfer_failed') && onRetry && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onRetry(invoice.id)}
                          disabled={retryingInvoiceId === invoice.id}
                          className="flex-1 min-w-[70px] sm:min-w-[80px] h-8 sm:h-9 text-[10px] sm:text-xs rounded-xl font-semibold border-emerald-500/40 text-emerald-600 bg-emerald-50/40 hover:bg-emerald-500 hover:text-white dark:border-emerald-500/30 dark:text-emerald-400 dark:bg-emerald-500/5 dark:hover:bg-emerald-500 dark:hover:text-neutral-950 transition-all"
                        >
                          {retryingInvoiceId === invoice.id ? (
                            <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5 animate-spin" />
                          ) : (
                            <RefreshCw className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 sm:mr-1.5" />
                          )}
                          {retryingInvoiceId === invoice.id ? 'Retrying...' : 'Retry'}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {mobileVisibleCount < invoices.length && (
            <div className="flex justify-center py-3">
              <button
                type="button"
                onClick={() => setMobileVisibleCount(prev => prev + 20)}
                className="px-6 py-2.5 text-xs font-bold rounded-xl border-2 border-blue-500 text-blue-600 bg-white dark:bg-neutral-900 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors shadow-sm"
              >
                See More
              </button>
            </div>
          )}
        </>)}
            </div>

        <PaginationBar />
          </div>
        </div>
      </div>

      {/* Desktop Table View */}
      <div className="hidden lg:flex lg:flex-row lg:gap-0 h-full">
        {/* Sidebar */}
        {/* <div> */}
          {/* {onBack && (
            <Button
              variant="outline"
              size="icon"
              onClick={onBack}
              className="h-8 w-8 border-slate-300 text-slate-600"
              title="Back to Automation"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )} */}
          <BulkActionsSidebar />
        {/* </div> */}

        <div className="overflow-x-auto rounded-2xl flex-1 min-h-0">
          <div className="min-w-[830px] flex flex-col gap-2 h-full">

            {/* Header wrapper — right-padding synced to body scrollbar */}
            <div style={{ paddingRight: scrollbarWidth }}>
              {/* Table 1: Column Headers (blue header) */}
              <table className="w-full table-fixed bg-[#7c97f0] rounded-4xl flex-shrink-0 border-separate border-spacing-0">
                <thead>
                  <tr>
                    <th className="border-r-2 border-[#FFFFFF] w-[4%] px-1 pt-3.5 pb-2"></th>
                    <th className="border-r-2 border-[#FFFFFF] w-[11%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Invoice #
                    </th>
                    <th className="border-r-2 border-[#FFFFFF] w-[29%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Buyer Name
                    </th>
                    <th className="border-r-2 border-[#FFFFFF] w-[12%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Scheduled
                    </th>
                    <th className="border-r-2 border-[#FFFFFF] w-[12%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Amount
                    </th>
                    <th className="border-r-2 border-[#FFFFFF] w-[12%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Status
                    </th>
                    <th className="w-[12%] px-2 py-2 text-center text-[12px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                      Actions
                    </th>
                  </tr>
                </thead>
              </table>

              {/* Table 2: Filter Inputs Row */}
              <table className="w-full table-fixed rounded-4xl flex-shrink-0">
                <thead>
                  <tr>
                    <th scope="col" className="w-[4%] px-1 py-2">
                      {selectAllLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin text-blue-600 mx-auto" />
                      ) : (
                        <Checkbox
                          checked={allSelectableSelected}
                          onCheckedChange={handleSelectAll}
                          aria-label="Select all invoices"
                          className={`data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500 ${someSelectableSelected && !allSelectableSelected ? 'data-[state=checked]:bg-slate-400 dark:data-[state=checked]:bg-neutral-600' : ''}`}
                        />
                      )}
                    </th>
                    <th scope="col" className="w-[11%] px-1 py-2">
                      <input
                        type="text"
                        placeholder="Filter ID"
                        value={localFilters.invoice_number || ''}
                        onChange={(e) => setLocalFilters({ ...localFilters, invoice_number: e.target.value || null })}
                        className={filterInputClass}
                      />
                    </th>
                    <th scope="col" className="w-[29%] px-1 py-2">
                      <input
                        type="text"
                        placeholder="Filter customer"
                        value={localFilters.customer || ''}
                        onChange={(e) => setLocalFilters({ ...localFilters, customer: e.target.value || null })}
                        className={filterInputClass}
                      />
                    </th>
                    <th scope="col" className="w-[12%] px-1 py-2">
                      <div className="relative" ref={datePopoverRef}>
                        <button
                          type="button"
                          onClick={() => setDatePopoverOpen(!datePopoverOpen)}
                          className={`${filterInputClass} flex items-center gap-1.5 text-left`}
                          style={hasDateFilter ? undefined : { color: '#94a3b8' }}
                        >
                          <Calendar className="h-3 w-3 shrink-0" />
                          <span className="truncate">
                            {hasDateFilter
                              ? `${localFilters.date_from || '...'} – ${localFilters.date_to || '...'}`
                              : 'Date'}
                          </span>
                        </button>
                        {datePopoverOpen && (
                          <div className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-neutral-900 rounded-xl shadow-xl p-3 w-[260px]">
                            <div className="space-y-2">
                              <div>
                                <label className="block text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase mb-0.5">From</label>
                                <input
                                  type="date"
                                  value={localFilters.date_from || ''}
                                  onChange={(e) => setLocalFilters({ ...localFilters, date_from: e.target.value || null })}
                                  className={filterInputClass}
                                />
                              </div>
                              <div>
                                <label className="block text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase mb-0.5">To</label>
                                <input
                                  type="date"
                                  value={localFilters.date_to || ''}
                                  onChange={(e) => setLocalFilters({ ...localFilters, date_to: e.target.value || null })}
                                  className={filterInputClass}
                                />
                              </div>
                              {hasDateFilter && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setLocalFilters({ ...localFilters, date_from: null, date_to: null });
                                  }}
                                  className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-neutral-300 underline w-full text-left"
                                >
                                  Clear dates
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </th>
                    <th scope="col" className="w-[12%] px-1 py-2">
                      <input
                        type="text"
                        placeholder="Filter amount"
                        value={localFilters.amount || ''}
                        onChange={(e) => setLocalFilters({ ...localFilters, amount: e.target.value || null })}
                        className={filterInputClass}
                      />
                    </th>
                    <th scope="col" className="w-[12%] px-1 py-2">
                      <Select
                        value={localFilters.status || 'all'}
                        onValueChange={(value) => setLocalFilters({ ...localFilters, status: value === 'all' ? null : value })}
                      >
                        <SelectTrigger className="text-[10px] text-slate-400" style={{ height: '32px', padding: '2px 6px', borderRadius: '8px', fontSize: '10px', borderWidth: '1px', color: '#94a3b8', borderColor: '#2563eb' }}>
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
                          <SelectItem value="all" className="text-xs rounded-md">All</SelectItem>
                          <SelectItem value="pending" className="text-xs rounded-md">Pending</SelectItem>
                          <SelectItem value="validated" className="text-xs rounded-md">Valid</SelectItem>
                          <SelectItem value="transferred" className="text-xs rounded-md">Transferred</SelectItem>
                          <SelectItem value="transfer_failed" className="text-xs rounded-md">Tr. Failed</SelectItem>
                          <SelectItem value="failed" className="text-xs rounded-md">Failed</SelectItem>
                          <SelectItem value="blocked" className="text-xs rounded-md">Blocked</SelectItem>
                          <SelectItem value="paused" className="text-xs rounded-md">Paused</SelectItem>
                          <SelectItem value="expired" className="text-xs rounded-md">Expired</SelectItem>
                        </SelectContent>
                      </Select>
                    </th>
                    <th scope="col" className="w-[12%] pl-1 pr-0 py-2">
                      <div className="flex items-center gap-1 justify-center">
                        {activeFilterCount > 0 && (
                          <button
                            type="button"
                            onClick={handleClearFilters}
                            className="text-[10px] font-semibold text-red-500 hover:text-red-600 transition-colors px-1 py-1"
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    </th>
                  </tr>
                </thead>
              </table>
            </div>

            {/* Table 3: Body — scrollable */}
            {invoices.length === 0 ? (
              <div className="flex-1 flex items-start justify-center">
                <EmptyStateContent />
              </div>
            ) : (
              <div className="flex-1 min-h-0 flex flex-col items-start">
                <div ref={bodyScrollRef} className="w-full max-h-full overflow-y-auto overflow-x-hidden rounded-4xl bg-blue-50 border-2 border-blue-600">
                  <table className="w-full table-fixed border-separate border-spacing-0">
                    <tbody>
                      {invoices.map((invoice) => {
                        const isSelected = selectedInvoices.includes(invoice.id);
                        const statusCfg = getStatusBadge(invoice.status);

                        return (
                          <tr
                            key={invoice.id}
                            className={`group transition-colors duration-150 ${
                              isSelected
                                ? 'bg-emerald-50/20'
                                : 'hover:bg-slate-50/60'
                            }`}
                          >
                            <td className="border-r-2 border-b-1 border-blue-200 px-3.5 py-4 align-middle w-[4%]">
                              <Checkbox
                                checked={isSelected}
                                onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                                disabled={!isSelectable(invoice.status)}
                                aria-label={`Select invoice ${invoice.invoice_number}`}
                                className="data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500"
                              />
                            </td>
                            <td className="px-1 py-4 align-middle w-[11%] border-r-2 border-b-1 border-blue-200">
                              <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700">{invoice.invoice_number || '—'}</div>
                              {/* <div className="text-[9px] lg:text-[10px] xl:text-xs font-medium text-slate-500 truncate mt-0.5">Automation</div> */}
                            </td>
                            <td className="px-2 py-4 w-[29%] border-r-2 border-b-1 border-blue-200">
                              <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700 truncate">
                                {invoice.invoice_data?.buyer_business_name || 'N/A'}
                              </div>
                            </td>
                            <td className="px-1 py-4 w-[12%] border-r-2 border-b-1 border-blue-200">
                              <div className="text-[10px] lg:text-[11px] xl:text-[13px] font-medium text-slate-700 whitespace-nowrap text-center">
                                {formatDate(invoice.scheduled_date)}
                              </div>
                              <div className="text-[9px] lg:text-[10px] xl:text-xs font-medium text-slate-500 text-center">
                                {formatTime(invoice.scheduled_time)}
                              </div>
                            </td>
                            <td className="px-1 py-4 w-[12%] border-r-2 border-b-1 border-blue-200 text-right align-middle pr-3">
                              <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700 tabular-nums">
                                {formatAmount(computeTotalAmount(invoice.invoice_data))}
                              </div>
                            </td>
                            <td className="px-1 py-4 text-center w-[12%] border-r-2 border-b-1 border-blue-200">
                              <Badge className={statusCfg.className}>
                                {statusCfg.label}
                              </Badge>
                            </td>
                            <td className="pl-1 pr-0 py-4 text-center align-middle w-[12%] border-b-1 border-blue-200">
                              <div className="flex items-center justify-center gap-1">
                                <Button
                                  variant="outline"
                                  size="icon"
                                  onClick={() => onInvoiceClick(invoice.id)}
                                  className="h-10 w-10 rounded-lg border-slate-200 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100"
                                  title="View"
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                                {invoice.status === 'validated' && onPause && (
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => onPause(invoice.id)}
                                    disabled={pausingInvoiceId === invoice.id}
                                    className="h-10 w-10 rounded-lg border-amber-200 text-amber-600 bg-amber-50/30 hover:bg-amber-50 dark:border-amber-500/30 dark:text-amber-400 dark:bg-amber-500/5 dark:hover:bg-amber-500/20 shadow-sm"
                                    title="Pause"
                                  >
                                    {pausingInvoiceId === invoice.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Pause className="h-4 w-4" />
                                    )}
                                  </Button>
                                )}
                                {invoice.status === 'paused' && onResume && (
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => onResume(invoice.id)}
                                    disabled={resumingInvoiceId === invoice.id}
                                    className="h-10 w-10 rounded-lg border-green-300 text-green-600 bg-green-50/30 hover:bg-green-50 dark:border-green-500/30 dark:text-green-400 dark:bg-green-500/5 dark:hover:bg-green-500/20 shadow-sm"
                                    title="Resume"
                                  >
                                    {resumingInvoiceId === invoice.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Play className="h-4 w-4" />
                                    )}
                                  </Button>
                                )}
                                {(invoice.status === 'pending' || invoice.status === 'transfer_failed') && onRetry && (
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => onRetry(invoice.id)}
                                    disabled={retryingInvoiceId === invoice.id}
                                    className="h-10 w-10 rounded-lg border-emerald-500/30 text-emerald-600 bg-emerald-50/20 hover:bg-emerald-500 hover:text-white dark:border-emerald-500/30 dark:text-emerald-400 dark:bg-emerald-500/5 dark:hover:bg-emerald-500 dark:hover:text-neutral-950 shadow-sm transition-all"
                                    title="Retry"
                                  >
                                    {retryingInvoiceId === invoice.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <RefreshCw className="h-4 w-4" />
                                    )}
                                  </Button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <PaginationBar />

          </div>
        </div>

      </div>
    </div>
  );
}
