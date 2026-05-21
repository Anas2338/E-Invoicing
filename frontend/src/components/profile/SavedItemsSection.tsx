'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { api } from '@/lib/api';
import { masterDataService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, CheckCircle, XCircle, Package, Loader2, Download, Upload, Search } from 'lucide-react';

interface SavedItem {
  id: number;
  item_code: string;
  item_name: string;
  hs_code: string;
  product_description: string;
  default_uom: string | null;
  default_rate: string | null;
  transaction_type: string | null;
  sro_schedule_no: string | null;
  sro_item_serial_no: string | null;
  fbr_validated: boolean;
  created_at: string;
  updated_at: string;
}

interface UOM {
  code: string;
  name: string;
}

interface TransactionType {
  code: string;
  name: string;
}

export default function SavedItemsSection() {
  const [items, setItems] = useState<SavedItem[]>([]);
  const [uoms, setUoms] = useState<UOM[]>([]);
  const [transactionTypes, setTransactionTypes] = useState<TransactionType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validatingHSCode, setValidatingHSCode] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingItem, setEditingItem] = useState<SavedItem | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<{
    success_count: number;
    error_count: number;
    errors: string[];
    total_errors: number;
  } | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<number[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  // Form state
  const [itemCode, setItemCode] = useState('');
  const [itemName, setItemName] = useState('');
  const [hsCode, setHsCode] = useState('');
  const [hsCodeValid, setHsCodeValid] = useState<boolean | null>(null);
  const [hsCodeError, setHsCodeError] = useState<string>('');
  const [productDescription, setProductDescription] = useState('');
  const [defaultUom, setDefaultUom] = useState('');
  const [defaultRate, setDefaultRate] = useState('');
  const [transactionType, setTransactionType] = useState('');
  const [sroScheduleNo, setSroScheduleNo] = useState('');
  const [sroItemSerialNo, setSroItemSerialNo] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [itemsData, masterData] = await Promise.all([
        api.auth.getSavedProducts(true),
        masterDataService.getAllMasterData(),
      ]);
      setItems(itemsData);
      setUoms(masterData.uom || []);
      setTransactionTypes(masterData.transaction_types || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load saved items');
    } finally {
      setLoading(false);
    }
  };

  const validateHSCode = async (code: string) => {
    if (!code || code.trim() === '') {
      setHsCodeValid(null);
      setHsCodeError('');
      return;
    }

    setValidatingHSCode(true);

    try {
      // Call API to validate HS code against local database
      const result = await masterDataService.validateHSCode(code.trim());

      if (result.valid) {
        setHsCodeValid(true);
        setHsCodeError('');
      } else {
        setHsCodeValid(false);
        setHsCodeError('HS Code not found in FBR database');
      }
    } catch (error) {
      console.error('Error validating HS code:', error);
      setHsCodeValid(false);
      setHsCodeError('Error validating HS Code');
    } finally {
      setValidatingHSCode(false);
    }
  };

  const getDefaultTransactionType = () => {
    if (transactionTypes.length === 0) return '';
    return transactionTypes[0].name;
  };

  const handleOpenAddForm = () => {
    setTransactionType(getDefaultTransactionType());
    setShowAddForm(true);
  };

  const resetForm = () => {
    setItemCode('');
    setItemName('');
    setHsCode('');
    setHsCodeValid(null);
    setHsCodeError('');
    setProductDescription('');
    setDefaultUom('');
    setDefaultRate('');
    setTransactionType('');
    setSroScheduleNo('');
    setSroItemSerialNo('');
    setEditingItem(null);
    setShowAddForm(false);
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!itemCode || !itemName || !hsCode || !productDescription || !defaultUom || !defaultRate || !transactionType) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setSaving(true);

      const newItem = await api.auth.createSavedProduct({
        item_code: itemCode,
        item_name: itemName,
        hs_code: hsCode,
        product_description: productDescription,
        default_uom: defaultUom,
        default_rate: defaultRate,
        default_sale_type: transactionType,
        transaction_type: transactionType,
        sro_schedule_no: sroScheduleNo || undefined,
        sro_item_serial_no: sroItemSerialNo || undefined,
      });

      if (newItem.fbr_validated) {
        toast.success('✓ Item added and HS Code validated with FBR!');
      } else {
        toast.warning('⚠ Item added but HS Code validation failed');
      }

      await loadData();
      resetForm();
    } catch (error: any) {
      console.error('Error adding item:', error);
      toast.error(error.message || 'Failed to add item');
    } finally {
      setSaving(false);
    }
  };

  const handleEditItem = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingItem) return;

    if (!itemCode || !itemName || !hsCode || !productDescription || !defaultUom || !defaultRate || !transactionType) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setSaving(true);

      const updatedItem = await api.auth.updateSavedProduct(editingItem.id, {
        item_code: itemCode,
        item_name: itemName,
        hs_code: hsCode,
        product_description: productDescription,
        default_uom: defaultUom,
        default_rate: defaultRate,
        default_sale_type: transactionType,
        transaction_type: transactionType,
        sro_schedule_no: sroScheduleNo || undefined,
        sro_item_serial_no: sroItemSerialNo || undefined,
      });

      if (updatedItem.fbr_validated) {
        toast.success('✓ Item updated and HS Code validated with FBR!');
      } else {
        toast.warning('⚠ Item updated but HS Code validation failed');
      }

      await loadData();
      resetForm();
    } catch (error: any) {
      console.error('Error updating item:', error);
      toast.error(error.message || 'Failed to update item');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteItem = async (id: number) => {
    if (!confirm('Are you sure you want to delete this item?')) {
      return;
    }

    try {
      await api.auth.deleteSavedProduct(id);
      toast.success('Item deleted successfully');
      await loadData();
    } catch (error: any) {
      console.error('Error deleting item:', error);
      toast.error(error.message || 'Failed to delete item');
    }
  };

  const startEdit = (item: SavedItem) => {
    setEditingItem(item);
    setItemCode(item.item_code);
    setItemName(item.item_name);
    setHsCode(item.hs_code);
    setHsCodeValid(item.fbr_validated);
    setHsCodeError('');
    setProductDescription(item.product_description);
    setDefaultUom(item.default_uom || '');
    setDefaultRate(item.default_rate || '');
    setTransactionType(transactionTypes.find(t => t.code === item.transaction_type)?.name || item.transaction_type || '');
    setSroScheduleNo(item.sro_schedule_no || '');
    setSroItemSerialNo(item.sro_item_serial_no || '');
    setShowAddForm(true);
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50);
  };

  const handleDownloadTemplate = async () => {
    try {
      await api.auth.downloadSavedProductsTemplate();
      toast.success('Template downloaded successfully');
    } catch (error: any) {
      console.error('Error downloading template:', error);
      toast.error(error.message || 'Failed to download template');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error('Please upload an Excel file (.xlsx or .xls)');
      event.target.value = '';
      return;
    }

    try {
      setUploading(true);
      setUploadResults(null);

      const results = await api.auth.uploadSavedProducts(file);
      setUploadResults(results);

      if (results.success_count > 0) {
        toast.success(`Successfully uploaded ${results.success_count} items`);
        await loadData();
      }

      if (results.error_count > 0) {
        toast.warning(`${results.error_count} items failed to upload. Check details below.`);
      }
    } catch (error: any) {
      console.error('Error uploading file:', error);
      toast.error(error.message || 'Failed to upload file');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const formatHSCode = (code: string): string => {
    // If code already has dots, return as-is
    if (code.includes('.')) return code;

    // Format HS code with dots: 8509401 -> 8509.4010 or 84713000 -> 8471.3000
    if (!code) return code;
    const cleaned = code.replace(/\./g, '');
    if (cleaned.length === 8) {
      return `${cleaned.slice(0, 4)}.${cleaned.slice(4)}`;
    } else if (cleaned.length === 7) {
      return `${cleaned.slice(0, 4)}.${cleaned.slice(4)}0`;
    }
    return code;
  };

  const filteredItems = items.filter((item) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return item.item_name.toLowerCase().includes(query);
  });

  const handleSearch = () => {
    setSearchQuery(searchInput);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
  };

  const handleSearchKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSelectAll = () => {
    if (selectedItems.length === filteredItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredItems.map(item => item.id));
    }
  };

  const handleSelectItem = (id: number) => {
    if (selectedItems.includes(id)) {
      setSelectedItems(selectedItems.filter(itemId => itemId !== id));
    } else {
      setSelectedItems([...selectedItems, id]);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedItems.length === 0) return;

    if (!confirm(`Are you sure you want to delete ${selectedItems.length} selected item(s)?`)) {
      return;
    }

    try {
      setIsDeleting(true);

      // Use bulk delete endpoint for better performance
      await api.auth.bulkDeleteSavedProducts(selectedItems);

      toast.success(`Successfully deleted ${selectedItems.length} item(s)`);
      setSelectedItems([]);
      await loadData();
    } catch (error: any) {
      console.error('Error deleting items:', error);
      toast.error(error.message || 'Failed to delete items');
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Saved Items
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876]"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
              <Package className="h-5 w-5 flex-shrink-0" />
              Saved Items
            </CardTitle>
            <CardDescription className="text-sm mt-1">
              Manage your saved items for quick invoice creation ({items.length} items)
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2 flex-shrink-0">
            {!showAddForm && (
              <>
                <Button
                  onClick={handleDownloadTemplate}
                  size="sm"
                  variant="outline"
                  className="hidden sm:flex"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download Template
                </Button>
                <Button
                  onClick={() => document.getElementById('excel-upload')?.click()}
                  size="sm"
                  variant="outline"
                  disabled={uploading}
                >
                  {uploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Excel
                    </>
                  )}
                </Button>
                <input
                  id="excel-upload"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <Button
                  onClick={handleOpenAddForm}
                  size="sm"
                  className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Item
                </Button>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Upload Results */}
        {uploadResults && (
          <div className="mb-6 p-4 border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl bg-[#f6f6f7] dark:bg-[#1a1a1a]">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">
              Upload Results
            </h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                <span className="text-[#202223] dark:text-[#e3e3e3]">
                  Successfully uploaded: <strong>{uploadResults.success_count}</strong> items
                </span>
              </div>
              {uploadResults.error_count > 0 && (
                <>
                  <div className="flex items-center gap-2 text-sm">
                    <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="text-[#202223] dark:text-[#e3e3e3]">
                      Failed: <strong>{uploadResults.error_count}</strong> items
                    </span>
                  </div>
                  {uploadResults.errors.length > 0 && (
                    <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                      <p className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">
                        Error Details {uploadResults.total_errors > uploadResults.errors.length && `(showing first ${uploadResults.errors.length} of ${uploadResults.total_errors})`}:
                      </p>
                      <ul className="text-xs text-red-700 dark:text-red-400 space-y-1 list-disc list-inside">
                        {uploadResults.errors.map((error, index) => (
                          <li key={index}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
              <Button
                onClick={() => setUploadResults(null)}
                size="sm"
                variant="outline"
                className="mt-3"
              >
                Dismiss
              </Button>
            </div>
          </div>
        )}

        {/* Add/Edit Form */}
        {showAddForm && (
          <form ref={formRef} onSubmit={editingItem ? handleEditItem : handleAddItem} className="mb-6 p-4 border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl bg-[#f6f6f7] dark:bg-[#1a1a1a]">
            <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
              {editingItem ? 'Edit Item' : 'Add New Item'}
            </h3>

            <div className="space-y-4">
              {/* Item Code */}
              <div>
                <Label htmlFor="itemCode">Item Code *</Label>
                <Input
                  id="itemCode"
                  type="text"
                  value={itemCode}
                  onChange={(e) => setItemCode(e.target.value)}
                  placeholder="e.g., ITEM-001 or SKU-12345"
                  className="mt-1"
                  required
                />
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                  Unique code to identify this item in your inventory
                </p>
              </div>

              {/* Item Name */}
              <div>
                <Label htmlFor="itemName">Item Name *</Label>
                <Input
                  id="itemName"
                  type="text"
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  placeholder="e.g., Laptop Computer"
                  className="mt-1"
                  required
                />
              </div>

              {/* HS Code with validation */}
              <div>
                <Label htmlFor="hsCode" className="flex items-center gap-2">
                  HS Code *
                  {hsCodeValid === true && (
                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                  )}
                  {hsCodeValid === false && (
                    <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  )}
                </Label>
                <div className="relative">
                  <Input
                    id="hsCode"
                    type="text"
                    value={hsCode}
                    onChange={(e) => setHsCode(e.target.value)}
                    onBlur={(e) => validateHSCode(e.target.value)}
                    placeholder="Enter HS Code"
                    className="mt-1 pr-10"
                    required
                  />
                  {validatingHSCode && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 mt-0.5">
                      <Loader2 className="h-4 w-4 animate-spin text-[#008060] dark:text-[#00a876]" />
                    </div>
                  )}
                </div>
                {hsCodeError && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">{hsCodeError}</p>
                )}
                {hsCodeValid === true && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                    ✓ HS Code validated against FBR database
                  </p>
                )}
              </div>

              {/* Product Description */}
              <div>
                <Label htmlFor="productDescription">Product Description *</Label>
                <Input
                  id="productDescription"
                  type="text"
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                  placeholder="Enter product description"
                  className="mt-1"
                  required
                />
              </div>

              {/* UOM */}
              <div>
                <Label htmlFor="defaultUom">Unit of Measurement *</Label>
                <Select value={defaultUom} onValueChange={setDefaultUom}>
                  <SelectTrigger className="mt-1">
                    {defaultUom ? (
                      <span>{defaultUom}</span>
                    ) : (
                      <span className="text-muted-foreground">Select UOM</span>
                    )}
                  </SelectTrigger>
                  <SelectContent>
                    {uoms.map((uom) => (
                      <SelectItem key={uom.code} value={uom.name}>
                        {uom.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Tax Rate */}
              <div>
                <Label htmlFor="defaultRate">Tax Rate *</Label>
                <Input
                  id="defaultRate"
                  type="text"
                  value={defaultRate}
                  onChange={(e) => setDefaultRate(e.target.value)}
                  placeholder="e.g., 18"
                  className="mt-1"
                  required
                />
              </div>

              {/* Transaction Type */}
              <div>
                <Label htmlFor="transactionType">Transaction Type *</Label>
                <Select value={transactionType} onValueChange={setTransactionType}>
                  <SelectTrigger className="mt-1">
                    {transactionType ? (
                      <span>{transactionType}</span>
                    ) : (
                      <span className="text-muted-foreground">Select transaction type</span>
                    )}
                  </SelectTrigger>
                  <SelectContent>
                    {transactionTypes.map((type) => (
                      <SelectItem key={type.code} value={type.name}>
                        {type.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* SRO Schedule No (Optional) */}
              <div>
                <Label htmlFor="sroScheduleNo">SRO Schedule No (Optional)</Label>
                <Input
                  id="sroScheduleNo"
                  type="text"
                  value={sroScheduleNo}
                  onChange={(e) => setSroScheduleNo(e.target.value)}
                  placeholder="Enter SRO schedule number"
                  className="mt-1"
                />
              </div>

              {/* SRO Item Serial No (Optional) */}
              <div>
                <Label htmlFor="sroItemSerialNo">SRO Item Serial No (Optional)</Label>
                <Input
                  id="sroItemSerialNo"
                  type="text"
                  value={sroItemSerialNo}
                  onChange={(e) => setSroItemSerialNo(e.target.value)}
                  placeholder="Enter SRO item serial number"
                  className="mt-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
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
                {saving ? 'Saving...' : editingItem ? 'Update Item' : 'Add Item'}
              </Button>
            </div>
          </form>
        )}

        {/* Search Filter */}
        {items.length > 0 && !showAddForm && (
          <div className="mb-4 space-y-3">
            <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2">
              <div className="relative flex-1 min-w-[160px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6d7175] dark:text-[#8c9196]" />
                <Input
                  type="text"
                  placeholder="Search by item name..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyPress={handleSearchKeyPress}
                  className="pl-10"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={handleSearch}
                  size="sm"
                  variant="outline"
                >
                  Search
                </Button>
                {searchQuery && (
                  <Button
                    onClick={handleClearSearch}
                    size="sm"
                    variant="outline"
                  >
                    Clear
                  </Button>
                )}
                {selectedItems.length > 0 && (
                  <Button
                    onClick={handleBulkDelete}
                    disabled={isDeleting}
                    variant="destructive"
                    size="sm"
                  >
                    {isDeleting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete ({selectedItems.length})
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="select-all"
                  checked={selectedItems.length === filteredItems.length && filteredItems.length > 0}
                  onChange={handleSelectAll}
                  className="h-4 w-4 rounded border-[#c9cccf] dark:border-[#5c5f62] text-[#008060] focus:ring-[#008060] dark:text-[#00a876] dark:focus:ring-[#00a876] cursor-pointer"
                />
                <label
                  htmlFor="select-all"
                  className="text-sm text-[#6d7175] dark:text-[#8c9196] cursor-pointer"
                >
                  Select All
                </label>
              </div>
              {searchQuery && (
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                  Showing {filteredItems.length} of {items.length} items
                </p>
              )}
            </div>
          </div>
        )}

        {/* Items List */}
        {filteredItems.length === 0 ? (
          <div className="text-center py-8">
            {searchQuery ? (
              <>
                <Package className="h-12 w-12 mx-auto text-[#6d7175] dark:text-[#8c9196] mb-3" />
                <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">No items match your search</p>
                <Button
                  onClick={handleClearSearch}
                  size="sm"
                  variant="outline"
                >
                  Clear Search
                </Button>
              </>
            ) : (
              <>
                <Package className="h-12 w-12 mx-auto text-[#6d7175] dark:text-[#8c9196] mb-3" />
                <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">No saved items yet</p>
                {!showAddForm && (
                  <Button
                    onClick={handleOpenAddForm}
                    size="sm"
                    className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Your First Item
                  </Button>
                )}
              </>
            )}
          </div>
        ) : (
          <div className="max-h-[600px] overflow-y-auto pr-2 space-y-3">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="p-3 sm:p-4 border border-[#e1e3e5] dark:border-[#2e2e2e] rounded-xl bg-white dark:bg-[#1a1a1a]"
              >
                <div className="flex items-start gap-2 sm:gap-3">
                  <Checkbox
                    id={`item-${item.id}`}
                    checked={selectedItems.includes(item.id)}
                    onCheckedChange={() => handleSelectItem(item.id)}
                    className="mt-1 flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1 sm:gap-2 mb-2">
                      <h4 className="font-semibold text-[#202223] dark:text-[#e3e3e3] text-sm sm:text-base">
                        {item.item_name}
                      </h4>
                      <span className="text-xs text-[#6d7175] dark:text-[#8c9196] font-mono">
                        ({item.item_code})
                      </span>
                      {item.fbr_validated ? (
                        <Badge className="bg-[#d1fae5] text-[#065f46] dark:bg-[#064e3b]/30 dark:text-[#34d399] flex items-center gap-1 text-xs">
                          <CheckCircle className="h-3 w-3" />
                          Validated
                        </Badge>
                      ) : (
                        <Badge className="bg-[#fee2e2] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:text-[#f87171] flex items-center gap-1 text-xs">
                          <XCircle className="h-3 w-3" />
                          Not Validated
                        </Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 sm:gap-2 text-xs sm:text-sm">
                      <div>
                        <span className="text-[#6d7175] dark:text-[#8c9196]">HS Code:</span>{' '}
                        <span className="text-[#202223] dark:text-[#e3e3e3] font-medium">{formatHSCode(item.hs_code)}</span>
                      </div>
                      <div>
                        <span className="text-[#6d7175] dark:text-[#8c9196]">UOM:</span>{' '}
                        <span className="text-[#202223] dark:text-[#e3e3e3]">
                          {item.default_uom ? (uoms.find(u => u.code === item.default_uom)?.name || item.default_uom) : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#6d7175] dark:text-[#8c9196]">Tax Rate:</span>{' '}
                        <span className="text-[#202223] dark:text-[#e3e3e3]">{item.default_rate || 'N/A'}%</span>
                      </div>
                      <div>
                        <span className="text-[#6d7175] dark:text-[#8c9196]">Transaction Type:</span>{' '}
                        <span className="text-[#202223] dark:text-[#e3e3e3]">
                          {item.transaction_type ? (transactionTypes.find(t => t.code === item.transaction_type)?.name || item.transaction_type) : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-xs sm:text-sm">
                      <span className="text-[#6d7175] dark:text-[#8c9196]">Description:</span>{' '}
                      <span className="text-[#202223] dark:text-[#e3e3e3]">{item.product_description}</span>
                    </div>
                    {(item.sro_schedule_no || item.sro_item_serial_no) && (
                      <div className="mt-2 text-xs sm:text-sm">
                        {item.sro_schedule_no && (
                          <span className="text-[#6d7175] dark:text-[#8c9196]">
                            SRO Schedule: <span className="text-[#202223] dark:text-[#e3e3e3]">{item.sro_schedule_no}</span>
                          </span>
                        )}
                        {item.sro_schedule_no && item.sro_item_serial_no && ' | '}
                        {item.sro_item_serial_no && (
                          <span className="text-[#6d7175] dark:text-[#8c9196]">
                            SRO Item Serial: <span className="text-[#202223] dark:text-[#e3e3e3]">{item.sro_item_serial_no}</span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col sm:flex-row gap-1 sm:gap-2 flex-shrink-0">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(item)}
                      className="h-8 w-8 sm:h-9 sm:w-9"
                    >
                      <Edit2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDeleteItem(item.id)}
                      className="h-8 w-8 sm:h-9 sm:w-9"
                    >
                      <Trash2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
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
