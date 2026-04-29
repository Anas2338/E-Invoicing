'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { userService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, CheckCircle, XCircle, AlertCircle, Package, Info } from 'lucide-react';

interface SavedProduct {
  id: number;
  hs_code: string;
  product_description: string;
  default_uom: string | null;
  default_rate: string | null;
  default_sale_type: string | null;
  default_unit_price: number | null;
  display_order: number;
  is_active: number;
  fbr_validated: boolean;
  fbr_validation_date: string | null;
  fbr_validation_error: string | null;
  created_at: string;
  updated_at: string;
}

export default function SavedProductsSection() {
  const [products, setProducts] = useState<SavedProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<SavedProduct | null>(null);

  // Form state
  const [hsCode, setHsCode] = useState('');
  const [productDescription, setProductDescription] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await userService.getSavedProducts(true);
      setProducts(data);
    } catch (error) {
      console.error('Error loading products:', error);
      toast.error('Failed to load saved products');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setHsCode('');
    setProductDescription('');
    setEditingProduct(null);
    setShowAddForm(false);
  };

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hsCode || !productDescription) {
      toast.error('HS Code and Product Description are required');
      return;
    }

    try {
      setSaving(true);

      const productData = {
        hs_code: hsCode,
        product_description: productDescription,
      };

      const newProduct = await userService.createSavedProduct(productData);

      if (newProduct.fbr_validated) {
        toast.success('✓ Item added - HS code validated with FBR!');
      } else {
        toast.warning(`⚠ Item added but HS code validation failed:\n${newProduct.fbr_validation_error}`);
      }

      await loadProducts();
      resetForm();
    } catch (error: any) {
      console.error('Error adding product:', error);
      toast.error(error.message || 'Failed to add product');
    } finally {
      setSaving(false);
    }
  };

  const handleEditProduct = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingProduct) return;

    try {
      setSaving(true);

      const productData = {
        hs_code: hsCode,
        product_description: productDescription,
      };

      const updatedProduct = await userService.updateSavedProduct(editingProduct.id, productData);

      if (updatedProduct.fbr_validated) {
        toast.success('✓ Item updated - HS code validated with FBR!');
      } else {
        toast.warning(`⚠ Item updated but HS code validation failed:\n${updatedProduct.fbr_validation_error}`);
      }

      await loadProducts();
      resetForm();
    } catch (error: any) {
      console.error('Error updating product:', error);
      toast.error(error.message || 'Failed to update product');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProduct = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product?')) {
      return;
    }

    try {
      await userService.deleteSavedProduct(id, false);
      toast.success('Product deleted successfully');
      await loadProducts();
    } catch (error: any) {
      console.error('Error deleting product:', error);
      toast.error(error.message || 'Failed to delete product');
    }
  };

  const startEdit = (product: SavedProduct) => {
    setEditingProduct(product);
    setHsCode(product.hs_code);
    setProductDescription(product.product_description);
    setShowAddForm(true);
  };

  const validatedCount = products.filter(p => p.fbr_validated).length;

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading products...</p>
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
            <Package className="h-5 w-5" />
            My Validated Items ({validatedCount}/{products.length} validated)
          </div>
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              size="sm"
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Item
            </Button>
          )}
        </CardTitle>
        <CardDescription className="text-sm">
          Add HS codes to validate against FBR master data. You can use your own product descriptions. Only items with valid HS codes can be used in invoices.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="p-4 bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#3d3d3d] rounded-xl">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              {editingProduct ? 'Edit Item' : 'Add New Item'}
            </h3>
            <form onSubmit={editingProduct ? handleEditProduct : handleAddProduct} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="hsCode">HS Code *</Label>
                  <Input
                    id="hsCode"
                    value={hsCode}
                    onChange={(e) => setHsCode(e.target.value)}
                    placeholder="e.g., 5904.9000"
                    required
                  />
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Enter the HS code to validate against FBR
                  </p>
                </div>
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
                    Enter your own product description
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
                  {saving ? 'Saving...' : editingProduct ? 'Update Item' : 'Add Item'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Products List */}
        {products.length === 0 ? (
          <div className="text-center py-8">
            <Package className="h-12 w-12 text-[#8c9196] mx-auto mb-4" />
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              No items added yet. Add your first HS code and product description to get started.
            </p>
            {!showAddForm && (
              <Button
                onClick={() => setShowAddForm(true)}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Item
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {products.map((product) => (
              <div
                key={product.id}
                className={`p-4 border rounded-xl ${
                  product.fbr_validated
                    ? 'bg-[#d1fae5] dark:bg-[#064e3b]/30 border-[#a7f3d0] dark:border-[#065f46]'
                    : 'bg-[#fee2e2] dark:bg-[#7f1d1d]/30 border-[#fecaca] dark:border-[#991b1b]'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {product.hs_code}
                      </h4>
                      {product.fbr_validated ? (
                        <Badge className="bg-[#065f46] text-white dark:bg-[#34d399] dark:text-[#1a1a1a]">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          FBR Validated
                        </Badge>
                      ) : (
                        <Badge className="bg-[#991b1b] text-white dark:bg-[#f87171] dark:text-[#1a1a1a]">
                          <XCircle className="h-3 w-3 mr-1" />
                          Not Validated
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-2">
                      {product.product_description}
                    </p>

                    {product.fbr_validation_error && (
                      <div className="mt-2 p-2 bg-white dark:bg-[#1a1a1a] border border-[#fecaca] dark:border-[#991b1b] rounded">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="h-4 w-4 text-[#991b1b] dark:text-[#f87171] flex-shrink-0 mt-0.5" />
                          <p className="text-xs text-[#991b1b] dark:text-[#f87171]">
                            {product.fbr_validation_error}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(product)}
                      className="flex-shrink-0"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDeleteProduct(product.id)}
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

        {/* Info Box */}
        {products.length > 0 && validatedCount === 0 && (
          <div className="p-4 bg-[#fef3c7] dark:bg-[#78350f]/30 border border-[#fde68a] dark:border-[#92400e] rounded-xl">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-[#92400e] dark:text-[#fbbf24] mb-1">
                  No Validated Items
                </h4>
                <p className="text-sm text-[#92400e] dark:text-[#fbbf24]">
                  You need at least one item with a valid HS code to create invoices. Please ensure your HS codes exist in FBR master data.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Info Box - UOM and Price */}
        {products.length > 0 && validatedCount > 0 && (
          <div className="p-4 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 border border-[#bfdbfe] dark:border-[#1e3a8a] rounded-xl">
            <div className="flex items-start gap-2">
              <Info className="h-5 w-5 text-[#1e40af] dark:text-[#60a5fa] flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-[#1e40af] dark:text-[#60a5fa] mb-1">
                  Note
                </h4>
                <p className="text-sm text-[#1e40af] dark:text-[#60a5fa]">
                  UOM, tax rate, and prices will be entered when creating each invoice, as they may vary per transaction.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
