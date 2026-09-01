'use client';

import type { ReportItemSummary } from '@/lib/api';

interface ReportItemsTableProps {
  items: ReportItemSummary[];
}

/**
 * Item summary of the report: every product sold in the selected period
 * with its total quantity, sorted by quantity (highest first) by the
 * backend. Item names come from the user's saved products (/products)
 * when available, falling back to the raw product description.
 * Matches the card/table styling of the report page.
 */
export function ReportItemsTable({ items }: ReportItemsTableProps) {
  const formatQuantity = (quantity: number) =>
    new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3,
    }).format(quantity);

  return (
    <div className="rounded-2xl border-2 border-blue-600 bg-white dark:bg-neutral-900 shadow-sm overflow-hidden">
      <div className="px-3 lg:px-4 py-2 lg:py-2.5 border-b border-blue-200 dark:border-neutral-800 flex items-center justify-between gap-3">
        <p className="text-xs lg:text-sm font-bold text-slate-900 dark:text-neutral-100 uppercase tracking-wider">
          Items Summary
        </p>
        <p className="text-[10px] text-slate-500 dark:text-neutral-400">
          {items.length} item{items.length === 1 ? '' : 's'}
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-blue-50 dark:bg-neutral-800/60 text-[10px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
              <th className="text-left px-3 lg:px-4 py-2">Item Name</th>
              <th className="text-right px-3 lg:px-4 py-2 whitespace-nowrap">Quantity</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr
                key={`${item.item_name}-${index}`}
                className="border-t border-blue-100 dark:border-neutral-800/60"
              >
                <td className="px-3 lg:px-4 py-2 text-slate-700 dark:text-neutral-200">
                  {item.item_name}
                </td>
                <td className="px-3 lg:px-4 py-2 text-right font-semibold text-slate-900 dark:text-neutral-100 whitespace-nowrap">
                  {formatQuantity(item.quantity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
