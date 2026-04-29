'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { userService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, CheckCircle, XCircle, AlertCircle, Hash } from 'lucide-react';

interface SavedHSCode {
  id: number;
  hs_code: string;
  fbr_validated: boolean;
  fbr_validation_date: string | null;
  fbr_validation_error: string | null;
  created_at: string;
  updated_at: string;
}

export default function SavedHSCodesSection() {
  const [hsCodes, setHSCodes] = useState<SavedHSCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingHSCode, setEditingHSCode] = useState<SavedHSCode | null>(null);

  // Form state
  const [hsCode, setHsCode] = useState('');

  useEffect(() => {
    loadHSCodes();
  }, []);

  const loadHSCodes = async () => {
    try {
      setLoading(true);
      const data = await userService.getSavedHSCodes(true);
      setHSCodes(data);
    } catch (error) {
      console.error('Error loading HS codes:', error);
      toast.error('Failed to load saved HS codes');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setHsCode('');
    setEditingHSCode(null);
    setShowAddForm(false);
  };

  const handleAddHSCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hsCode) {
      toast.error('HS Code is required');
      return;
    }

    try {
      setSaving(true);

      const newHSCode = await userService.createSavedHSCode({ hs_code: hsCode });

      if (newHSCode.fbr_validated) {
        toast.success('✓ HS Code added and validated with FBR!');
      } else {
        toast.warning(`⚠ HS Code added but validation failed:\n${newHSCode.fbr_validation_error}`);
      }

      await loadHSCodes();
      resetForm();
    } catch (error: any) {
      console.error('Error adding HS code:', error);
      toast.error(error.message || 'Failed to add HS code');
    } finally {
      setSaving(false);
    }
  };

  const handleEditHSCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingHSCode) return;

    try {
      setSaving(true);

      const updatedHSCode = await userService.updateSavedHSCode(editingHSCode.id, { hs_code: hsCode });

      if (updatedHSCode.fbr_validated) {
        toast.success('✓ HS Code updated and validated with FBR!');
      } else {
        toast.warning(`⚠ HS Code updated but validation failed:\n${updatedHSCode.fbr_validation_error}`);
      }

      await loadHSCodes();
      resetForm();
    } catch (error: any) {
      console.error('Error updating HS code:', error);
      toast.error(error.message || 'Failed to update HS code');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteHSCode = async (id: number) => {
    if (!confirm('Are you sure you want to delete this HS code?')) {
      return;
    }

    try {
      await userService.deleteSavedHSCode(id);
      toast.success('HS Code deleted successfully');
      await loadHSCodes();
    } catch (error: any) {
      console.error('Error deleting HS code:', error);
      toast.error(error.message || 'Failed to delete HS code');
    }
  };

  const startEdit = (hsCodeItem: SavedHSCode) => {
    setEditingHSCode(hsCodeItem);
    setHsCode(hsCodeItem.hs_code);
    setShowAddForm(true);
  };

  const validatedCount = hsCodes.filter(h => h.fbr_validated).length;

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
            <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading HS codes...</p>
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
            <Hash className="h-5 w-5" />
            My HS Codes ({validatedCount}/{hsCodes.length} validated)
          </div>
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              size="sm"
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add HS Code
            </Button>
          )}
        </CardTitle>
        <CardDescription className="text-sm">
          Add HS codes to validate against FBR master data. Only validated HS codes can be used in invoices.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="p-4 bg-[#f6f6f7] dark:bg-[#2e2e2e] border border-[#e1e3e5] dark:border-[#3d3d3d] rounded-xl">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              {editingHSCode ? 'Edit HS Code' : 'Add New HS Code'}
            </h3>
            <form onSubmit={editingHSCode ? handleEditHSCode : handleAddHSCode} className="space-y-4">
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
                  {saving ? 'Saving...' : editingHSCode ? 'Update HS Code' : 'Add HS Code'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* HS Codes List */}
        {hsCodes.length === 0 ? (
          <div className="text-center py-8">
            <Hash className="h-12 w-12 text-[#8c9196] mx-auto mb-4" />
            <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
              No HS codes added yet. Add your first HS code to get started.
            </p>
            {!showAddForm && (
              <Button
                onClick={() => setShowAddForm(true)}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First HS Code
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {hsCodes.map((hsCodeItem) => (
              <div
                key={hsCodeItem.id}
                className={`p-4 border rounded-xl ${
                  hsCodeItem.fbr_validated
                    ? 'bg-[#d1fae5] dark:bg-[#064e3b]/30 border-[#a7f3d0] dark:border-[#065f46]'
                    : 'bg-[#fee2e2] dark:bg-[#7f1d1d]/30 border-[#fecaca] dark:border-[#991b1b]'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {hsCodeItem.hs_code}
                      </h4>
                      {hsCodeItem.fbr_validated ? (
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

                    {hsCodeItem.fbr_validation_error && (
                      <div className="mt-2 p-2 bg-white dark:bg-[#1a1a1a] border border-[#fecaca] dark:border-[#991b1b] rounded">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="h-4 w-4 text-[#991b1b] dark:text-[#f87171] flex-shrink-0 mt-0.5" />
                          <p className="text-xs text-[#991b1b] dark:text-[#f87171]">
                            {hsCodeItem.fbr_validation_error}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(hsCodeItem)}
                      className="flex-shrink-0"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDeleteHSCode(hsCodeItem.id)}
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
        {hsCodes.length > 0 && validatedCount === 0 && (
          <div className="p-4 bg-[#fef3c7] dark:bg-[#78350f]/30 border border-[#fde68a] dark:border-[#92400e] rounded-xl">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-[#92400e] dark:text-[#fbbf24] mb-1">
                  No Validated HS Codes
                </h4>
                <p className="text-sm text-[#92400e] dark:text-[#fbbf24]">
                  You need at least one validated HS code to create invoices. Please ensure your HS codes exist in FBR master data.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
