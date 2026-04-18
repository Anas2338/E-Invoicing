import { Badge } from '@/components/ui/badge';

interface Invoice {
  id: string;
  number: string;
  date: string;
  amount: number;
  status: 'draft' | 'validated' | 'posted' | 'failed';
}

interface RecentInvoicesProps {
  invoices: Invoice[];
}

export function RecentInvoices({ invoices }: RecentInvoicesProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-[#fef3c7] text-[#92400e] dark:bg-[#451a03]/30 dark:text-[#fbbf24]';
      case 'validated': return 'bg-[#dbeafe] text-[#1e40af] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa]';
      case 'posted': return 'bg-[#d1fae5] text-[#065f46] dark:bg-[#064e3b]/30 dark:text-[#34d399]';
      case 'failed': return 'bg-[#fee2e2] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:text-[#f87171]';
      default: return 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]';
    }
  };

  return (
    <div className="overflow-hidden bg-white dark:bg-[#1a1a1a] border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm rounded-2xl">
      <ul className="divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
        {invoices.map((invoice) => (
          <li key={invoice.id}>
            <div className="block hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors duration-150">
              <div className="flex items-center px-4 py-4 sm:px-6">
                <div className="min-w-0 flex-1 flex items-center">
                  <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] truncate">
                    {invoice.number}
                  </div>
                  <div className="ml-2 flex-shrink-0 flex">
                    <Badge className={`${getStatusColor(invoice.status)} capitalize`}>
                      {invoice.status}
                    </Badge>
                  </div>
                </div>
                <div className="hidden md:block">
                  <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                    {new Date(invoice.date).toLocaleDateString('en-US', { timeZone: 'Asia/Karachi' })}
                  </div>
                </div>
                <div className="hidden md:block">
                  <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                    PKR {invoice.amount.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}