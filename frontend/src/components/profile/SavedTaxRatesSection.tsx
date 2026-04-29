'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { userService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, Percent } from 'lucide-react';

interface SavedTaxRate {
  id: number;
  tax_rate: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export default function SavedTaxRatesSection() {
  const [taxRates, setTaxRates] = useState<SavedTaxRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTaxRate, setEditingTaxRate] = useState<SavedTaxRate | null>(null);

  // Form state
  const [taxRate, setTaxRate] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    loadTaxRates();
  }, []);

  const loadTaxRates = async () => {
    try {
      setLoading(true);
      const data = await userService.getSavedTaxRates(true);
      setTaxRates(data);
    } catch (error) {
      console.error('Error loading tax rates:', error);
      toast.error('Failed to load saved tax rates');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setTaxRate('');
    setDescription('');
    setEditingTaxRate(null);
    setShowAddForm(false);
  };

  const handleAddTaxRate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!taxRate) {
      toast.error('Tax Rate is required');
      return;
    }

    // Validate tax rate is a number
    if (isNaN(Number(taxRate))) {
      toast.error('Tax Rate must be a number');
      return;
    }

    try {
      setSaving(true);

      await userService.createSavedTaxRate({
        tax_rate: taxRate,
        description: description || undefined
      });

      toast.success('✓ Tax rate added successfully!');
      await loadTaxRates();
      resetForm();
    } catch (error: any) {
      console.error('Error adding tax rate:', error);
      toast.error(error.message || 'Failed to add tax rate');
    } finally {
      setSaving(false);
    }
  };

  const handleEditTaxRate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingTaxRate) return;

    if (!taxRate) {
      toast.error('Tax Rate is required');
      return;
    }

    // Validate tax rate is a number
    if (isNaN(Number(taxRate))) {
      toast.error('Tax Rate must be a number');
      return;
    }

    try {
      setSaving(true);

      await userService.updateSavedTaxRate(editingTaxRate.id, {
        tax_rate: taxRate,
        description: description || undefined
      });

      toast.success('✓ Tax rate updated successfully!');
      await loadTaxRates();
      resetForm();
    } catch (error: any) {
      console.error('Error updating tax rate:', error);
      toast.error(error.message || 'Failed to update tax rate');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTaxRate = async (id: number) => {
    if (!confirm('Are you sure you want to delete this tax rate?')) {
      return;
    }

    try {
      await userService.deleteSavedTaxRate(id);
      toast.success('Tax rate deleted successfully');
      await loadTaxRates();
    } catch (error: any) {
      console.error('Error deleting tax rate:', error);
      toast.error(error.message || 'Failed to delete tax rate');
    }
  };

  const startEdit = (taxRateItem: SavedTaxRate) => {
    setEditingTaxRate(taxRateItem);
    setTaxRate(taxRateItem.tax_rate);
    setDescription(taxRateItem.description || '');
    setShowAddForm(true);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading tax rates...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-lg sm:text-xl">
          <div className="flex items-center gap-2">
            <Percent className="h-5 w-5" />
            My Tax Rates ({taxRates.length})
          </div>
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              size="sm"
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Tax Rate
            </Button>
          )}
        </CardTitle>
        <CardDescription className="text-sm">
          Add tax rates that you commonly use in your invoices (e.g., 18, 24).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="p-4 bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#3d3d3d] rounded-xl">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              {editingTaxRate ? 'Edit Tax Rate' : 'Add New Tax Rate'}
            </h3>
            <form onSubmit={editingTaxRate ? handleEditTaxRate : handleAddTaxRate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="taxRate">Tax Rate (%) *</Label>
                  <Input
                    id="taxRate"
                    type="text"
                    value={taxRate}
                    onChange={(e) => setTaxRate(e.target.value)}
                    placeholder="e.g., 18"
                    required
                  />
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Enter the tax rate percentage
                  </p>
                </div>
                <div>
                  <Label htmlFor="description">Description (Optional)</Label>
                  <Input
                    id="description"
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g., Standard Rate"
                  />
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Optional label for this rate
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={resetForm}
                  disabled={saving}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={saving}
                  className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
                >
                  {saving ? 'Saving...' : editingTaxRate ? 'Update Tax Rate' : 'Add Tax Rate'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Tax Rates List */}
        {taxRates.length === 0 ? (
          <div className="text-center py-8">
            <Percent className="h-12 w-12 text-[#8c9196] mx-auto mb-4" />
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              No tax rates added yet. Add tax rates to use in your invoices.
            </p>
            {!showAddForm && (
              <Button
                onClick={() => setShowAddForm(true)}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Tax Rate
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {taxRates.map((rate) => (
              <div
                key={rate.id}
                className="p-4 border rounded-xl bg-[#f6f6f7] dark:bg-[#2e2e2e] border-[#e1e3e5] dark:border-[#3d3d3d]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                      {rate.tax_rate}%
                    </h4>
                    {rate.description && (
                      <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                        {rate.description}
                      </p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(rate)}
                      className="flex-shrink-0"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDeleteTaxRate(rate.id)}
                      className="flex-shrink-0"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
