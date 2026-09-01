'use client';

import { useEffect, useState } from 'react';
import { CalendarDays, FileSearch, Loader2, Search, X } from 'lucide-react';
import { toast } from 'react-toastify';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { api, type InvoiceReportResponse } from '@/lib/api';
import { ReportSummaryTable } from '@/components/reports/report-summary-table';
import { ReportItemsTable } from '@/components/reports/report-items-table';
import { ReportDownloadButton } from '@/components/reports/report-download-button';

const filterInputClass =
  'w-full h-9 text-sm px-3 py-1.5 border border-blue-600 dark:border-neutral-800 rounded-xl bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-150 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed';

const MONTHS = [
  { value: '01', label: 'January' },
  { value: '02', label: 'February' },
  { value: '03', label: 'March' },
  { value: '04', label: 'April' },
  { value: '05', label: 'May' },
  { value: '06', label: 'June' },
  { value: '07', label: 'July' },
  { value: '08', label: 'August' },
  { value: '09', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
];

// Fallback list used only if the years endpoint fails, so the filter
// keeps working (e.g. during rate limiting or backend downtime).
const STATIC_YEARS = (() => {
  const current = new Date().getFullYear();
  return Array.from({ length: 6 }, (_, i) => current - i);
})();

export default function ReportPage() {
  const [year, setYear] = useState('');
  const [month, setMonth] = useState('');
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<InvoiceReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Populate the Year dropdown with the user's actual invoice years
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.reports.getInvoiceYears();
        if (!cancelled) setAvailableYears(data.years);
      } catch {
        if (!cancelled) setAvailableYears(STATIC_YEARS);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSearch = async () => {
    let queryFrom = '';
    let queryTo = '';

    if (year) {
      // Year/month mode takes precedence over the From/To fields
      if (month) {
        const m = Number(month);
        const lastDay = new Date(Number(year), m, 0).getDate();
        queryFrom = `${year}-${month}-01`;
        queryTo = `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
      } else {
        queryFrom = `${year}-01-01`;
        queryTo = `${year}-12-31`;
      }
    } else {
      if (month) {
        toast.error('Please select a year along with the month');
        return;
      }
      if (!dateFrom || !dateTo) {
        toast.error('Please select both From and To dates, or pick a Year/Month');
        return;
      }
      if (dateFrom > dateTo) {
        toast.error('From date must not be after To date');
        return;
      }
      queryFrom = dateFrom;
      queryTo = dateTo;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await api.reports.getInvoiceReport({ date_from: queryFrom, date_to: queryTo });
      setReport(data);
    } catch (err) {
      setReport(null);
      const message = err instanceof Error ? err.message : 'Failed to generate report';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setYear('');
    setMonth('');
    setDateFrom('');
    setDateTo('');
    setReport(null);
    setError(null);
  };

  // Any non-empty filter means the user has set a filter
  const isFilterSet = year !== '' || month !== '' || dateFrom !== '' || dateTo !== '';

  return (
    <div className="max-w-7xl mx-auto p-3 sm:p-4 lg:p-5 space-y-3 lg:space-y-4">

      {/* Filter bar — grid below lg (tidy 1/2-col layout), flex-wrap with even
          spacing on laptop and up (matches the invoice history filter bar) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:flex-wrap lg:justify-around items-end gap-2 lg:gap-3 px-3 lg:px-4 py-2 lg:py-2.5 border-2 border-blue-600 rounded-4xl bg-white shadow-sm">
        <div className="flex flex-col gap-1 lg:min-w-30">
          <label className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
            <CalendarDays className="h-3 w-3" />
            Year
          </label>
          <Select value={year} onValueChange={setYear}>
            <SelectTrigger
              className="text-xs"
              style={{ height: '32px', padding: '4px 10px', borderRadius: '8px', fontSize: '12px', borderWidth: '1px', borderColor: '#2563eb' }}
              aria-label="Year"
            >
              <SelectValue placeholder="All Years" />
            </SelectTrigger>
            <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
              {availableYears.map((y) => (
                <SelectItem key={y} value={String(y)} className="text-xs rounded-md">
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1 lg:min-w-32.5">
          <label className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
            <CalendarDays className="h-3 w-3" />
            Month
          </label>
          <Select value={month} onValueChange={setMonth}>
            <SelectTrigger
              className="text-xs"
              style={{ height: '32px', padding: '4px 10px', borderRadius: '8px', fontSize: '12px', borderWidth: '1px', borderColor: '#2563eb' }}
              disabled={!year}
              aria-label="Month"
            >
              <SelectValue placeholder="All Months" />
            </SelectTrigger>
            <SelectContent className="rounded-xl border-blue-600 dark:border-neutral-800">
              {MONTHS.map((m) => (
                <SelectItem key={m.value} value={m.value} className="text-xs rounded-md">
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1 lg:min-w-37.5">
          <label className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
            <CalendarDays className="h-3 w-3" />
            From
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className={filterInputClass}
            disabled={year !== ''}
            aria-label="From date"
          />
        </div>
        <div className="flex flex-col gap-1 lg:min-w-37.5">
          <label className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
            <CalendarDays className="h-3 w-3" />
            To
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className={filterInputClass}
            disabled={year !== ''}
            aria-label="To date"
          />
        </div>
        <div className="flex flex-wrap items-end gap-2 lg:gap-3 sm:col-span-2 lg:contents">
          <Button type="button" size="default" onClick={handleSearch} disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            Search
          </Button>
          {isFilterSet && (
            <Button className="bg-red-600!" type="button" variant="outline" size="default" onClick={handleClear} disabled={loading}>
              <X className="h-4 w-4 mr-2" />
              Clear
            </Button>
          )}
          {report !== null && (
            <ReportDownloadButton
              dateFrom={report.date_from}
              dateTo={report.date_to}
              disabled={report.invoices.length === 0}
            />
          )}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Generating report…</p>
          </div>
        </div>
      )}

      {!loading && !error && report === null && (
        <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
          <FileSearch className="h-6 w-6 text-slate-300 dark:text-neutral-600" />
          <p className="mt-2 text-sm text-slate-500 dark:text-neutral-400">
            Select a year/month or a date range, then click Search to generate your report.
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-[#d72c0d] dark:text-[#ff6f59]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59]">Error generating report</h3>
              <p className="mt-1 text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
            </div>
          </div>
        </div>
      )}

      {!loading && report !== null && (
        <div className="space-y-4 sm:space-y-6">
          {report.invoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4 border-2 border-dashed border-blue-200 dark:border-neutral-800 rounded-4xl bg-white dark:bg-neutral-900">
              <FileSearch className="h-8 w-8 text-slate-300 dark:text-neutral-600" />
              <p className="mt-3 text-sm font-semibold text-slate-600 dark:text-neutral-300">
                No invoices found for the selected period
              </p>
              <p className="mt-1 text-xs text-slate-400 dark:text-neutral-500">
                Try widening the date range or selecting a different year/month.
              </p>
            </div>
          ) : (
            <>
              <ReportSummaryTable summary={report.summary} />
              {report.items_summary.length > 0 && (
                <ReportItemsTable items={report.items_summary} />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
