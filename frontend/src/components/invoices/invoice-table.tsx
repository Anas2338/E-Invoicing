import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Eye, Edit, CheckCircle, Send, Trash2 } from 'lucide-react';

interface Invoice {
  id: string;
  invoiceNumber: string;
  date: string;
  buyerName: string;
  sellerName: string;
  totalAmount: number;
  status: 'DRAFT' | 'VALIDATED' | 'POSTED' | 'FAILED';
  environment: 'SANDBOX' | 'PRODUCTION';
  invoiceType: string;
  createdAt: string;
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
}

export function InvoiceTable({
  invoices,
  selectedInvoices = new Set(),
  onSelectionChange,
  onView,
  onEdit,
  onValidate,
  onPost,
  onDelete
}: InvoiceTableProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'VALIDATED': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'POSTED': return 'bg-green-100 text-green-800 border-green-200';
      case 'FAILED': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getEnvironmentColor = (env: string) => {
    return env === 'PRODUCTION'
      ? 'bg-red-100 text-red-800 border-red-200'
      : 'bg-blue-100 text-blue-800 border-blue-200';
  };

  const formatStatus = (status: string) => {
    return status.charAt(0) + status.slice(1).toLowerCase();
  };

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;

    if (checked) {
      // Select all deletable invoices (DRAFT or FAILED)
      const deletableIds = new Set(
        invoices
          .filter(inv => inv.status === 'DRAFT' || inv.status === 'FAILED')
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

  const deletableInvoices = invoices.filter(inv => inv.status === 'DRAFT' || inv.status === 'FAILED');
  const allDeletableSelected = deletableInvoices.length > 0 &&
    deletableInvoices.every(inv => selectedInvoices.has(inv.id));
  const someDeletableSelected = deletableInvoices.some(inv => selectedInvoices.has(inv.id));

  if (invoices.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
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
        <h3 className="mt-2 text-sm font-medium text-gray-900">No invoices found</h3>
        <p className="mt-1 text-sm text-gray-500">
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
          const isDeletable = invoice.status === 'DRAFT' || invoice.status === 'FAILED';
          const isSelected = selectedInvoices.has(invoice.id);

          return (
            <div
              key={invoice.id}
              className={`bg-white rounded-lg border-2 p-4 ${
                isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
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
                    <div className="text-sm font-semibold text-gray-900">{invoice.invoiceNumber}</div>
                    <div className="text-xs text-gray-500">{invoice.invoiceType}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Badge className={`${getStatusColor(invoice.status)} border text-xs`}>
                    {formatStatus(invoice.status)}
                  </Badge>
                </div>
              </div>

              {/* Invoice Details */}
              <div className="space-y-2 mb-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Date:</span>
                  <span className="text-gray-900 font-medium">
                    {new Date(invoice.date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Buyer:</span>
                  <span className="text-gray-900 truncate ml-2">{invoice.buyerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Seller:</span>
                  <span className="text-gray-900 truncate ml-2">{invoice.sellerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Amount:</span>
                  <span className="text-gray-900 font-semibold">
                    PKR {invoice.totalAmount.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">Environment:</span>
                  <Badge className={`${getEnvironmentColor(invoice.environment)} border text-xs`}>
                    {invoice.environment}
                  </Badge>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-200">
                {onView && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onView(invoice.id)}
                    className="flex-1 min-w-[80px] h-9 border-blue-300 text-blue-600 hover:bg-blue-50"
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
                    className="flex-1 min-w-[80px] h-9 border-gray-300 text-gray-600 hover:bg-gray-50"
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
                    className="flex-1 min-w-[80px] h-9 border-blue-300 text-blue-600 hover:bg-blue-50"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Validate
                  </Button>
                )}
                {onPost && invoice.status === 'VALIDATED' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onPost(invoice.id)}
                    className="flex-1 min-w-[80px] h-9 border-green-300 text-green-600 hover:bg-green-50"
                  >
                    <Send className="h-4 w-4 mr-1" />
                    Post
                  </Button>
                )}
                {onDelete && isDeletable && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDelete(invoice.id)}
                    className="flex-1 min-w-[80px] h-9 border-red-300 text-red-600 hover:bg-red-50"
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
        <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
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
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Invoice #
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Buyer
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Seller
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Amount
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Environment
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {invoices.map((invoice) => {
            const isDeletable = invoice.status === 'DRAFT' || invoice.status === 'FAILED';
            const isSelected = selectedInvoices.has(invoice.id);

            return (
            <tr key={invoice.id} className={`hover:bg-gray-50 transition-colors ${isSelected ? 'bg-blue-50' : ''}`}>
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
                <div className="text-sm font-medium text-gray-900">{invoice.invoiceNumber}</div>
                <div className="text-xs text-gray-500">{invoice.invoiceType}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {new Date(invoice.date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                })}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">{invoice.buyerName}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">{invoice.sellerName}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  PKR {invoice.totalAmount.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge className={`${getStatusColor(invoice.status)} border`}>
                  {formatStatus(invoice.status)}
                </Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge className={`${getEnvironmentColor(invoice.environment)} border`}>
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
                      className="h-8 px-3 border-blue-300 text-blue-600 hover:bg-blue-50 hover:border-blue-400"
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
                      className="h-8 px-3 border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400"
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
                      className="h-8 px-3 border-blue-300 text-blue-600 hover:bg-blue-50 hover:border-blue-400"
                      title="Validate with FBR"
                    >
                      <CheckCircle className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Post Button - Only for VALIDATED */}
                  {onPost && invoice.status === 'VALIDATED' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPost(invoice.id)}
                      className="h-8 px-3 border-green-300 text-green-600 hover:bg-green-50 hover:border-green-400"
                      title="Post to FBR"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Delete Button - Only for DRAFT or FAILED */}
                  {onDelete && isDeletable && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onDelete(invoice.id)}
                      className="h-8 px-3 border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400"
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