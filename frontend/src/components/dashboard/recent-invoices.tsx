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
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      case 'validated': return 'bg-blue-100 text-blue-800';
      case 'posted': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="overflow-hidden bg-white shadow sm:rounded-md">
      <ul className="divide-y divide-gray-200">
        {invoices.map((invoice) => (
          <li key={invoice.id}>
            <div className="block hover:bg-gray-50">
              <div className="flex items-center px-4 py-4 sm:px-6">
                <div className="min-w-0 flex-1 flex items-center">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {invoice.number}
                  </div>
                  <div className="ml-2 flex-shrink-0 flex">
                    <Badge className={`${getStatusColor(invoice.status)} capitalize`}>
                      {invoice.status}
                    </Badge>
                  </div>
                </div>
                <div className="hidden md:block">
                  <div className="text-sm text-gray-900">
                    {new Date(invoice.date).toLocaleDateString()}
                  </div>
                </div>
                <div className="hidden md:block">
                  <div className="text-sm text-gray-500">
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