'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { Hash, Loader2 } from 'lucide-react';

export default function InvoiceSettingsSection() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Invoice settings state
  const [invoicePrefix, setInvoicePrefix] = useState('INV-');
  const [invoiceStartNumber, setInvoiceStartNumber] = useState(1);
  const [invoicePadding, setInvoicePadding] = useState(4);
  const [invoiceIncludeYear, setInvoiceIncludeYear] = useState(false);

  // Preview state
  const [previewNumber, setPreviewNumber] = useState('');

  useEffect(() => {
    fetchInvoiceSettings();
  }, []);

  useEffect(() => {
    updatePreview();
  }, [invoicePrefix, invoiceStartNumber, invoicePadding, invoiceIncludeYear]);

  const fetchInvoiceSettings = async () => {
    try {
      setLoading(true);
      const profile = await api.auth.getProfile();

      setInvoicePrefix(profile.invoice_prefix || 'INV-');
      setInvoiceStartNumber(profile.invoice_start_number || 1);
      setInvoicePadding(profile.invoice_padding || 4);
      setInvoiceIncludeYear(profile.invoice_include_year || false);
    } catch (error) {
      console.error('Failed to fetch invoice settings:', error);
      toast.error('Failed to load invoice settings');
    } finally {
      setLoading(false);
    }
  };

  const updatePreview = () => {
    const paddedNumber = invoiceStartNumber.toString().padStart(invoicePadding, '0');

    if (invoiceIncludeYear) {
      const currentYear = new Date().getFullYear();
      setPreviewNumber(`${invoicePrefix}${currentYear}-${paddedNumber}`);
    } else {
      setPreviewNumber(`${invoicePrefix}${paddedNumber}`);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);

      await api.auth.updateInvoiceSettings({
        invoice_prefix: invoicePrefix,
        invoice_start_number: invoiceStartNumber,
        invoice_padding: invoicePadding,
        invoice_include_year: invoiceIncludeYear,
      });

      toast.success('Invoice settings saved successfully');
      // Refresh settings from backend to reflect changes
      await fetchInvoiceSettings();
    } catch (error) {
      console.error('Failed to save invoice settings:', error);
      toast.error('Failed to save invoice settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="h-5 w-5" />
            Invoice Numbering Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Hash className="h-5 w-5" />
          Invoice Numbering Settings
        </CardTitle>
        <CardDescription>
          Configure how your invoice numbers are generated automatically
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="invoicePrefix">Invoice Prefix</Label>
            <Input
              id="invoicePrefix"
              value={invoicePrefix}
              onChange={(e) => setInvoicePrefix(e.target.value)}
              placeholder="INV-"
              maxLength={20}
            />
            <p className="text-xs text-gray-500 mt-1">
              Text before the number (e.g., "INV-", "SALE-")
            </p>
          </div>

          <div>
            <Label htmlFor="invoiceStartNumber">Starting Number</Label>
            <Input
              id="invoiceStartNumber"
              type="number"
              value={invoiceStartNumber}
              onChange={(e) => setInvoiceStartNumber(parseInt(e.target.value) || 1)}
              min={1}
            />
            <p className="text-xs text-gray-500 mt-1">
              First invoice number to use
            </p>
          </div>

          <div>
            <Label htmlFor="invoicePadding">Number Padding</Label>
            <Select
              value={invoicePadding.toString()}
              onValueChange={(val) => setInvoicePadding(parseInt(val))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3 digits (001)</SelectItem>
                <SelectItem value="4">4 digits (0001)</SelectItem>
                <SelectItem value="5">5 digits (00001)</SelectItem>
                <SelectItem value="6">6 digits (000001)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500 mt-1">
              How many digits to display
            </p>
          </div>

          <div className="flex items-center space-x-2 md:pt-6 pt-0">
            <Checkbox
              id="invoiceIncludeYear"
              checked={invoiceIncludeYear}
              onCheckedChange={(checked) => setInvoiceIncludeYear(checked as boolean)}
            />
            <Label htmlFor="invoiceIncludeYear" className="cursor-pointer">
              Include current year
            </Label>
          </div>
        </div>

        {/* Preview */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <Label className="text-sm font-semibold mb-2 block">Preview</Label>
          <div className="text-2xl font-mono font-bold text-[#008060] dark:text-[#00a876]">
            {previewNumber}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            This is how your next invoice number will look
          </p>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Note:</strong> Invoice numbers are generated automatically when you create a new invoice.
            The system will use your latest invoice number and increment it by 1.
          </p>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
