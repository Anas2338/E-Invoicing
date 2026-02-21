'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SaleInvoiceForm } from '@/components/invoices/sale-invoice-form';
import { PurchaseInvoiceForm } from '@/components/invoices/purchase-invoice-form';
import { invoiceService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';

export default function CreateInvoicePage() {
  const [invoiceType, setInvoiceType] = useState<'sale' | 'purchase' | null>(null);
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Create Invoice</h1>
        <p className="mt-2 text-sm sm:text-base text-gray-600">Create a new sale or purchase invoice</p>
      </div>

      {!invoiceType ? (
        <Card>
          <CardHeader>
            <CardTitle>Select Invoice Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Button
                variant="outline"
                size="lg"
                className="h-32 flex flex-col items-center justify-center"
                onClick={() => setInvoiceType('sale')}
              >
                <span className="text-2xl mb-2">🏢</span>
                <span className="text-lg font-medium">Sale Invoice</span>
                <span className="text-sm text-gray-500">Create invoice for sales</span>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-32 flex flex-col items-center justify-center"
                onClick={() => setInvoiceType('purchase')}
              >
                <span className="text-2xl mb-2">🛒</span>
                <span className="text-lg font-medium">Purchase Invoice</span>
                <span className="text-sm text-gray-500">Create invoice for purchases</span>
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
          ) : (
            <PurchaseInvoiceForm
              onSubmit={handleSubmit}
              onCancel={() => setInvoiceType(null)}
              isLoading={isSubmitting}
            />
          )}
        </>
      )}
    </div>
  );
}