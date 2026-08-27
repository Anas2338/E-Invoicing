'use client';

import type { ReportSummary } from '@/lib/api';

interface ReportSummaryTableProps {
  summary: ReportSummary;
}

/**
 * All tax totals of the report in a house-style card grid: 3 columns on
 * laptop screens, 2 on tablet, stacked on mobile, with the grand total as
 * a full-width highlighted strip so the whole report fits one screen.
 *
 * Labels match the PDF summary block exactly (report_pdf_service
 * SUMMARY_ROWS), so the on-screen totals and the downloaded PDF always
 * line up row for row.
 */
const SUMMARY_ROWS: { key: keyof ReportSummary; label: string; currency: boolean }[] = [
  { key: 'total_invoices', label: 'Total Number of Invoices', currency: false },
  { key: 'sales_value_excluding_st', label: 'Total Sales Value Excl. Tax', currency: true },
  { key: 'sales_tax', label: 'Total Sales Tax', currency: true },
  { key: 'sales_tax_withheld_at_source', label: 'Total Sales Tax Withheld at Source', currency: true },
  { key: 'further_tax', label: 'Total Further Tax', currency: true },
  { key: 'extra_tax', label: 'Total Extra Tax', currency: true },
  { key: 'fed_payable', label: 'Total FED Payable', currency: true },
  { key: 'withholding_tax_amount', label: 'Total Withholding Tax', currency: true },
  { key: 'discount', label: 'Total Discount', currency: true },
  { key: 'value_including_tax', label: 'Total Value Incl. Tax', currency: true },
];

export function ReportSummaryTable({ summary }: ReportSummaryTableProps) {
  const totalRow = SUMMARY_ROWS[SUMMARY_ROWS.length - 1];
  const statRows = SUMMARY_ROWS.slice(0, -1);

  // Plain number formatting without a currency prefix — the card labels
  // already describe what each amount is, so "PKR" is omitted.
  const formatAmount = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);

  const renderValue = (row: (typeof SUMMARY_ROWS)[number]) =>
    row.currency ? formatAmount(summary[row.key]) : summary[row.key];

  return (
    <div className="space-y-2.5 lg:space-y-3">
      {/* Stat cards — 3 cols on laptop, 2 on tablet, 1 on mobile */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 lg:gap-3">
        {statRows.map((row) => (
          <div
            key={row.key}
            className="rounded-xl border-2 border-blue-600 bg-blue-50 dark:bg-neutral-900 px-3 lg:px-4 py-2 lg:py-2.5"
          >
            <p className="text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
              {row.label}
            </p>
            <p className="mt-0.5 text-sm lg:text-base font-bold text-slate-900 dark:text-neutral-100">
              {renderValue(row)}
            </p>
          </div>
        ))}
      </div>

      {/* Grand total strip — stacks on phones so long amounts never overflow */}
      <div className="rounded-xl border-2 border-blue-600 bg-[#7c97f0]/10 dark:bg-neutral-800/70 px-3 lg:px-4 py-2 lg:py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-3">
        <p className="text-xs lg:text-sm font-extrabold text-black dark:text-neutral-100 uppercase tracking-wider">
          {totalRow.label}
        </p>
        <p className="text-sm lg:text-base font-extrabold text-[#008060] dark:text-[#00a876] whitespace-nowrap">
          {renderValue(totalRow)}
        </p>
      </div>
    </div>
  );
}
