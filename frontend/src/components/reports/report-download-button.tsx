'use client';

import { useState } from 'react';
import {
  ChevronDown,
  FileSpreadsheet,
  FileText,
  Landmark,
  Loader2,
  Receipt,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { toast } from 'react-toastify';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

/** The two tax reports the dropdowns download. */
type ReportMenu = 'sales-tax' | 'income-tax';

type ReportFormat =
  | 'pdf'
  | 'csv'
  | 'party-pdf'
  | 'income-tax-pdf'
  | 'income-tax-csv'
  | 'income-tax-party-pdf';

const FORMAT_META: Record<
  ReportFormat,
  { label: string; extension: string; path: string; filePrefix: string; menu: ReportMenu }
> = {
  pdf: {
    label: 'PDF',
    extension: 'pdf',
    path: 'pdf',
    filePrefix: 'invoice_report',
    menu: 'sales-tax',
  },
  csv: {
    label: 'CSV',
    extension: 'csv',
    path: 'csv',
    filePrefix: 'invoice_report',
    menu: 'sales-tax',
  },
  'party-pdf': {
    label: 'Party-wise PDF',
    extension: 'pdf',
    path: 'party-wise-pdf',
    filePrefix: 'party_wise_report',
    menu: 'sales-tax',
  },
  'income-tax-pdf': {
    label: 'Income Tax PDF',
    extension: 'pdf',
    path: 'income-tax-pdf',
    filePrefix: 'income_tax_report',
    menu: 'income-tax',
  },
  'income-tax-csv': {
    label: 'Income Tax CSV',
    extension: 'csv',
    path: 'income-tax-csv',
    filePrefix: 'income_tax_report',
    menu: 'income-tax',
  },
  'income-tax-party-pdf': {
    label: 'Party-wise Income Tax PDF',
    extension: 'pdf',
    path: 'income-tax-party-wise-pdf',
    filePrefix: 'party_wise_income_tax_report',
    menu: 'income-tax',
  },
};

/** Dropdown contents, in the order they render. */
const MENUS: {
  key: ReportMenu;
  label: string;
  icon: LucideIcon;
  formats: { format: ReportFormat; label: string; icon: LucideIcon }[];
}[] = [
  {
    key: 'sales-tax',
    label: 'Sales Tax',
    icon: Receipt,
    formats: [
      { format: 'pdf', label: 'Download PDF', icon: FileText },
      { format: 'csv', label: 'Download CSV', icon: FileSpreadsheet },
      { format: 'party-pdf', label: 'Download Party-wise PDF', icon: Users },
    ],
  },
  {
    key: 'income-tax',
    label: 'Income Tax',
    icon: Landmark,
    formats: [
      { format: 'income-tax-pdf', label: 'Download Income Tax PDF', icon: FileText },
      { format: 'income-tax-csv', label: 'Download Income Tax CSV', icon: FileSpreadsheet },
      {
        format: 'income-tax-party-pdf',
        label: 'Download Party-wise Income Tax PDF',
        icon: Users,
      },
    ],
  },
];

interface ReportDownloadButtonProps {
  dateFrom: string;
  dateTo: string;
  buyerName?: string;
  buyerNtnCnic?: string;
  className?: string;
  disabled?: boolean;
}

/**
 * Two download dropdowns for the already-searched filters:
 * - Sales Tax: the invoice PDF summary, a CSV line-item export, and the
 *   party-wise PDF (per-customer totals).
 * - Income Tax: the same three shapes carrying the 236G / 236H position
 *   instead of the sales tax columns.
 *
 * Mirrors PrintInvoiceButton's fetch + blob + anchor mechanism; GET needs
 * no CSRF header, credentials are included so the httpOnly cookie travels.
 */
export function ReportDownloadButton({
  dateFrom,
  dateTo,
  buyerName = '',
  buyerNtnCnic = '',
  className = '',
  disabled = false,
}: ReportDownloadButtonProps) {
  const [generating, setGenerating] = useState<ReportFormat | null>(null);

  const handleDownload = async (format: ReportFormat) => {
    const { label, extension, path, filePrefix } = FORMAT_META[format];
    setGenerating(format);

    try {
      const queryParams = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
      if (buyerName) queryParams.append('buyer_name', buyerName);
      if (buyerNtnCnic) queryParams.append('buyer_ntn_cnic', buyerNtnCnic);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1'}/reports/invoices/${path}?${queryParams.toString()}`,
        {
          credentials: 'include', // Send httpOnly cookies
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || `Failed to generate report ${label}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const filename = `${filePrefix}_${dateFrom}_${dateTo}.${extension}`;

      // Detect mobile: iOS Safari ignores the download attribute on anchor
      // clicks, so the PDF is opened in a new tab where the native viewer
      // offers share/save. CSV has no inline viewer, so it always downloads.
      const openInNewTab = extension === 'pdf' && /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent);

      if (openInNewTab) {
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
          toast.error('Please allow pop-ups to view the report PDF');
        } else {
          toast.success('Report PDF opened — use share/save to download');
        }
      } else {
        // On desktop, trigger a direct download
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success(`Report ${label} downloaded successfully`);
      }

      // Cleanup blob URL after a delay (new tab needs it still alive)
      if (openInNewTab) {
        setTimeout(() => window.URL.revokeObjectURL(url), 3000);
      } else {
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error(`Report ${label} generation failed:`, error);

      const errorMessage = error instanceof Error ? error.message : `Failed to generate report ${label}`;
      toast.error(errorMessage);
    } finally {
      setGenerating(null);
    }
  };

  return (
    <>
      {MENUS.map((menu) => {
        const MenuIcon = menu.icon;
        // Only the button whose own format is in flight shows the spinner;
        // both stay disabled so a second download can't race the first.
        const busy = generating !== null && FORMAT_META[generating].menu === menu.key;

        return (
          <DropdownMenu key={menu.key}>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="default"
                disabled={generating !== null || disabled}
                className={className}
                title={`Download ${menu.label} report (${dateFrom} to ${dateTo})`}
              >
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating…
                  </>
                ) : (
                  <>
                    {/* The tax icon rather than a generic download glyph:
                        the two buttons sit side by side in the filter bar,
                        so telling them apart matters more than repeating
                        what the chevron and the menu items already say. */}
                    <MenuIcon className="h-4 w-4" />
                    {menu.label}
                    <ChevronDown className="h-4 w-4 opacity-60" />
                  </>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="rounded-xl border-blue-600 dark:border-neutral-800"
            >
              {menu.formats.map(({ format, label, icon: ItemIcon }) => (
                <DropdownMenuItem
                  key={format}
                  className="text-xs cursor-pointer gap-2"
                  onSelect={() => handleDownload(format)}
                >
                  <ItemIcon className="h-4 w-4" />
                  {label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      })}
    </>
  );
}
