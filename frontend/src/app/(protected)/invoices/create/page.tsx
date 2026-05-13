'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SaleInvoiceForm } from '@/components/invoices/sale-invoice-form';
import ManualExcelUploadForm from '@/components/invoices/ManualExcelUploadForm';
import { invoiceService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { ArrowLeft, ShoppingCart, FileSpreadsheet } from 'lucide-react';

export default function CreateInvoicePage() {
  const [invoiceType, setInvoiceType] = useState<'sale' | 'purchase' | 'excel' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const handleSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      const response = await invoiceService.createInvoice(data);
      if (response.success) {
        // Show success notification
        toast.success('Invoice created successfully!');

        // Always redirect to invoice history
        router.push('/invoices/history');
      }
    } catch (error) {
      console.error('Error creating invoice:', error);
      toast.error('Failed to create invoice. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    router.back();
  };

  return (
    <div className="space-y-6 pb-8">
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/invoices/history')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Invoice History
        </Button>
      </div>

      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Create Invoice</h1>
        <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Create a new sale or purchase invoice</p>
      </div>

      {!invoiceType ? (
        <Card>
          <CardHeader>
            <CardTitle>Select Invoice Creation Method</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Button
                variant="outline"
                size="lg"
                className="h-32 flex flex-col items-center justify-center hover:border-[#008060] dark:hover:border-[#00a876] hover:bg-[#f1f8f5] dark:hover:bg-[#0d3d2f]/20"
                onClick={() => setInvoiceType('sale')}
              >
                <span className="text-2xl mb-2">🏢</span>
                <span className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Sale Invoice</span>
                <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">Create invoice for sales</span>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-32 flex flex-col items-center justify-center hover:border-[#008060] dark:hover:border-[#00a876] hover:bg-[#f1f8f5] dark:hover:bg-[#0d3d2f]/20"
                onClick={() => setInvoiceType('purchase')}
              >
                <span className="text-2xl mb-2">🛒</span>
                <span className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Purchase Invoice</span>
                <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">Create invoice for purchases</span>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-32 flex flex-col items-center justify-center hover:border-[#008060] dark:hover:border-[#00a876] hover:bg-[#f1f8f5] dark:hover:bg-[#0d3d2f]/20"
                onClick={() => setInvoiceType('excel')}
              >
                <FileSpreadsheet className="h-8 w-8 mb-2 text-[#008060] dark:text-[#00a876]" />
                <span className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Upload via Excel</span>
                <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">Bulk create invoices from file</span>
              </Button>
            </div>
            <div className="mt-6 flex justify-end">
              <Button variant="outline" onClick={handleCancel}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {invoiceType === 'sale' ? (
            <SaleInvoiceForm
              onSubmit={handleSubmit}
              onCancel={() => setInvoiceType(null)}
              isLoading={isSubmitting}
            />
          ) : invoiceType === 'excel' ? (
            <div>
              <div className="mb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setInvoiceType(null)}
                  className="flex items-center gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to Selection
                </Button>
              </div>
              <ManualExcelUploadForm />
            </div>
          ) : (
            <Card className="border-2 border-dashed border-[#d2d5d8] dark:border-[#3a3e41]">
              <CardContent className="flex flex-col items-center justify-center py-20 space-y-4">
                <div className="h-20 w-20 rounded-full bg-[#f6f6f7] dark:bg-[#2a2e31] flex items-center justify-center">
                  <ShoppingCart className="h-10 w-10 text-[#8c9196]" />
                </div>
                <h2 className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3]">Coming Soon</h2>
                <p className="text-[#6d7175] dark:text-[#8c9196] text-center max-w-md">
                  The Purchase Invoice feature is currently under development and will be available soon. You can create Sale Invoices in the meantime.
                </p>
                <Button
                  variant="outline"
                  onClick={() => setInvoiceType(null)}
                  className="mt-4"
                >
                  Go Back
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}