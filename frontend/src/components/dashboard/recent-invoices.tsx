import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Calendar, User, Hash } from 'lucide-react';
import { PrintInvoiceButton } from '@/components/invoices/PrintInvoiceButton';

interface Invoice {
  id: string;
  number: string;
  date: string;
  fbrInvoiceNumber?: string;
  amount: number;
  status: 'draft' | 'validated' | 'posted' | 'failed';
  buyerName?: string;
}

interface RecentInvoicesProps {
  invoices: Invoice[];
  onView?: (id: string) => void;
}

export function RecentInvoices({
  invoices,
  onView,
}: RecentInvoicesProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'px-2.5 py-0.5 text-xs font-black tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-blue-400 via-blue-500 to-blue-600 border border-blue-400/40 shadow-[0_5px_12px_-3px_rgba(59,130,246,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
      case 'validated': return 'px-2.5 py-0.5 text-xs font-black tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-sky-400 via-sky-500 to-sky-600 border border-sky-400/40 shadow-[0_5px_12px_-3px_rgba(14,165,233,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
      case 'posted': return 'px-2.5 py-0.5 text-xs font-black tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-emerald-400 via-emerald-500 to-emerald-600 border border-emerald-400/40 shadow-[0_5px_12px_-3px_rgba(16,185,129,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
      case 'failed': return 'px-2.5 py-0.5 text-xs font-black tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-rose-400 via-rose-500 to-rose-600 border border-rose-400/40 shadow-[0_5px_12px_-3px_rgba(244,63,94,0.4),inset_0_4px_6px_rgba(255,255,255,0.4),inset_0_-3px_6px_rgba(0,0,0,0.1)]';
      default: return 'px-2.5 py-0.5 text-xs font-black tracking-widest uppercase rounded-full text-white bg-gradient-to-b from-gray-400 to-gray-500';
    }
  };

  return (
    <div className="flex flex-col gap-2">

      {/* ===== MOBILE / TABLET CARD VIEW (< lg) ===== */}
      <div className="lg:hidden flex flex-col gap-2">
        {invoices.map((invoice) => (
          <div
            key={invoice.id}
            className="bg-[#cfd4e7] dark:bg-neutral-900 rounded-2xl p-3 sm:p-4 shadow-sm border border-slate-200/60 dark:border-neutral-800 space-y-2.5"
          >
            {/* Top row: Invoice number + Status */}
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm sm:text-base font-bold text-slate-800 dark:text-neutral-200 tracking-tight">
                  {invoice.number}
                </div>
                {invoice.fbrInvoiceNumber && (
                  <div className="text-xs font-medium text-slate-500 dark:text-neutral-400 mt-0.5">
                    FBR: {invoice.fbrInvoiceNumber}
                  </div>
                )}
              </div>
              <Badge className={`${getStatusColor(invoice.status)}`}>
                {invoice.status}
              </Badge>
            </div>

            {/* Details row */}
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs sm:text-sm">
              <div className="flex items-center gap-1.5 text-slate-500 dark:text-neutral-400">
                <Calendar className="h-3 w-3 sm:h-3.5 sm:w-3.5 flex-shrink-0" />
                <span className="font-medium text-slate-700 dark:text-neutral-300">
                  {new Date(invoice.date).toLocaleDateString('en-US', { timeZone: 'Asia/Karachi' })}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-500 dark:text-neutral-400">
                <User className="h-3 w-3 sm:h-3.5 sm:w-3.5 flex-shrink-0" />
                <span className="font-medium text-slate-700 dark:text-neutral-300 truncate">
                  {invoice.buyerName || 'N/A'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-500 dark:text-neutral-400">
                <Hash className="h-3 w-3 sm:h-3.5 sm:w-3.5 flex-shrink-0" />
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {invoice.amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Action row */}
            {onView && (
              <div className="flex justify-end pt-1 border-t border-slate-200/60 dark:border-neutral-700/50">
                {invoice.status === 'posted' ? (
                  <PrintInvoiceButton
                    invoiceId={invoice.id}
                    invoiceNumber={invoice.number}
                    status={invoice.status}
                    variant="outline"
                    size="sm"
                    className="h-8 rounded-xl text-xs font-semibold gap-1.5"
                  />
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onView(invoice.id)}
                    className="h-8 rounded-xl text-xs font-semibold gap-1.5"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    View
                  </Button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ===== DESKTOP TABLE VIEW (≥ lg) ===== */}
<div className="hidden lg:flex lg:flex-col gap-2">
  <div className='rounded-4xl bg-[#7c97f0]'>
    <table className='w-full table-fixed'>
      <thead>
        <tr>
          <th className="border-r-2 border-[#FFFFFF] pl-2 py-0.5 text-centre text-xs font-bold text-black uppercase w-[125px]">Invoice No.</th>
          <th className="border-r-2 border-[#FFFFFF] py-0.5 text-center text-xs font-bold text-black uppercase tracking-wider w-[185px]">FBR Ref Number</th>
          <th className="border-r-2 border-[#FFFFFF] px-2 py-2 text-center text-xs font-bold text-black uppercase tracking-wider w-[95px]">Date</th>
          <th className="border-r-2 border-[#FFFFFF] px-2 py-2 text-center text-xs font-bold text-black uppercase tracking-wider w-[340px]">Buyer Name</th>
          <th className="border-r-2 border-[#FFFFFF] px-2 py-2 text-center text-xs font-bold text-black uppercase tracking-wider w-[115px]">Amount</th>
          <th className="border-r-2 border-[#FFFFFF] py-2 text-center text-xs font-bold text-black uppercase tracking-wider w-[100px]">Status</th>
          <th className="px-2 py-2 text-center text-xs font-bold text-black uppercase tracking-wider w-[180px]">Actions</th>
        </tr>
      </thead>
    </table>
  </div>

  <div className='rounded-4xl bg-[#e7eaf1] border-2  border-blue-200'>
    <table className="w-full table-fixed">
      <tbody className="divide-y divide-[#FFFFFF]">
        {invoices.map((invoice) => (
          <tr key={invoice.id} className="hover:bg-slate-50/60 transition-colors duration-150">
            <td className="border-r-2 border-[#FFFFFF] pl-2 py-0.5 w-[125px]">
              <div className="text-sm font-medium text-slate-700 truncate">{invoice.number}</div>
            </td>
            <td className="border-r-2 border-[#FFFFFF] px-1 py-0.5 w-[185px]">
              <div className="text-sm font-medium text-slate-700 truncate">{invoice.fbrInvoiceNumber || '—'}</div>
            </td>
            <td className="border-r-2 border-[#FFFFFF] px-2 py-0.5 w-[95px]">
              <div className="text-sm font-medium text-slate-700">
                {new Date(invoice.date).toLocaleDateString('en-GB', { timeZone: 'Asia/Karachi' })}
              </div>
            </td>
            <td className="border-r-2 border-[#FFFFFF] px-2 py-0.5 w-[340px]">
              <div className="text-sm font-medium text-slate-700">{invoice.buyerName || 'N/A'}</div>
            </td>
            <td className="border-r-2 border-[#FFFFFF] px-2 py-0.5 w-[115px]">
              <div className="text-sm font-medium text-slate-700 text-right">
                {invoice.amount.toLocaleString(
                  'en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                })}
              </div>
            </td>
            <td className="border-r-2 border-[#FFFFFF] px-2 py-0.5 text-center w-[100px]">
              <Badge className={`${getStatusColor(invoice.status)}`}>
                {invoice.status === 'validated' ? 'valid' : invoice.status}
              </Badge>
            </td>
            {/* REMOVED 'flex gap-2' from this td tag to fix alignment */}
            <td className="px-2 py-0.5 w-[180px]">
              <div className="flex items-center justify-center gap-2">
                {onView && (
                  invoice.status === 'posted' ? (
                    <PrintInvoiceButton
                      invoiceId={invoice.id}
                      invoiceNumber={invoice.number}
                      status={invoice.status}
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                    />
                  ) : (
                    <Button variant="outline" size="icon" onClick={() => onView(invoice.id)} className="h-8 w-8" title="View">
                      <Eye className="h-4 w-4" />
                    </Button>
                  )
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</div>
      </div>

  );
}
