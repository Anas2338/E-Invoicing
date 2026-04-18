import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Eye, Edit, CheckCircle, Send, Trash2, Loader2 } from 'lucide-react';
import { PrintInvoiceButton } from '@/components/automation/PrintInvoiceButton';

interface Invoice {
  id: string;
  source: 'manual' | 'automated';
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: string;
  environment: string;
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
}

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
  postingInvoiceId = null
}: InvoiceTableProps) {
  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'DRAFT':
      case 'PENDING':
        return 'bg-[#fef3c7] text-[#92400e] border-[#fde68a] dark:bg-[#451a03]/30 dark:text-[#fbbf24] dark:border-[#451a03]';
      case 'VALIDATED':
        return 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa] dark:border-[#1e3a8a]';
      case 'POSTED':
      case 'SUBMITTED':
        return 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]';
      case 'FAILED':
        return 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]';
      case 'EXPIRED':
        return 'bg-[#f3f4f6] text-[#4b5563] border-[#d1d5db] dark:bg-[#374151]/30 dark:text-[#9ca3af] dark:border-[#4b5563]';
      default:
        return 'bg-[#f6f6f7] text-[#6d7175] border-[#e1e3e5] dark:bg-[#2e2e2e] dark:text-[#8c9196] dark:border-[#404040]';
    }
  };

  const getSourceColor = (source: string) => {
    return source === 'manual'
      ? 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa] dark:border-[#1e3a8a]'
      : 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] dark:bg-[#064e3b]/30 dark:text-[#34d399] dark:border-[#065f46]';
  };

  const getEnvironmentColor = (env: string) => {
    return env === 'PRODUCTION'
      ? 'bg-[#fee2e2] text-[#991b1b] border-[#fecaca] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] dark:border-[#7f1d1d]'
      : 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa] dark:border-[#1e3a8a]';
  };

  const formatStatus = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  };

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;

    if (checked) {
      // Select all deletable invoices (DRAFT, VALIDATED, or FAILED)
      const deletableIds = new Set(
        invoices
          .filter(inv => inv.status === 'DRAFT' || inv.status === 'VALIDATED' || inv.status === 'FAILED')
          .map(inv => inv.id)
      );
      onSelectionChange(deletableIds);
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

  const deletableInvoices = invoices.filter(inv => inv.status === 'DRAFT' || inv.status === 'VALIDATED' || inv.status === 'FAILED');
  const allDeletableSelected = deletableInvoices.length > 0 &&
    deletableInvoices.every(inv => selectedInvoices.has(inv.id));
  const someDeletableSelected = deletableInvoices.some(inv => selectedInvoices.has(inv.id));

  if (invoices.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-[#8c9196] dark:text-[#6d7175]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">No invoices found</h3>
        <p className="mt-1 text-sm text-[#6d7175] dark:text-[#8c9196]">
          Try adjusting your filters or create a new invoice.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Mobile Card View */}
      <div className="block lg:hidden space-y-4">
        {invoices.map((invoice) => {
          const isDeletable = invoice.status === 'DRAFT' || invoice.status === 'VALIDATED' || invoice.status === 'FAILED';
          const isSelected = selectedInvoices.has(invoice.id);

          return (
            <div
              key={invoice.id}
              className={`bg-white dark:bg-[#1a1a1a] rounded-xl border-2 p-4 transition-all duration-150 ${
                isSelected ? 'border-[#008060] bg-[#f1f8f5] dark:border-[#00a876] dark:bg-[#0d3d2f]/20' : 'border-[#e1e3e5] dark:border-[#2e2e2e]'
              }`}
            >
              {/* Header with checkbox and invoice number */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3 flex-1">
                  {onSelectionChange && (
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                      disabled={!isDeletable}
                      aria-label={`Select invoice ${invoice.invoiceNumber}`}
                      className="mt-1"
                    />
                  )}
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">{invoice.invoiceNumber}</div>
                    <div className="text-xs text-[#6d7175] dark:text-[#8c9196]">{invoice.invoiceType}</div>
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap justify-end">
                  <Badge className={`${getSourceColor(invoice.source)} border text-xs font-semibold`}>
                    {invoice.source === 'manual' ? 'Manual' : 'Automated'}
                  </Badge>
                  <Badge className={`${getStatusColor(invoice.status)} border text-xs font-semibold`}>
                    {formatStatus(invoice.status)}
                  </Badge>
                </div>
              </div>

              {/* Invoice Details */}
              <div className="space-y-2 mb-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Date:</span>
                  <span className="text-[#202223] dark:text-[#e3e3e3] font-medium">
                    {new Date(invoice.date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      timeZone: 'Asia/Karachi'
                    })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Buyer:</span>
                  <span className="text-[#202223] dark:text-[#e3e3e3] truncate ml-2">{invoice.buyerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Seller:</span>
                  <span className="text-[#202223] dark:text-[#e3e3e3] truncate ml-2">{invoice.sellerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Amount:</span>
                  <span className="text-[#202223] dark:text-[#e3e3e3] font-semibold">
                    PKR {invoice.totalAmount.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#6d7175] dark:text-[#8c9196]">Environment:</span>
                  <Badge className={`${getEnvironmentColor(invoice.environment)} border text-xs font-semibold`}>
                    {invoice.environment}
                  </Badge>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-3 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
                {onView && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onView(invoice.id)}
                    className="flex-1 min-w-[80px] h-9"
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    View
                  </Button>
                )}
                {onEdit && invoice.status === 'DRAFT' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEdit(invoice.id)}
                    className="flex-1 min-w-[80px] h-9"
                  >
                    <Edit className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                )}
                {onValidate && invoice.status === 'DRAFT' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onValidate(invoice.id)}
                    disabled={validatingInvoiceId === invoice.id}
                    className="flex-1 min-w-[80px] h-9"
                  >
                    {validatingInvoiceId === invoice.id ? (
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    ) : (
                      <CheckCircle className="h-4 w-4 mr-1" />
                    )}
                    {validatingInvoiceId === invoice.id ? 'Validating...' : 'Validate'}
                  </Button>
                )}
                {onPost && invoice.status === 'VALIDATED' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onPost(invoice.id)}
                    disabled={postingInvoiceId === invoice.id}
                    className="flex-1 min-w-[80px] h-9"
                  >
                    {postingInvoiceId === invoice.id ? (
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4 mr-1" />
                    )}
                    {postingInvoiceId === invoice.id ? 'Posting...' : 'Post'}
                  </Button>
                )}
                {(invoice.status === 'POSTED' || invoice.status === 'submitted') && (
                  <div className="flex-1 min-w-[80px]">
                    <PrintInvoiceButton
                      invoiceId={invoice.id}
                      invoiceNumber={invoice.invoiceNumber}
                      status={invoice.status}
                      className="w-full h-9"
                    />
                  </div>
                )}
                {onDelete && isDeletable && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDelete(invoice.id)}
                    className="flex-1 min-w-[80px] h-9"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop Table View */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="min-w-full divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
        <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e]">
          <tr>
            {onSelectionChange && (
              <th scope="col" className="px-6 py-3 text-left">
                <Checkbox
                  checked={allDeletableSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="Select all deletable invoices"
                  className={someDeletableSelected && !allDeletableSelected ? 'data-[state=checked]:bg-gray-400' : ''}
                />
              </th>
            )}
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Invoice #
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Source
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Date
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Buyer
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Seller
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Amount
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Environment
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-[#1a1a1a] divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
          {invoices.map((invoice) => {
            const isDeletable = invoice.status === 'DRAFT' || invoice.status === 'VALIDATED' || invoice.status === 'FAILED';
            const isSelected = selectedInvoices.has(invoice.id);

            return (
            <tr key={invoice.id} className={`hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors duration-150 ${isSelected ? 'bg-[#f1f8f5] dark:bg-[#0d3d2f]/20' : ''}`}>
              {onSelectionChange && (
                <td className="px-6 py-4 whitespace-nowrap">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={(checked) => handleSelectInvoice(invoice.id, checked as boolean)}
                    disabled={!isDeletable}
                    aria-label={`Select invoice ${invoice.invoiceNumber}`}
                  />
                </td>
              )}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">{invoice.invoiceNumber}</div>
                <div className="text-xs text-[#6d7175] dark:text-[#8c9196]">{invoice.invoiceType}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge className={`${getSourceColor(invoice.source)} border text-xs font-semibold`}>
                  {invoice.source === 'manual' ? 'Manual' : 'Automated'}
                </Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-[#6d7175] dark:text-[#8c9196]">
                {new Date(invoice.date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                })}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">{invoice.buyerName}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">{invoice.sellerName}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                  PKR {invoice.totalAmount.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge className={`${getStatusColor(invoice.status)} border font-semibold`}>
                  {formatStatus(invoice.status)}
                </Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge className={`${getEnvironmentColor(invoice.environment)} border font-semibold`}>
                  {invoice.environment}
                </Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <div className="flex items-center gap-2">
                  {/* View Button - Always visible */}
                  {onView && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onView(invoice.id)}
                      className="h-8 px-3"
                      title="View Details"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Edit Button - Only for DRAFT */}
                  {onEdit && invoice.status === 'DRAFT' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onEdit(invoice.id)}
                      className="h-8 px-3"
                      title="Edit Invoice"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Validate Button - Only for DRAFT */}
                  {onValidate && invoice.status === 'DRAFT' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onValidate(invoice.id)}
                      disabled={validatingInvoiceId === invoice.id}
                      className="h-8 px-3"
                      title="Validate with FBR"
                    >
                      {validatingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4" />
                      )}
                    </Button>
                  )}

                  {/* Post Button - Only for VALIDATED */}
                  {onPost && invoice.status === 'VALIDATED' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPost(invoice.id)}
                      disabled={postingInvoiceId === invoice.id}
                      className="h-8 px-3"
                      title="Post to FBR"
                    >
                      {postingInvoiceId === invoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  )}

                  {/* Print Button - Only for POSTED or submitted */}
                  {(invoice.status === 'POSTED' || invoice.status === 'submitted') && (
                    <PrintInvoiceButton
                      invoiceId={invoice.id}
                      invoiceNumber={invoice.invoiceNumber}
                      status={invoice.status}
                    />
                  )}

                  {/* Delete Button - Only for DRAFT or FAILED */}
                  {onDelete && isDeletable && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onDelete(invoice.id)}
                      className="h-8 px-3"
                      title="Delete Invoice"
                    >
                      <Trash2 className="h-4 w-4" />
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
    </>
  );
}