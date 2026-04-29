'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { userService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, FileText } from 'lucide-react';

interface SavedProductDescription {
  id: number;
  product_description: string;
  created_at: string;
  updated_at: string;
}

export default function SavedProductDescriptionsSection() {
  const [descriptions, setDescriptions] = useState<SavedProductDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingDescription, setEditingDescription] = useState<SavedProductDescription | null>(null);

  // Form state
  const [productDescription, setProductDescription] = useState('');

  useEffect(() => {
    loadDescriptions();
  }, []);

  const loadDescriptions = async () => {
    try {
      setLoading(true);
      const data = await userService.getSavedProductDescriptions(true);
      setDescriptions(data);
    } catch (error) {
      console.error('Error loading product descriptions:', error);
      toast.error('Failed to load saved product descriptions');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setProductDescription('');
    setEditingDescription(null);
    setShowAddForm(false);
  };

  const handleAddDescription = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!productDescription) {
      toast.error('Product Description is required');
      return;
    }

    try {
      setSaving(true);

      await userService.createSavedProductDescription({ product_description: productDescription });
      toast.success('✓ Product description added successfully!');

      await loadDescriptions();
      resetForm();
    } catch (error: any) {
      console.error('Error adding product description:', error);
      toast.error(error.message || 'Failed to add product description');
    } finally {
      setSaving(false);
    }
  };

  const handleEditDescription = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingDescription) return;

    try {
      setSaving(true);

      await userService.updateSavedProductDescription(editingDescription.id, { product_description: productDescription });
      toast.success('✓ Product description updated successfully!');

      await loadDescriptions();
      resetForm();
    } catch (error: any) {
      console.error('Error updating product description:', error);
      toast.error(error.message || 'Failed to update product description');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDescription = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product description?')) {
      return;
    }

    try {
      await userService.deleteSavedProductDescription(id);
      toast.success('Product description deleted successfully');
      await loadDescriptions();
    } catch (error: any) {
      console.error('Error deleting product description:', error);
      toast.error(error.message || 'Failed to delete product description');
    }
  };

  const startEdit = (description: SavedProductDescription) => {
    setEditingDescription(description);
    setProductDescription(description.product_description);
    setShowAddForm(true);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading product descriptions...</p>
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
            <FileText className="h-5 w-5" />
            My Product Descriptions ({descriptions.length})
          </div>
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              size="sm"
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Description
            </Button>
          )}
        </CardTitle>
        <CardDescription className="text-sm">
          Add product descriptions that you commonly use. These can be paired with HS codes when creating invoices.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="p-4 bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#3d3d3d] rounded-xl">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              {editingDescription ? 'Edit Product Description' : 'Add New Product Description'}
            </h3>
            <form onSubmit={editingDescription ? handleEditDescription : handleAddDescription} className="space-y-4">
              <div>
                <Label htmlFor="productDescription">Product Description *</Label>
                <Input
                  id="productDescription"
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                  placeholder="e.g., Linoleum floor covering"
                  required
                />
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                  Enter your product description
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
                  {saving ? 'Saving...' : editingDescription ? 'Update Description' : 'Add Description'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Descriptions List */}
        {descriptions.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-[#8c9196] mx-auto mb-4" />
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              No product descriptions added yet. Add your first product description to get started.
            </p>
            {!showAddForm && (
              <Button
                onClick={() => setShowAddForm(true)}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Description
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {descriptions.map((description) => (
              <div
                key={description.id}
                className="p-4 border rounded-xl bg-[#f6f6f7] dark:bg-[#2e2e2e] border-[#e1e3e5] dark:border-[#3d3d3d]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {description.product_description}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(description)}
                      className="flex-shrink-0"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDeleteDescription(description.id)}
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
