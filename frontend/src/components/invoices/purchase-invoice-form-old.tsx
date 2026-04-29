'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { validatedInvoiceSchema, type InvoiceFormData } from '@/lib/validation/invoice-schema';

interface PurchaseInvoiceFormProps {
  onSubmit: (data: InvoiceFormData) => void;
  onCancel: () => void;
  isLoading: boolean;
}

export function PurchaseInvoiceForm({ onSubmit, onCancel, isLoading }: PurchaseInvoiceFormProps) {
  const [lineItems, setLineItems] = useState([
    { id: '1', description: '', quantity: 1, unitPrice: 0, taxRate: 0 }
  ]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch
  } = useForm<InvoiceFormData>({
    resolver: zodResolver(validatedInvoiceSchema) as any,
    defaultValues: {
      type: 'purchase',
      environment: 'sandbox',
      saveAsDraft: true,
      invoiceNumber: '',
      date: '',
      dueDate: '',
      lineItems: [{ id: '1', description: '', quantity: 1, unitPrice: 0, taxRate: 0 }],
      supplierInfo: {
        name: '',
        taxId: '',
        address: {
          street: '',
          city: '',
          state: '',
          zipCode: '',
          country: ''
        },
        contact: {}
      }
    }
  });

  const watchedType = watch('type');

  const addLineItem = () => {
    const newItem = {
      id: Date.now().toString(),
      description: '',
      quantity: 1,
      unitPrice: 0,
      taxRate: 0
    };
    setLineItems([...lineItems, newItem]);
  };

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index));
    }
  };

  const updateLineItem = (index: number, field: keyof typeof lineItems[0], value: any) => {
    const updatedItems = [...lineItems];
    updatedItems[index] = { ...updatedItems[index], [field]: value };
    setLineItems(updatedItems);
  };

  const handleFormSubmit = (formData: InvoiceFormData) => {
    // Add the line items to the form data
    const invoiceData = {
      ...formData,
      lineItems
    };
    onSubmit(invoiceData);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Create Purchase Invoice</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="invoiceNumber">Invoice Number *</Label>
              <Input
                id="invoiceNumber"
                {...register('invoiceNumber')}
                placeholder="INV-001"
              />
              {errors.invoiceNumber && (
                <p className="text-red-500 text-sm mt-1">{errors.invoiceNumber.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="environment">Environment *</Label>
              <Select value={watch('environment')} onValueChange={(val) => setValue('environment', val as 'sandbox' | 'production')}>
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sandbox">Sandbox</SelectItem>
                  <SelectItem value="production">Production</SelectItem>
                </SelectContent>
              </Select>
              {errors.environment && (
                <p className="text-red-500 text-sm mt-1">{errors.environment.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="date">Date *</Label>
              <Input
                id="date"
                type="date"
                {...register('date')}
              />
              {errors.date && (
                <p className="text-red-500 text-sm mt-1">{errors.date.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="dueDate">Due Date *</Label>
              <Input
                id="dueDate"
                type="date"
                {...register('dueDate')}
              />
              {errors.dueDate && (
                <p className="text-red-500 text-sm mt-1">{errors.dueDate.message}</p>
              )}
            </div>
          </div>

          {/* Supplier Info */}
          <div className="border-t pt-4">
            <h3 className="text-lg font-medium mb-4">Supplier Information *</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="supplierName">Supplier Name *</Label>
                <Input
                  id="supplierName"
                  {...register('supplierInfo.name')}
                  placeholder="Supplier name"
                />
                {errors.supplierInfo?.name && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.name.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="supplierTaxId">Tax ID *</Label>
                <Input
                  id="supplierTaxId"
                  {...register('supplierInfo.taxId')}
                  placeholder="Tax identification number"
                />
                {errors.supplierInfo?.taxId && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.taxId.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="supplierAddress">Address *</Label>
                <Input
                  id="supplierAddress"
                  {...register('supplierInfo.address.street')}
                  placeholder="Street address"
                />
                {errors.supplierInfo?.address?.street && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.address.street.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="supplierCity">City *</Label>
                <Input
                  id="supplierCity"
                  {...register('supplierInfo.address.city')}
                  placeholder="City"
                />
                {errors.supplierInfo?.address?.city && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.address.city.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="supplierState">State *</Label>
                <Input
                  id="supplierState"
                  {...register('supplierInfo.address.state')}
                  placeholder="State"
                />
                {errors.supplierInfo?.address?.state && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.address.state.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="supplierZip">ZIP Code *</Label>
                <Input
                  id="supplierZip"
                  {...register('supplierInfo.address.zipCode')}
                  placeholder="ZIP code"
                />
                {errors.supplierInfo?.address?.zipCode && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.address.zipCode.message}</p>
                )}
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="supplierCountry">Country *</Label>
                <Input
                  id="supplierCountry"
                  {...register('supplierInfo.address.country')}
                  placeholder="Country"
                />
                {errors.supplierInfo?.address?.country && (
                  <p className="text-red-500 text-sm mt-1">{errors.supplierInfo.address.country.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div className="border-t pt-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Line Items</h3>
              <Button type="button" variant="outline" onClick={addLineItem}>Add Item</Button>
            </div>

            {lineItems.map((item, index) => (
              <div key={item.id} className="grid grid-cols-12 gap-2 mb-4 p-4 border rounded-md">
                <div className="col-span-5">
                  <Label>Description</Label>
                  <Input
                    value={item.description}
                    onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                    placeholder="Item description"
                  />
                </div>

                <div className="col-span-2">
                  <Label>Quantity</Label>
                  <Input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => updateLineItem(index, 'quantity', Number(e.target.value))}
                  />
                </div>

                <div className="col-span-2">
                  <Label>Unit Price</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={item.unitPrice}
                    onChange={(e) => updateLineItem(index, 'unitPrice', Number(e.target.value))}
                  />
                </div>

                <div className="col-span-2">
                  <Label>Tax Rate (%)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={item.taxRate}
                    onChange={(e) => updateLineItem(index, 'taxRate', Number(e.target.value) / 100)}
                  />
                </div>

                <div className="col-span-1 flex items-end">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => removeLineItem(index)}
                    className="w-full"
                    disabled={lineItems.length <= 1}
                  >
                    -
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between pt-4">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>

            <div className="space-x-2">
              <Button
                type="submit"
                variant="outline"
                onClick={() => setValue('saveAsDraft', true)}
              >
                Save as Draft
              </Button>

              <Button
                type="submit"
                onClick={() => setValue('saveAsDraft', false)}
                disabled={isLoading}
              >
                {isLoading ? 'Submitting...' : 'Submit for Validation'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}