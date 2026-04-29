'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { userService, masterDataService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Package } from 'lucide-react';

interface SavedUOM {
  id: number;
  uom_code: string;
  uom_name: string;
  created_at: string;
  updated_at: string;
}

export default function SavedUOMsSection() {
  const [uoms, setUOMs] = useState<SavedUOM[]>([]);
  const [fbrUOMs, setFBRUOMs] = useState<Array<{code: string, name: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // Form state
  const [selectedUOM, setSelectedUOM] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load saved UOMs
      const savedData = await userService.getSavedUOMs(true);
      setUOMs(savedData);

      // Load FBR UOMs
      const fbrData = await masterDataService.getUomCodes();
      setFBRUOMs(fbrData);
    } catch (error) {
      console.error('Error loading UOMs:', error);
      toast.error('Failed to load UOMs');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedUOM('');
    setShowAddForm(false);
  };

  const handleAddUOM = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedUOM) {
      toast.error('Please select a UOM');
      return;
    }

    try {
      setSaving(true);

      const uomData = fbrUOMs.find(u => u.code === selectedUOM);
      if (!uomData) {
        toast.error('Invalid UOM selected');
        return;
      }

      await userService.createSavedUOM({
        uom_code: uomData.code,
        uom_name: uomData.name
      });

      toast.success('✓ UOM added successfully!');
      await loadData();
      resetForm();
    } catch (error: any) {
      console.error('Error adding UOM:', error);
      toast.error(error.message || 'Failed to add UOM');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUOM = async (id: number) => {
    if (!confirm('Are you sure you want to delete this UOM?')) {
      return;
    }

    try {
      await userService.deleteSavedUOM(id);
      toast.success('UOM deleted successfully');
      await loadData();
    } catch (error: any) {
      console.error('Error deleting UOM:', error);
      toast.error(error.message || 'Failed to delete UOM');
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading UOMs...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Filter out already saved UOMs
  const availableUOMs = fbrUOMs.filter(fbr => !uoms.some(saved => saved.uom_code === fbr.code));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-lg sm:text-xl">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            My UOMs ({uoms.length})
          </div>
          {!showAddForm && availableUOMs.length > 0 && (
            <Button
              onClick={() => setShowAddForm(true)}
              size="sm"
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add UOM
            </Button>
          )}
        </CardTitle>
        <CardDescription className="text-sm">
          Select UOMs from FBR master data to use in your invoices.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add Form */}
        {showAddForm && (
          <div className="p-4 bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#3d3d3d] rounded-xl">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              Add New UOM
            </h3>
            <form onSubmit={handleAddUOM} className="space-y-4">
              <div>
                <Label htmlFor="uom">Select UOM *</Label>
                <Select value={selectedUOM} onValueChange={setSelectedUOM}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a UOM from FBR list" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableUOMs.map((uom) => (
                      <SelectItem key={uom.code} value={uom.code}>
                        {uom.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                  Select from FBR approved UOMs
                </p>
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
                  {saving ? 'Saving...' : 'Add UOM'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* UOMs List */}
        {uoms.length === 0 ? (
          <div className="text-center py-8">
            <Package className="h-12 w-12 text-[#8c9196] mx-auto mb-4" />
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              No UOMs added yet. Add UOMs to use in your invoices.
            </p>
            {!showAddForm && availableUOMs.length > 0 && (
              <Button
                onClick={() => setShowAddForm(true)}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First UOM
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {uoms.map((uom) => (
              <div
                key={uom.id}
                className="p-4 border rounded-xl bg-[#f6f6f7] dark:bg-[#2e2e2e] border-[#e1e3e5] dark:border-[#3d3d3d]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                      {uom.uom_name}
                    </h4>
                  </div>

                  <Button
                    variant="destructive"
                    size="icon"
                    onClick={() => handleDeleteUOM(uom.id)}
                    className="flex-shrink-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
