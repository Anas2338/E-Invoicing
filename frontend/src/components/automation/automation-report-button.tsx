'use client';

import { useState } from 'react';
import {
  BarChart3,
  FileSpreadsheet,
  FileText,
  Landmark,
  Loader2,
  Receipt,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  automationApi,
  type AutomationReportFilters,
  type AutomationReportFormat,
} from '@/services/automationApi';

/** The two tax reports the menu groups. */
type ReportMenu = 'sales-tax' | 'income-tax';

/**
 * Everything the menu needs per format. The format string is also the
 * endpoint's path segment, so it is not repeated here.
 */
const FORMAT_META: Record<
  AutomationReportFormat,
  {
    label: string;
    extension: 'pdf' | 'csv';
    filePrefix: string;
    menu: ReportMenu;
    icon: LucideIcon;
  }
> = {
  pdf: {
    label: 'PDF',
    extension: 'pdf',
    filePrefix: 'automation_invoice_report',
    menu: 'sales-tax',
    icon: FileText,
  },
  csv: {
    label: 'CSV',
    extension: 'csv',
    filePrefix: 'automation_invoice_report',
    menu: 'sales-tax',
    icon: FileSpreadsheet,
  },
  'party-wise-pdf': {
    label: 'Party-wise PDF',
    extension: 'pdf',
    filePrefix: 'automation_party_wise_report',
    menu: 'sales-tax',
    icon: Users,
  },
  'income-tax-pdf': {
    label: 'Income Tax PDF',
    extension: 'pdf',
    filePrefix: 'automation_income_tax_report',
    menu: 'income-tax',
    icon: FileText,
  },
  'income-tax-csv': {
    label: 'Income Tax CSV',
    extension: 'csv',
    filePrefix: 'automation_income_tax_report',
    menu: 'income-tax',
    icon: FileSpreadsheet,
  },
  'income-tax-party-wise-pdf': {
    label: 'Party-wise Income Tax PDF',
    extension: 'pdf',
    filePrefix: 'automation_party_wise_income_tax_report',
    menu: 'income-tax',
    icon: Users,
  },
};

/** Menu structure, in render order. */
const MENUS: {
  key: ReportMenu;
  label: string;
  icon: LucideIcon;
  formats: AutomationReportFormat[];
}[] = [
  {
    key: 'sales-tax',
    label: 'Sales Tax',
    icon: Receipt,
    formats: ['pdf', 'csv', 'party-wise-pdf'],
  },
  {
    key: 'income-tax',
    label: 'Income Tax',
    icon: Landmark,
    formats: ['income-tax-pdf', 'income-tax-csv', 'income-tax-party-wise-pdf'],
  },
];

interface AutomationReportButtonProps {
  /** The dashboard's current filters, applied to the report as-is. */
  filters: AutomationReportFilters;
  /** Sizing comes from the sidebar slot the button sits in. */
  className?: string;
}

/**
 * Sidebar report button for the automation dashboard.
 *
 * Downloads a report over the invoices the dashboard is currently filtered
 * to — built from the automation database, so it also covers invoices that
 * have not been transferred to the main database yet.
 *
 * Not disabled when the filtered list is empty: an empty selection is a
 * legitimate report (an empty-state PDF, or a header-only CSV), and the
 * dashboard's own list can be empty while older matching rows exist.
 */
export function AutomationReportButton({
  filters,
  className = '',
}: AutomationReportButtonProps) {
  const [generating, setGenerating] = useState<AutomationReportFormat | null>(null);

  const handleDownload = async (format: AutomationReportFormat) => {
    const { label, extension, filePrefix } = FORMAT_META[format];
    setGenerating(format);

    try {
      const { blob, filename } = await automationApi.downloadReport(format, filters);
      const url = window.URL.createObjectURL(blob);

      // Prefer the server's filename: it names the period the report actually
      // covered, which an download with no date filter only knows server-side.
      const downloadName =
        filename ||
        `${filePrefix}_${filters.date_from ?? 'all'}_${filters.date_to ?? 'all'}.${extension}`;

      // Detect mobile: iOS Safari ignores the download attribute on anchor
      // clicks, so the PDF is opened in a new tab where the native viewer
      // offers share/save. CSV has no inline viewer, so it always downloads.
      const openInNewTab =
        extension === 'pdf' && /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent);

      if (openInNewTab) {
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
          toast.error('Please allow pop-ups to view the report PDF');
        } else {
          toast.success('Report PDF opened — use share/save to download');
        }
        // The new tab still needs the blob URL alive while it loads.
        setTimeout(() => window.URL.revokeObjectURL(url), 3000);
      } else {
        const link = document.createElement('a');
        link.href = url;
        link.download = downloadName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        toast.success(`Report ${label} downloaded successfully`);
      }
    } catch (error) {
      console.error(`Report ${label} generation failed:`, error);
      toast.error(
        error instanceof Error ? error.message : `Failed to generate report ${label}`
      );
    } finally {
      setGenerating(null);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={generating !== null}
          className={`border-slate-500 text-slate-600 ${className}`}
          title="Download report for the current filters"
        >
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            // Same icon as the main navigation's Report button, so the two
            // entry points to a report read as the same action.
            <BarChart3 className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        // The sidebar hugs the left edge of the viewport, so the menu opens
        // to the right of it rather than underneath, where it would be
        // clipped on narrow screens.
        side="right"
        align="start"
        className="rounded-xl border-blue-600 dark:border-neutral-800"
      >
        {MENUS.map((menu, index) => {
          const MenuIcon = menu.icon;

          return (
            <div key={menu.key}>
              {index > 0 && <DropdownMenuSeparator />}
              <DropdownMenuLabel className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500 dark:text-neutral-400">
                <MenuIcon className="h-3.5 w-3.5" />
                {menu.label}
              </DropdownMenuLabel>
              {menu.formats.map((format) => {
                const { label, icon: ItemIcon } = FORMAT_META[format];

                return (
                  <DropdownMenuItem
                    key={format}
                    className="text-xs cursor-pointer gap-2"
                    disabled={generating !== null}
                    onSelect={() => handleDownload(format)}
                  >
                    {generating === format ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ItemIcon className="h-4 w-4" />
                    )}
                    Download {label}
                  </DropdownMenuItem>
                );
              })}
            </div>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
