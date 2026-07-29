'use client';

import { useState, useRef, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Eye, CheckCircle, Send, Trash2, Loader2, RefreshCw, Calendar } from 'lucide-react';
import { PrintInvoiceButton } from '@/components/invoices/PrintInvoiceButton';

interface Invoice {
  id: string;
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: string;
  environment: string;
  fbrReferenceNumber?: string;
  invoiceType: string;
  createdAt: string;
  scheduledDate?: string;
  scheduledTime?: string;
}

interface InvoiceTableProps {
  invoices: Invoice[];
  selectedInvoices?: Set<string>;
  onSelectionChange?: (selected: Set<string>) => void;
  onView?: (id: string) => void;
  onEdit?: (id: string) => void;
  onValidate?: (id: string) => void;
  onPost?: (id: string) => void;
  onDelete?: (id: string) => void;
  validatingInvoiceId?: string | null;
  postingInvoiceId?: string | null;
  deletingInvoiceId?: string | null;
  processingInvoiceIds?: string[];
  invoiceNumberFilter?: string;
  onInvoiceNumberFilterChange?: (value: string) => void;
  dateFromFilter?: string;
  onDateFromFilterChange?: (value: string) => void;
  dateToFilter?: string;
  onDateToFilterChange?: (value: string) => void;
  buyerNameFilter?: string;
  onBuyerNameFilterChange?: (value: string) => void;
  amountFilter?: string;
  onAmountFilterChange?: (value: string) => void;
  statusFilter?: string;
  onStatusFilterChange?: (value: string) => void;
  fbrRefFilter?: string;
  onFbrRefFilterChange?: (value: string) => void;
  // Pagination / cross-page select support
  totalFilteredCount?: number;
  allFilteredSelectableIds?: string[];
}

const statusOptions = [
  { value: 'all', label: 'All' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'VALIDATED', label: 'Valid' },
  { value: 'POSTED', label: 'Posted' },
  { value: 'FAILED', label: 'Failed' },
];

export function InvoiceTable({
  invoices,
  selectedInvoices = new Set(),
  onSelectionChange,
  onView,
  onEdit,
  onValidate,
  onPost,
  onDelete,
  validatingInvoiceId = null,
  postingInvoiceId = null,
  deletingInvoiceId = null,
  processingInvoiceIds = [],
  invoiceNumberFilter = '',
  onInvoiceNumberFilterChange = () => {},
  dateFromFilter = '',
  onDateFromFilterChange = () => {},
  dateToFilter = '',
  onDateToFilterChange = () => {},
  buyerNameFilter = '',
  onBuyerNameFilterChange = () => {},
  amountFilter = '',
  onAmountFilterChange = () => {},
  statusFilter = 'all',
  onStatusFilterChange = () => {},
  fbrRefFilter = '',
  onFbrRefFilterChange = () => {},
  totalFilteredCount,
  allFilteredSelectableIds,
}: InvoiceTableProps) {
  const [datePopoverOpen, setDatePopoverOpen] = useState(false);
  const datePopoverRef = useRef<HTMLDivElement>(null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [scrollbarWidth, setScrollbarWidth] = useState(0);
  const bodyScrollRef = useRef<HTMLDivElement>(null);

  const activeFilterCount = [
    invoiceNumberFilter, dateFromFilter, dateToFilter, buyerNameFilter, amountFilter, fbrRefFilter,
  ].filter(v => v !== '').length + (statusFilter !== 'all' ? 1 : 0);

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

  const hasDateFilter = dateFromFilter || dateToFilter;

  const getStatusColor = (status: string) => {
  switch (status.toUpperCase()) {
    case 'DRAFT':
    case 'PENDING':
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-blue-400 via-blue-500 to-blue-600 border border-blue-400/40 shadow-[0_5px_12px_-3px_rgba(59,130,246,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
    case 'VALIDATED':
    case 'TRANSFERRED':
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-sky-400 via-sky-500 to-sky-600 border border-sky-400/40 shadow-[0_5px_12px_-3px_rgba(14,165,233,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
    case 'POSTED':
    case 'SUBMITTED':
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-emerald-400 via-emerald-500 to-emerald-600 border border-emerald-400/40 shadow-[0_5px_12px_-3px_rgba(16,185,129,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
    case 'FAILED':
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-rose-400 via-rose-500 to-rose-600 border border-rose-400/40 shadow-[0_5px_12px_-3px_rgba(244,63,94,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
    case 'EXPIRED':
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-slate-400 via-slate-500 to-slate-600 border border-slate-400/40 shadow-[0_5px_12px_-3px_rgba(100,116,139,0.3),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)] transition-all duration-200 hover:brightness-110 active:scale-[0.97] cursor-pointer select-none';
    default:
      return 'px-1 lg:px-1.5 xl:px-2.5 py-0.5 text-[9px] lg:text-[10px] xl:text-xs font-black tracking-wider lg:tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-gray-400 to-gray-500';
  }
};

  const formatStatus = (status: string) => {
    if (status.toUpperCase() === 'VALIDATED') return 'Valid';
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  };

  const isSelectable = (status: string) =>
    status === 'DRAFT' || status === 'VALIDATED' || status === 'FAILED' || status === 'TRANSFERRED' || status === 'POSTED';

  const isDeletable = (status: string) =>
    status === 'DRAFT' || status === 'VALIDATED' || status === 'FAILED' || status === 'TRANSFERRED';

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;

    if (checked) {
      // When pagination is active, allFilteredSelectableIds contains ALL selectable
      // invoice IDs across all pages — select those instead of just the current page.
      const selectableIds = new Set(
        allFilteredSelectableIds && allFilteredSelectableIds.length > invoices.length
          ? allFilteredSelectableIds
          : invoices
              .filter(inv => isSelectable(inv.status))
              .map(inv => inv.id)
      );
      onSelectionChange(selectableIds);
    } else {
      onSelectionChange(new Set());
    }
  };

  const handleSelectInvoice = (invoiceId: string, checked: boolean) => {
    if (!onSelectionChange) return;

    const newSelection = new Set(selectedInvoices);
    if (checked) {
      newSelection.add(invoiceId);
    } else {
      newSelection.delete(invoiceId);
    }
    onSelectionChange(newSelection);
  };

  const selectableInvoices = invoices.filter(inv => isSelectable(inv.status));
  const allSelectableSelected = selectableInvoices.length > 0 &&
    selectableInvoices.every(inv => selectedInvoices.has(inv.id));
  const someSelectableSelected = selectableInvoices.some(inv => selectedInvoices.has(inv.id));

  // High-performance focused input styling with adjusted colors and clean borders
  const filterInputClass = "w-full h-8 text-xs px-2.5 py-1 border border-blue-600 dark:border-neutral-800 rounded-lg bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-150 shadow-sm";

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
        Try adjusting your filters or create a new invoice to populate this space.
      </p>
    </div>
  );

  return (
    <>
      {/* Mobile/Tablet Card View */}
      <div className="block lg:hidden p-0.5 space-y-3">

        {/* Mobile Filter Toggle & Panel */}
        <div>
          <button
            type="button"
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 ${
              showMobileFilters
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-white dark:bg-neutral-900 border-2 border-blue-600 text-blue-600 dark:text-blue-400'
            }`}
          >
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              Filters
            </span>
            {activeFilterCount > 0 && (
              <span className="bg-red-500 text-white text-xs font-black px-2 py-0.5 rounded-full leading-none">
                {activeFilterCount}
              </span>
            )}
          </button>

          {showMobileFilters && (
            <div className="mt-2 bg-white dark:bg-neutral-950 rounded-2xl border border-slate-200 dark:border-neutral-800 p-3 shadow-sm space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Invoice #..."
                  value={invoiceNumberFilter}
                  onChange={(e) => onInvoiceNumberFilterChange(e.target.value)}
                  className={filterInputClass}
                />
                <input
                  type="text"
                  placeholder="FBR Ref..."
                  value={fbrRefFilter}
                  onChange={(e) => onFbrRefFilterChange(e.target.value)}
                  className={filterInputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="relative">
                  <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                  <input
                    type="date"
                    value={dateFromFilter}
                    onChange={(e) => onDateFromFilterChange(e.target.value)}
                    placeholder="From date"
                    className={`${filterInputClass} pl-8`}
                  />
                </div>
                <div className="relative">
                  <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                  <input
                    type="date"
                    value={dateToFilter}
                    onChange={(e) => onDateToFilterChange(e.target.value)}
                    placeholder="To date"
                    className={`${filterInputClass} pl-8`}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Buyer name..."
                  value={buyerNameFilter}
                  onChange={(e) => onBuyerNameFilterChange(e.target.value)}
                  className={filterInputClass}
                />
                <input
                  type="text"
                  placeholder="Amount..."
                  value={amountFilter}
                  onChange={(e) => onAmountFilterChange(e.target.value)}
                  className={filterInputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Select value={statusFilter} onValueChange={onStatusFilterChange}>
                  <SelectTrigger
                    className="text-xs"
                    style={{ height: '32px', padding: '4px 10px', borderRadius: '8px', fontSize: '12px', borderWidth: '1px', borderColor: '#2563eb' }}
                  >
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
                    {statusOptions.map(option => (
                      <SelectItem key={option.value} value={option.value} className="text-xs rounded-md">
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    onInvoiceNumberFilterChange('');
                    onDateFromFilterChange('');
                    onDateToFilterChange('');
                    onBuyerNameFilterChange('');
                    onAmountFilterChange('');
                    onStatusFilterChange('all');
                    onFbrRefFilterChange('');
                  }}
                  className="w-full text-center text-xs font-semibold text-red-500 hover:text-red-600 py-1.5"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>

        {invoices.length === 0 && (
          <div className="bg-white dark:bg-neutral-950 rounded-2xl border border-slate-100 dark:border-neutral-900 shadow-sm">
            <EmptyStateContent />
          </div>
        )}
        {/* Cross-page selection banner — mobile */}
        {allFilteredSelectableIds && allFilteredSelectableIds.length > invoices.length && allSelectableSelected && selectedInvoices.size > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40 rounded-lg">
            <span className="text-xs text-amber-800 dark:text-amber-300 font-medium">
              All {invoices.length} on this page selected.
            </span>
            <button
              type="button"
              onClick={() => {
                if (!onSelectionChange) return;
                onSelectionChange(new Set(allFilteredSelectableIds));
              }}
              className="text-xs font-bold text-amber-700 dark:text-amber-400 underline hover:no-underline"
            >
              Select all {allFilteredSelectableIds.length} matching invoices.
            </button>
          </div>
        )}
        {invoices.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
        {invoices.map((invoice) => {
          const canDelete = isDeletable(invoice.status);
          const isSelected = selectedInvoices.has(invoice.id);

          return (
            <div
              key={invoice.id}
              className={`bg-white dark:bg-neutral-950 rounded-2xl border transition-all duration-200 shadow-sm hover:shadow-md ${
                isSelected 
                  ? 'border-emerald-500 ring-1 ring-emerald-500/30 bg-emerald-50/10 dark:bg-emerald-500/[0.02]' 
                  : 'border-slate-200/80 dark:border-neutral-900 hover:border-slate-300 dark:hover:border-neutral-800'
              }`}
            >
              <div className="p-4">
                {/* Header with checkbox and invoice number */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3 flex-1">
                    {onSelectionChange && (
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                        disabled={!isSelectable(invoice.status)}
                        aria-label={`Select invoice ${invoice.invoiceNumber}`}
                        className="mt-1 data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500"
                      />
                    )}
                    <div className="flex-1">
                      <div className="text-sm font-bold text-slate-900 dark:text-neutral-100 tracking-tight">{invoice.invoiceNumber}</div>
                      <div className="text-xs font-medium text-slate-400 dark:text-neutral-500 mt-0.5">{invoice.invoiceType}</div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-end">
                    <Badge className={`${getStatusColor(invoice.status)} border px-2.5 py-0.5 text-xs font-semibold tracking-wide rounded-full shadow-sm`}>
                      {formatStatus(invoice.status)}
                    </Badge>
                  </div>
                </div>

                {/* Invoice Details */}
                <div className="space-y-2.5 mb-4 text-xs font-medium">
                  <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50">
                    <span className="text-slate-400 dark:text-neutral-500">Date</span>
                    <span className="text-slate-700 dark:text-neutral-300 font-semibold">
                      {new Date(invoice.date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        timeZone: 'Asia/Karachi'
                      })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50">
                    <span className="text-slate-400 dark:text-neutral-500">Buyer</span>
                    <span className="text-slate-800 dark:text-neutral-200 truncate ml-4 max-w-[180px] font-semibold">{invoice.buyerName}</span>
                  </div>
                  <div className="flex justify-between items-center py-0.5 border-b border-slate-50 dark:border-neutral-900/50">
                    <span className="text-slate-400 dark:text-neutral-500">Amount</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold text-sm">
                      PKR {invoice.totalAmount.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </span>
                  </div>
                  {invoice.fbrReferenceNumber && (
                    <div className="flex justify-between items-center py-0.5">
                      <span className="text-slate-400 dark:text-neutral-500">FBR Ref</span>
                      <span className="text-slate-600 dark:text-neutral-400 font-mono text-[11px] bg-slate-50 dark:bg-neutral-900 px-1.5 py-0.5 rounded border border-slate-100 dark:border-neutral-800/60">{invoice.fbrReferenceNumber}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-100 dark:border-neutral-900">
                  {onView && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onView(invoice.id)}
                      disabled={processingInvoiceIds.includes(invoice.id)}
                      className="flex-1 min-w-[80px] h-9 text-xs rounded-xl font-semibold border-slate-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Eye className="h-4 w-4 mr-1.5 opacity-80" />
                      View
                    </Button>
                  )}
                  {onValidate && invoice.status === 'DRAFT' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onValidate(invoice.id)}
                      disabled={validatingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                      className="flex-1 min-w-[80px] h-9 text-xs rounded-xl font-semibold border-amber-200 text-amber-700 bg-amber-50/50 hover:bg-amber-50 dark:border-amber-500/30 dark:text-amber-400 dark:bg-amber-500/5 dark:hover:bg-amber-500/10"
                    >
                      {validatingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-1.5" />
                      )}
                      {validatingInvoiceId === invoice.id ? 'Validating...' : 'Validate'}
                    </Button>
                  )}
                  {onValidate && invoice.status === 'FAILED' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onValidate(invoice.id)}
                      disabled={validatingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                      className="flex-1 min-w-[80px] h-9 text-xs rounded-xl font-semibold border-emerald-500/40 text-emerald-600 bg-emerald-50/40 hover:bg-emerald-500 hover:text-white dark:border-emerald-500/30 dark:text-emerald-400 dark:bg-emerald-500/5 dark:hover:bg-emerald-500 dark:hover:text-neutral-950 transition-all"
                    >
                      {validatingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-1.5" />
                      )}
                      {validatingInvoiceId === invoice.id ? 'Retrying...' : 'Retry'}
                    </Button>
                  )}
                  {onPost && (invoice.status === 'VALIDATED' || invoice.status === 'TRANSFERRED') && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPost(invoice.id)}
                      disabled={postingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                      className="flex-1 min-w-[80px] h-9 text-xs rounded-xl font-semibold border-blue-200 text-blue-700 bg-blue-50/50 hover:bg-blue-50 dark:border-blue-500/30 dark:text-blue-400 dark:bg-blue-500/5 dark:hover:bg-blue-500/10"
                    >
                      {postingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                      {postingInvoiceId === invoice.id ? 'Posting...' : 'Post'}
                    </Button>
                  )}
                  {invoice.status === 'POSTED' && (
                    <div className="flex-1 min-w-[80px]">
                      <PrintInvoiceButton
                        invoiceId={invoice.id}
                        invoiceNumber={invoice.invoiceNumber}
                        status={invoice.status}
                        className="w-full h-9 text-xs rounded-xl font-semibold shadow-sm"
                      />
                    </div>
                  )}
                  {onDelete && canDelete && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onDelete(invoice.id)}
                      disabled={deletingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                      className="flex-1 min-w-[80px] h-9 text-xs rounded-xl font-semibold border-rose-100 text-rose-600 bg-rose-50/30 hover:bg-rose-50 dark:border-rose-950 dark:text-rose-400 dark:bg-rose-950/20 dark:hover:bg-rose-950/40"
                    >
                      {deletingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4 mr-1.5" />
                      )}
                      {deletingInvoiceId === invoice.id ? 'Deleting...' : 'Delete'}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        </div>
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden lg:flex lg:flex-col lg:gap-2 h-full">
        <div className="overflow-x-auto rounded-2xl flex-1 min-h-0">
        <div className="min-w-[880px] flex flex-col gap-2 h-full">

        {/* Header wrapper — right-padding synced to body scrollbar */}
        <div style={{ paddingRight: scrollbarWidth }}>
        {/*table 1 heading*/}
        <table className="w-full table-fixed bg-[#7c97f0] rounded-4xl flex-shrink-0 border-separate border-spacing-0">
          <thead>
            {/* Column Headers */}
            <tr>
              {onSelectionChange && (
                <th className="border-r-2 border-[#FFFFFF] w-[4%] px-1 pt-3.5 pb-2"></th>
              )}
              <th className="border-r-2 border-[#FFFFFF] w-[11%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Invoice #
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[16%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                FBR Ref
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[8%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Date
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[29%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Buyer Name
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[10%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Amount
              </th>
              <th className="border-r-2 border-[#FFFFFF] w-[8%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Status
              </th>
              <th className="w-[14%] px-2 py-2 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">
                Actions
              </th>
            </tr>
          </thead>
        </table>

        {/*table 2 heading*/}
        <table className="w-full table-fixed rounded-4xl flex-shrink-0">
            <thead>
              {/* Filter Inputs Row */}
              <tr>
                {onSelectionChange && (
                  <th scope="col" className="w-[4%] px-1 py-2">
                    <Checkbox
                      checked={allSelectableSelected}
                      onCheckedChange={handleSelectAll}
                      aria-label="Select all invoices"
                      className={`data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500 ${someSelectableSelected && !allSelectableSelected ? 'data-[state=checked]:bg-slate-400 dark:data-[state=checked]:bg-neutral-600' : ''}`}
                    />
                  </th>
                )}
                <th scope="col" className="w-[11%] px-1 py-2">
                  <input
                    type="text"
                    placeholder="Filter ID..."
                    value={invoiceNumberFilter}
                    onChange={(e) => onInvoiceNumberFilterChange(e.target.value)}
                    className={filterInputClass}
                  />
                </th>
                <th scope="col" className="w-[16%] px-1 py-2">
                  <input
                    type="text"
                    placeholder="Filter FBR..."
                    value={fbrRefFilter}
                    onChange={(e) => onFbrRefFilterChange(e.target.value)}
                    className={filterInputClass}
                  />
                </th>
                <th scope="col" className="w-[8%] px-1 py-2">
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
                          ? `${dateFromFilter || '...'} – ${dateToFilter || '...'}`
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
                              value={dateFromFilter}
                              onChange={(e) => onDateFromFilterChange(e.target.value)}
                              className={filterInputClass}
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase mb-0.5">To</label>
                            <input
                              type="date"
                              value={dateToFilter}
                              onChange={(e) => onDateToFilterChange(e.target.value)}
                              className={filterInputClass}
                            />
                          </div>
                          {hasDateFilter && (
                            <button
                              type="button"
                              onClick={() => {
                                onDateFromFilterChange('');
                                onDateToFilterChange('');
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
                <th scope="col" className="w-[29%] px-1 py-2">
                  <input
                    type="text"
                    placeholder="Filter buyer..."
                    value={buyerNameFilter}
                    onChange={(e) => onBuyerNameFilterChange(e.target.value)}
                    className={filterInputClass}
                  />
                </th>
                <th scope="col" className="w-[10%] px-1 py-2">
                  <input
                    type="text"
                    placeholder="Filter amt..."
                    value={amountFilter}
                    onChange={(e) => onAmountFilterChange(e.target.value)}
                    className={filterInputClass}
                  />
                </th>
                <th scope="col" className="w-[8%] px-1 py-2">
                  <Select value={statusFilter} onValueChange={onStatusFilterChange}>
                    <SelectTrigger
                      className="text-[10px] text-slate-400"
                      style={{ height: '32px', padding: '2px 6px', borderRadius: '8px', fontSize: '10px', borderWidth: '1px', color: '#94a3b8', borderColor: '#2563eb' }}
                    >
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
                      {statusOptions.map(option => (
                        <SelectItem key={option.value} value={option.value} className="text-xs rounded-md">
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </th>
                <th scope="col" className="w-[14%] pl-1 pr-0 py-2">
                  {activeFilterCount > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        onInvoiceNumberFilterChange('');
                        onDateFromFilterChange('');
                        onDateToFilterChange('');
                        onBuyerNameFilterChange('');
                        onAmountFilterChange('');
                        onStatusFilterChange('all');
                        onFbrRefFilterChange('');
                      }}
                      className="text-[10px] font-semibold text-red-500 hover:text-red-600 transition-colors px-1 py-1"
                    >
                      Clear
                    </button>
                  )}
                </th>
              </tr>
              </thead>
        </table>

        </div>{/* end header wrapper */}

        {/* Cross-page selection banner */}
        {/* {allFilteredSelectableIds && allFilteredSelectableIds.length > invoices.length && allSelectableSelected && selectedInvoices.size > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40 rounded-lg mx-1 mb-1">
            <span className="text-xs text-amber-800 dark:text-amber-300 font-medium">
              All {invoices.length} invoice{invoices.length !== 1 ? 's' : ''} on this page selected.
            </span>
            <button
              type="button"
              onClick={() => {
                if (!onSelectionChange) return;
                onSelectionChange(new Set(allFilteredSelectableIds));
              }}
              className="text-xs font-bold text-amber-700 dark:text-amber-400 underline hover:no-underline"
            >
              Select all {allFilteredSelectableIds.length} matching invoices.
            </button>
          </div>
        )} */}

        {/*table 3 body — scrollable*/}
        {invoices.length === 0 ? (
          <div className="flex-1 flex items-start justify-center">
            <EmptyStateContent />
          </div>
        ) : (
        <div className="flex-1 min-h-0 flex flex-col items-start">
        <div ref={bodyScrollRef} className="w-full max-h-full overflow-y-auto overflow-x-hidden rounded-4xl bg-blue-50 border-2 border-blue-600">
        <table className="w-full table-fixed border-separate border-spacing-0">
          <tbody className=' border-1 border-blue-200'>
            {invoices.map((invoice) => {
              const canDelete = isDeletable(invoice.status);
              const isSelected = selectedInvoices.has(invoice.id);

              return (
                <tr
                  key={invoice.id}
                  className={`group transition-colors duration-150 ${
                    isSelected
                      ? 'bg-emerald-50/20'
                      : 'hover:bg-slate-50/60'
                  }`}
                >
                  {onSelectionChange && (
                    <td className="border-r-2 border-b-1 border-blue-200 px-2.5 py-4 align-middle w-[4%]">
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                        disabled={!isSelectable(invoice.status)}
                        aria-label={`Select invoice ${invoice.invoiceNumber}`}
                        className="data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500"
                      />
                    </td>
                  )}
                  <td className="px-1 py-4 align-middle w-[11%] border-r-2 border-b-1 border-blue-200">
                    <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700">{invoice.invoiceNumber}</div>
                    <div className="text-[9px] lg:text-[10px] xl:text-xs font-medium text-slate-500 truncate mt-0.5">{invoice.invoiceType}</div>
                  </td>
                  <td className="px-1 py-4 align-middle w-[16%] border-r-2 border-blue-200 border-b-1">
                    <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700 break-all leading-snug">
                      {invoice.fbrReferenceNumber || '—'}
                    </div>
                  </td>
                  <td className="px-1 py-4 w-[8%] border-r-2 border-blue-200 border-b-1 text-[10px] lg:text-[11px] xl:text-[13px] font-medium text-slate-700 whitespace-nowrap text-center align-middle">
                    {new Date(invoice.date).toLocaleDateString('en-GB', {
                      timeZone: 'Asia/Karachi'
                    })}
                  </td>
                  <td className="px-2 py-4 w-[29%] border-r-2 border-b-1 border-blue-200">
                    <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700 truncate">{invoice.buyerName}</div>
                  </td>
                  <td className="px-1 py-4 w-[10%] border-r-2 border-b-1 border-blue-200 align-middle">
                    <div className="text-[11px] lg:text-[13px] xl:text-sm font-medium text-slate-700 whitespace-nowrap text-right">
                       {invoice.totalAmount.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </div>
                  </td>
                  <td className="px-1 py-4 text-center w-[8%] border-r-2 border-b-1 border-blue-200">
                    <Badge className={`${getStatusColor(invoice.status)}`}>
                      {formatStatus(invoice.status)}
                    </Badge>
                  </td>
                  <td className="pl-1 pr-0 py-4 text-center align-middle w-[14%] border-b-1 border-blue-200">
                    <div className="flex items-center justify-center gap-1">
                      {onView && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => onView(invoice.id)}
                          disabled={processingInvoiceIds.includes(invoice.id)}
                          className="h-10 w-10 rounded-lg border-slate-200 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      )}
                      {onValidate && invoice.status === 'DRAFT' && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => onValidate(invoice.id)}
                          disabled={validatingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                          className="h-10 w-10 rounded-lg border-amber-200 text-amber-600 bg-amber-50/30 hover:bg-amber-50 dark:border-amber-500/30 dark:text-amber-400 dark:bg-amber-500/5 dark:hover:bg-amber-500/20 shadow-sm"
                          title="Validate"
                        >
                          {validatingInvoiceId === invoice.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <CheckCircle className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      {onValidate && invoice.status === 'FAILED' && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => onValidate(invoice.id)}
                          disabled={validatingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                          className="h-10 w-10 rounded-lg border-emerald-500/30 text-emerald-600 bg-emerald-50/20 hover:bg-emerald-500 hover:text-white dark:border-emerald-500/30 dark:text-emerald-400 dark:bg-emerald-500/5 dark:hover:bg-emerald-500 dark:hover:text-neutral-950 shadow-sm transition-all"
                          title="Retry"
                        >
                          {validatingInvoiceId === invoice.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      {onPost && (invoice.status === 'VALIDATED' || invoice.status === 'TRANSFERRED') && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => onPost(invoice.id)}
                          disabled={postingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                          className="h-10 w-10 rounded-lg border-blue-200 text-blue-600 bg-blue-50/30 hover:bg-blue-50 dark:border-blue-500/30 dark:text-blue-400 dark:bg-blue-500/5 dark:hover:bg-blue-500/20 shadow-sm"
                          title="Post to FBR"
                        >
                          {postingInvoiceId === invoice.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Send className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      {invoice.status === 'POSTED' && (
                        <PrintInvoiceButton
                          invoiceId={invoice.id}
                          invoiceNumber={invoice.invoiceNumber}
                          status={invoice.status}
                          variant="outline"
                          size="icon"
                          className="h-10 w-10 rounded-lg border-slate-200 dark:border-neutral-800 shadow-sm"
                        />
                      )}
                      {onDelete && canDelete && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => onDelete(invoice.id)}
                          disabled={deletingInvoiceId === invoice.id || processingInvoiceIds.includes(invoice.id)}
                          className="h-10 w-10 rounded-lg border-rose-100 text-rose-500 hover:text-rose-600 bg-rose-50/20 dark:border-rose-950/60 dark:text-rose-400 dark:bg-rose-950/20 dark:hover:bg-rose-900/40 shadow-sm transition-all"
                          title="Delete"
                        >
                          {deletingInvoiceId === invoice.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
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
        </div>
        </div>
      </div>
    </>
  );
}