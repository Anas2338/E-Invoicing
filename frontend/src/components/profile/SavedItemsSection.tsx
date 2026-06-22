'use client';

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { api } from '@/lib/api';
import { masterDataService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { Plus, Trash2, Edit2, CheckCircle, XCircle, Package, Loader2, Search, X, Upload } from 'lucide-react';

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

export interface SavedItemsSectionHandle {
  openAddForm: () => void;
  downloadTemplate: () => Promise<void>;
  triggerFileUpload: () => void;
}

interface SavedItemsSectionProps {
  hideHeaderActions?: boolean;
}

const SavedItemsSection = forwardRef<SavedItemsSectionHandle, SavedItemsSectionProps>(
  function SavedItemsSection({ hideHeaderActions = false }, ref) {
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
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [focusedCardId, setFocusedCardId] = useState<number | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useImperativeHandle(ref, () => ({
    openAddForm: handleOpenAddForm,
    downloadTemplate: handleDownloadTemplate,
    triggerFileUpload: () => document.getElementById('excel-upload')?.click(),
  }));

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

  // HS Code autocomplete state
  const [hsCodeOptions, setHsCodeOptions] = useState<{ code: string; description: string }[]>([]);
  const [hsCodeSearchOpen, setHsCodeSearchOpen] = useState(false);
  const [hsCodeHighlightIndex, setHsCodeHighlightIndex] = useState(-1);
  const [hsCodeSearching, setHsCodeSearching] = useState(false);
  const hsCodeSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hsCodeDropdownRef = useRef<HTMLDivElement>(null);

  // HS Code → UOM filtered options state
  const [hsCodeUoms, setHsCodeUoms] = useState<UOM[]>([]);
  const [hsCodeUomsLoading, setHsCodeUomsLoading] = useState(false);

  // Transaction Type → Tax Rate filtered options state
  const [taxRateOptions, setTaxRateOptions] = useState<{ rate: string; name: string }[]>([]);
  const [taxRatesLoading, setTaxRatesLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  // Fetch tax rates when transaction type changes
  useEffect(() => {
    if (!transactionType || transactionTypes.length === 0) {
      setTaxRateOptions([]);
      return;
    }

    const fetchTaxRates = async () => {
      try {
        setTaxRatesLoading(true);
        // Find the transaction type code from the name
        const tt = transactionTypes.find(
          (t) => t.name === transactionType || t.code === transactionType
        );
        if (tt) {
          const rates = await masterDataService.getTaxRatesByTransactionType(tt.code);
          if (rates && rates.length > 0) {
            setTaxRateOptions(rates);
            // Auto-select first rate if only one
            if (rates.length === 1) {
              setDefaultRate(rates[0].rate);
            }
            return;
          }
        }
        setTaxRateOptions([]);
      } catch {
        setTaxRateOptions([]);
      } finally {
        setTaxRatesLoading(false);
      }
    };

    fetchTaxRates();
  }, [transactionType, transactionTypes]);

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

  const searchHSCodes = (query: string) => {
    if (hsCodeSearchRef.current) {
      clearTimeout(hsCodeSearchRef.current);
    }
    if (!query || query.trim().length === 0) {
      setHsCodeOptions([]);
      setHsCodeSearchOpen(false);
      return;
    }
    hsCodeSearchRef.current = setTimeout(async () => {
      try {
        setHsCodeSearching(true);
        const results = await masterDataService.getHSCodes(query.trim(), 15);
        setHsCodeOptions(results);
        setHsCodeHighlightIndex(-1);
        setHsCodeSearchOpen(results.length > 0);
      } catch {
        setHsCodeOptions([]);
        setHsCodeSearchOpen(false);
      } finally {
        setHsCodeSearching(false);
      }
    }, 250);
  };

  const selectHsCode = async (code: string) => {
    setHsCode(code);
    setHsCodeOptions([]);
    setHsCodeSearchOpen(false);
    setHsCodeHighlightIndex(-1);
    validateHSCode(code);

    // Fetch relevant UOMs for this HS code
    if (code && code.trim()) {
      try {
        setHsCodeUomsLoading(true);
        setDefaultUom(''); // Reset UOM while loading
        const uoms = await masterDataService.getHsUom(code.trim(), 3);
        if (uoms && uoms.length > 0) {
          setHsCodeUoms(uoms);
          // Auto-select first UOM if only one
          if (uoms.length === 1) {
            setDefaultUom(uoms[0].name);
          }
        } else {
          // No HS-specific UOMs — fall back to all UOMs
          setHsCodeUoms([]);
        }
      } catch {
        setHsCodeUoms([]);
      } finally {
        setHsCodeUomsLoading(false);
      }
    } else {
      setHsCodeUoms([]);
    }

    // Auto-focus the next field (Product Description)
    setTimeout(() => {
      document.getElementById('productDescription')?.focus();
    }, 100);
  };

  const handleHsCodeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!hsCodeSearchOpen || hsCodeOptions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHsCodeHighlightIndex((prev) =>
        prev < hsCodeOptions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHsCodeHighlightIndex((prev) =>
        prev > 0 ? prev - 1 : hsCodeOptions.length - 1
      );
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (hsCodeHighlightIndex >= 0 && hsCodeHighlightIndex < hsCodeOptions.length) {
        selectHsCode(hsCodeOptions[hsCodeHighlightIndex].code);
      }
    } else if (e.key === 'Escape') {
      setHsCodeSearchOpen(false);
      setHsCodeHighlightIndex(-1);
    }
  };

  const getDefaultTransactionType = () => {
    if (transactionTypes.length === 0) return '';
    return transactionTypes[0].name;
  };

  const getNextItemCode = (): string => {
    if (items.length === 0) return 'ITEM-001';

    // Group codes by their prefix (non-numeric part before trailing digits)
    const prefixCounts: Record<string, { maxNum: number; count: number }> = {};
    for (const item of items) {
      const code = item.item_code?.trim();
      if (!code) continue;
      const match = code.match(/^(.+?)(\d+)$/);
      if (!match) continue;
      const prefix = match[1];
      const num = parseInt(match[2], 10);
      if (!prefixCounts[prefix]) {
        prefixCounts[prefix] = { maxNum: num, count: 1 };
      } else {
        if (num > prefixCounts[prefix].maxNum) prefixCounts[prefix].maxNum = num;
        prefixCounts[prefix].count++;
      }
    }

    // Use the most frequently used prefix, or fall back to ITEM-
    const prefixes = Object.keys(prefixCounts);
    if (prefixes.length === 0) return 'ITEM-001';

    const bestPrefix = prefixes.reduce((a, b) =>
      prefixCounts[a].count >= prefixCounts[b].count ? a : b
    );

    const nextNum = prefixCounts[bestPrefix].maxNum + 1;
    const padLength = String(prefixCounts[bestPrefix].maxNum).length;
    return `${bestPrefix}${String(nextNum).padStart(padLength, '0')}`;
  };

  const handleOpenAddForm = () => {
    setTransactionType(getDefaultTransactionType());
    setItemCode(getNextItemCode());
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
    setHsCodeOptions([]);
    setHsCodeSearchOpen(false);
    setHsCodeHighlightIndex(-1);
    setHsCodeUoms([]);
    setHsCodeUomsLoading(false);
    setTaxRateOptions([]);
    setTaxRatesLoading(false);
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
      setDeletingId(id);
      await api.auth.deleteSavedProduct(id);
      toast.success('Item deleted successfully');
      await loadData();
    } catch (error: any) {
      console.error('Error deleting item:', error);
      toast.error(error.message || 'Failed to delete item');
    } finally {
      setDeletingId(null);
    }
  };

  const startEdit = async (item: SavedItem) => {
    setEditingItem(item);
    setItemCode(item.item_code);
    setItemName(item.item_name);
    setHsCode(item.hs_code);
    setHsCodeValid(item.fbr_validated);
    setHsCodeError('');
    setProductDescription(item.product_description);
    setDefaultUom(item.default_uom || '');
    setDefaultRate(item.default_rate || '');
    const ttName = transactionTypes.find(t => t.code === item.transaction_type)?.name || item.transaction_type || '';
    setTransactionType(ttName);
    setSroScheduleNo(item.sro_schedule_no || '');
    setSroItemSerialNo(item.sro_item_serial_no || '');
    setShowAddForm(true);

    // Pre-fetch HS Code UOMs for editing
    if (item.hs_code && item.hs_code.trim()) {
      try {
        setHsCodeUomsLoading(true);
        const uoms = await masterDataService.getHsUom(item.hs_code.trim(), 3);
        if (uoms && uoms.length > 0) {
          setHsCodeUoms(uoms);
        }
      } catch {
        // Keep all UOMs as fallback
      } finally {
        setHsCodeUomsLoading(false);
      }
    }

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
      <div className="flex-1 flex flex-col items-center justify-center min-h-[70vh] px-4">
        <Loader2 className="h-14 w-14 animate-spin text-[#008060] dark:text-[#00a876] mb-6" />
        <p className="text-xl font-semibold text-neutral-700 dark:text-neutral-300">
          Loading saved items...
        </p>
        <p className="text-base text-neutral-500 dark:text-neutral-400 mt-2">
          Please wait while we fetch your products
        </p>
      </div>
    );
  }

  return (
    <>
      <style>{`
        input[type="number"]::-webkit-outer-spin-button,
        input[type="number"]::-webkit-inner-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        input[type="number"] {
          -moz-appearance: textfield;
        }
        @keyframes borderTravel {
          0% { background-position: 0% 0%, 0% 0%; }
          25% { background-position: 0% 0%, 100% 0%; }
          50% { background-position: 0% 0%, 100% 100%; }
          75% { background-position: 0% 0%, 0% 100%; }
          100% { background-position: 0% 0%, 0% 0%; }
        }
        .glow-border:focus {
          border: 2px solid transparent !important;
          outline: none !important;
          box-shadow: none !important;
          background-image:
            linear-gradient(#ffffff, #ffffff),
            linear-gradient(135deg, #60a5fa, #2563eb);
          background-origin: border-box;
          background-clip: padding-box, border-box;
          background-repeat: no-repeat, no-repeat;
          background-size: 100% 100%, 16px 16px;
          animation: borderTravel 2.5s linear infinite;
        }
        html.dark .glow-border:focus {
          background-image:
            linear-gradient(#1e1e1e, #1e1e1e),
            linear-gradient(135deg, #93c5fd, #3b82f6);
        }
      `}</style>
    
      {uploadResults && (
        <div className="mb-6 p-4 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-neutral-50 dark:bg-neutral-900 shadow-sm">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-3">
            Upload Results
          </h3>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-neutral-700 dark:text-neutral-300">
                Successfully uploaded: <strong>{uploadResults.success_count}</strong> items
              </span>
            </div>
            {uploadResults.error_count > 0 && (
              <>
                <div className="flex items-center gap-2 text-sm">
                  <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  <span className="text-neutral-700 dark:text-neutral-300">
                    Failed: <strong>{uploadResults.error_count}</strong> items
                  </span>
                </div>
                {uploadResults.errors.length > 0 && (
                  <div className="mt-3 p-3 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50 rounded-lg">
                    <p className="text-xs font-semibold text-red-800 dark:text-red-400 mb-2">
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
              className="mt-3 h-8 text-xs border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300"
            >
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {uploading && (
        <div className="mb-6 p-4 border border-blue-200 dark:border-blue-900 rounded-xl bg-blue-50 dark:bg-blue-950/30 shadow-sm flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
            Uploading items...
          </span>
        </div>
      )}

      {showAddForm && (
        <>
          <div
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={resetForm}
          />
          <div className="fixed inset-0 z-[60] flex items-start justify-center pt-2 sm:pt-10 overflow-y-auto">
            <div
              className="relative w-[95vw] max-w-2xl bg-white dark:bg-[#161616] rounded-2xl shadow-2xl border-2 border-black dark:border-[#2e2e2e] mb-10"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e2e] bg-blue-100 rounded-t-xl">
                <h4 className="text-base sm:text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">
                  {editingItem ? 'Edit Item' : 'Add New Saved Item'}
                </h4>
                <button
                  type="button"
                  onClick={resetForm}
                  className="p-2 rounded-lg hover:bg-[#f3f4f6] dark:hover:bg-[#2e2e2e] text-[#6d7175] transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form ref={formRef} onSubmit={editingItem ? handleEditItem : handleAddItem}>
                <div className="p-4 sm:p-6 max-h-[70vh] sm:max-h-[80vh] overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <Label htmlFor="itemCode">Item Code *</Label>
                    <Input
                      id="itemCode"
                      type="text"
                      value={itemCode}
                      onChange={(e) => setItemCode(e.target.value)}
                      placeholder="e.g., ITEM-001"
                      className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="itemName">Item Name *</Label>
                    <Input
                      id="itemName"
                      type="text"
                      value={itemName}
                      onChange={(e) => setItemName(e.target.value)}
                      placeholder="e.g., Laptop Computer"
                      className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                      required
                    />
                  </div>

                  <div ref={hsCodeDropdownRef}>
                    <Label htmlFor="hsCode" className="flex items-center gap-2">
                      HS Code *
                      {hsCodeValid === true && (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      )}
                      {hsCodeValid === false && (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                    </Label>
                    <div className="relative">
                      <Input
                        id="hsCode"
                        type="text"
                        value={hsCode}
                        onChange={(e) => {
                          setHsCode(e.target.value);
                          setHsCodeValid(null);
                          setHsCodeError('');
                          setHsCodeUoms([]);
                          setDefaultUom('');
                          searchHSCodes(e.target.value);
                        }}
                        onFocus={() => {
                          if (hsCodeOptions.length > 0) setHsCodeSearchOpen(true);
                        }}
                        onBlur={() => {
                          setTimeout(() => {
                            setHsCodeSearchOpen(false);
                            setHsCodeOptions([]);
                          }, 200);
                          if (hsCode.trim()) validateHSCode(hsCode);
                        }}
                        onKeyDown={handleHsCodeKeyDown}
                        placeholder="Type to search HS Code..."
                        className="mt-1 pr-10 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                        autoComplete="off"
                        required
                      />
                      <div className="absolute right-3 top-1/2 -translate-y-1/2 mt-0.5 pointer-events-none">
                        {(validatingHSCode || hsCodeSearching) && (
                          <Loader2 className="h-4 w-4 animate-spin text-[#008060]" />
                        )}
                      </div>
                      {hsCodeSearchOpen && hsCodeOptions.length > 0 && (
                        <div className="absolute left-0 right-0 top-full mt-1 z-[70] bg-white dark:bg-[#1e1e1e] border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                          {hsCodeOptions.map((opt, idx) => (
                            <button
                              key={opt.code}
                              type="button"
                              className={`w-full text-left px-3 py-1.5 flex items-start gap-2 transition-colors ${
                                idx === hsCodeHighlightIndex
                                  ? 'bg-[#008060]/10 text-[#008060] dark:bg-[#008060]/20 dark:text-[#00a876]'
                                  : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                              }`}
                              onMouseDown={(e) => {
                                e.preventDefault();
                                selectHsCode(opt.code);
                              }}
                              onMouseEnter={() => setHsCodeHighlightIndex(idx)}
                            >
                              <span className="font-mono text-[12px] font-semibold shrink-0">{opt.code}</span>
                              <span className="text-[11px] text-neutral-500 dark:text-neutral-400 leading-tight">
                                {opt.description || ''}
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {hsCodeError && (
                      <p className="text-xs text-red-600 mt-1">{hsCodeError}</p>
                    )}
                    {hsCodeValid === true && (
                      <p className="text-xs text-green-600 mt-1">
                        HS Code validated against FBR database
                      </p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="productDescription">Product Description *</Label>
                    <Input
                      id="productDescription"
                      type="text"
                      value={productDescription}
                      onChange={(e) => setProductDescription(e.target.value)}
                      placeholder="Enter product description"
                      className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                      required
                    />
                  </div>

                  <div className="w-full">
                    <Label htmlFor="defaultUom">
                      Unit of Measurement *
                      {hsCodeUomsLoading && (
                        <Loader2 className="inline h-3 w-3 ml-1 animate-spin text-[#008060]" />
                      )}
                    </Label>
                    <Select value={defaultUom} onValueChange={setDefaultUom}>
                      <SelectTrigger className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] glow-border">
                        {hsCodeUomsLoading ? (
                          <span className="text-muted-foreground">Loading UOMs for HS Code...</span>
                        ) : defaultUom ? (
                          <span>{defaultUom}</span>
                        ) : (
                          <span className="text-muted-foreground">Select UOM</span>
                        )}
                      </SelectTrigger>
                      <SelectContent>
                        {(hsCodeUomsLoading
                          ? []  // Show nothing while loading
                          : hsCode
                            ? hsCodeUoms  // HS code entered: show only its UOMs
                            : uoms  // No HS code yet: show all UOMs
                        ).map((uom) => (
                          <SelectItem key={uom.code} value={uom.name}>
                            {uom.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {hsCode && hsCodeUoms.length > 0 && (
                      <p className="text-xs text-green-600 mt-1">
                        {hsCodeUoms.length} UOM(s) found for this HS Code
                      </p>
                    )}
                  </div>

                  <div className="w-full">
                    <Label htmlFor="transactionType">Transaction Type *</Label>
                    <Select value={transactionType} onValueChange={(value) => {
                      if (value !== transactionType) {
                        setTransactionType(value);
                        setDefaultRate('');
                        setTaxRateOptions([]);
                      }
                    }}>
                      <SelectTrigger className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] glow-border">
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

                  <div className="w-full">
                    <Label htmlFor="defaultRate">
                      Tax Rate *
                      {taxRatesLoading && (
                        <Loader2 className="inline h-3 w-3 ml-1 animate-spin text-[#008060]" />
                      )}
                    </Label>
                    {taxRateOptions.length > 0 ? (
                      <Select value={defaultRate} onValueChange={setDefaultRate}>
                        <SelectTrigger className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] glow-border">
                          {defaultRate ? (
                            <span>{taxRateOptions.find(r => r.rate === defaultRate)?.name || defaultRate}</span>
                          ) : (
                            <span className="text-muted-foreground">Select tax rate</span>
                          )}
                        </SelectTrigger>
                        <SelectContent>
                          {taxRateOptions.map((rate) => (
                            <SelectItem key={rate.rate} value={rate.rate}>
                              {rate.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        id="defaultRate"
                        type="text"
                        value={defaultRate}
                        onChange={(e) => setDefaultRate(e.target.value)}
                        placeholder={taxRatesLoading ? 'Loading tax rates...' : 'e.g., 18'}
                        className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                        disabled={taxRatesLoading}
                        required
                      />
                    )}
                    {transactionType && taxRateOptions.length > 0 && (
                      <p className="text-xs text-green-600 mt-1">
                        {taxRateOptions.length} rate(s) for this transaction type
                      </p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="sroScheduleNo">SRO Schedule No (Optional)</Label>
                    <Input
                      id="sroScheduleNo"
                      type="text"
                      value={sroScheduleNo}
                      onChange={(e) => setSroScheduleNo(e.target.value)}
                      placeholder="Enter SRO schedule number"
                      className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                    />
                  </div>

                  <div>
                    <Label htmlFor="sroItemSerialNo">SRO Item Serial No (Optional)</Label>
                    <Input
                      id="sroItemSerialNo"
                      type="text"
                      value={sroItemSerialNo}
                      onChange={(e) => setSroItemSerialNo(e.target.value)}
                      placeholder="Enter SRO item serial number"
                      className="mt-1 text-xs sm:text-[12px] h-10 sm:h-[30px] w-full glow-border"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e] col-span-1 sm:col-span-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={resetForm}
                      disabled={saving}
                      className="h-8 w-8 text-red-500 hover:text-red-600 border-red-300 dark:border-red-800 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <X className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    </Button>
                    <Button
                      type="submit"
                      variant="outline"
                      size="icon"
                      disabled={saving}
                      className="h-8 w-8 rounded-lg border-blue-300 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      {saving ? (
                        <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 animate-spin" />
                      ) : (
                        <Plus className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </>
      )}

      {items.length > 0 && !showAddForm && (
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4 pb-4 sm:pb-5 border-b border-neutral-100 dark:border-neutral-900 mt-5 pl-1 ">
        <div className="relative flex-1 w-full sm:max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          <Input
            type="text"
            placeholder="Search stored products by name..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyPress={handleSearchKeyPress}
            className="pl-10 h-full border-neutral-200 dark:border-neutral-800 focus:border-neutral-400 dark:focus:border-neutral-600 rounded-lg text-sm transition-all w-full"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            onClick={handleSearch}
            size="sm"
            className="h-10 px-4 bg-neutral-900 hover:bg-neutral-800 text-white dark:bg-neutral-100 dark:hover:bg-neutral-200 dark:text-neutral-900 font-medium rounded-lg shadow-sm transition-all text-xs"
          >
            Search
          </Button>
          {searchQuery && (
            <Button
              onClick={handleClearSearch}
              size="sm"
              variant="outline"
              className="h-10 px-4 border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400 rounded-lg text-xs"
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
              className="h-10 px-4 font-medium rounded-lg text-xs shadow-sm flex items-center gap-2"
            >
              {isDeleting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Remove ({selectedItems.length})
            </Button>
          )}
        </div>
      </div>
      )}

      {!loading && items.length === 0 && !showAddForm && (
        <div className="flex-1 flex flex-col items-center justify-center min-h-[70vh] px-4">
          <div className="w-28 h-28 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-6">
            <Package className="h-14 w-14 text-neutral-400 dark:text-neutral-500" />
          </div>
          <h3 className="text-2xl font-bold text-neutral-700 dark:text-neutral-300 mb-3">
            No saved items yet
          </h3>
          <p className="text-base text-neutral-500 dark:text-neutral-400 text-center max-w-md mb-8">
            Add your first product by clicking the + button, or upload multiple items using the Excel template.
          </p>
          <div className="flex items-center gap-4">
            <Button
              size="default"
              onClick={() => document.getElementById('excel-upload')?.click()}
              variant="outline"
              className="h-11 px-6 text-sm border-green-300 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-950/30"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload Excel
            </Button>
            <Button
              size="default"
              onClick={handleOpenAddForm}
              className="h-11 px-6 text-sm bg-[#008060] hover:bg-[#006e52] text-white"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Item
            </Button>
          </div>
        </div>
      )}

      {items.length > 0 && !showAddForm && (
        <Card className='overflow-y-auto overflow-x-hidden min-h-[350px] h-[calc(100vh-15rem)] sm:h-[470px] md:h-[500px] lg:h-[550px]'>
          <CardContent className="p-3 sm:p-3">
            {/* <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4 pb-4 sm:pb-5 border-b border-neutral-100 dark:border-neutral-900">
              <div className="relative flex-1 w-full sm:max-w-md">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
                <Input
                  type="text"
                  placeholder="Search stored products by name..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyPress={handleSearchKeyPress}
                  className="pl-10 h-full border-neutral-200 dark:border-neutral-800 focus:border-neutral-400 dark:focus:border-neutral-600 rounded-lg text-sm transition-all w-full"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  onClick={handleSearch}
                  size="sm"
                  className="h-10 px-4 bg-neutral-900 hover:bg-neutral-800 text-white dark:bg-neutral-100 dark:hover:bg-neutral-200 dark:text-neutral-900 font-medium rounded-lg shadow-sm transition-all text-xs"
                >
                  Search
                </Button>
                {searchQuery && (
                  <Button
                    onClick={handleClearSearch}
                    size="sm"
                    variant="outline"
                    className="h-10 px-4 border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400 rounded-lg text-xs"
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
                    className="h-10 px-4 font-medium rounded-lg text-xs shadow-sm flex items-center gap-2"
                  >
                    {isDeleting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                    Remove ({selectedItems.length})
                  </Button>
                )}
              </div>
            </div> */}

            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 py-3.5 text-xs text-neutral-500 dark:text-neutral-400">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="selectAll"
                  checked={filteredItems.length > 0 && selectedItems.length === filteredItems.length}
                  onCheckedChange={handleSelectAll}
                  className="border-neutral-300 dark:border-neutral-700 data-[state=checked]:bg-neutral-900 dark:data-[state=checked]:bg-neutral-100"
                />
                <label htmlFor="selectAll" className="cursor-pointer font-medium select-none">
                  Select All Items ({filteredItems.length})
                </label>
              </div>
              {selectedItems.length > 0 && (
                <span className="font-semibold text-neutral-900 dark:text-neutral-100 bg-neutral-100 dark:bg-neutral-900 px-2 py-0.5 rounded whitespace-nowrap">
                  {selectedItems.length} checked
                </span>
              )}
            </div>

            {/* Main grid of cards containing only requested fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mt-2">
              {filteredItems.map((item) => {
                const isChecked = selectedItems.includes(item.id);
                return (
                  <div
                    key={item.id}
                    tabIndex={0}
                    onFocus={() => setFocusedCardId(item.id)}
                    onBlur={(e) => {
                      if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                        setFocusedCardId(null);
                      }
                    }}
                    // className={`"group relative p-3 sm:p-5 rounded-xl border-2 border-blue-600 bg-blue-50 flex flex-col justify-between transition-all duration-300 shadow-[0_10px_20px_-5px_rgba(124,58,237,0.35)] hover:-translate-y-2 hover:shadow-[0_20px_40px_-8px_rgba(124,58,237,0.45)] ${isChecked ? 'ring-1 ring-neutral-400 dark:ring-neutral-600 border-transparent ' : ''}`}
                      className={`relative overflow-hidden rounded-2xl border border-blue-400 bg-gradient-to-br from-white via-blue-50 to-blue-100 p-4 sm:p-6 flex flex-col justify-between transition-all duration-300 ease-out focus-visible:outline-none
                        translate-y-[-2px]
                        hover:-translate-y-3 hover:scale-[1.02] hover:shadow-[0_8px_12px_rgba(0,0,0,0.10),0_20px_35px_rgba(59,130,246,0.18),0_36px_60px_rgba(124,58,237,0.28)]
                        ${
                          focusedCardId === item.id
                            ? "-translate-y-3 scale-[1.02] shadow-[0_8px_12px_rgba(0,0,0,0.10),0_20px_35px_rgba(59,130,246,0.18),0_36px_60px_rgba(124,58,237,0.28)]"
                            : ""
                        }
                        ${
                          isChecked
                            ? "ring-2 ring-blue-500 border-blue-500"
                            : ""
                        }`}
                      >
                    {/* Top Action Layer & Main Codes Header */}
                    <div className="flex flex-col items-start justify-between gap-3 sm:gap-4 pb-2.5 sm:pb-3">
                      <div className='flex items-center justify-between w-full'>
                        <div className='flex items-center gap-2'>
                          <Checkbox
                            checked={isChecked}
                            onCheckedChange={() => handleSelectItem(item.id)}
                            className="mt-1 border-neutral-300 data-[state=checked]:bg-neutral-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
                          />
                          <div>
                            <div className="text-center">
                              {/* <span className="text-[10px] font-bold tracking-wider text-neutral-500 uppercase block">
                                Item Code
                              </span> */}
                              <span className="px-3 py-1.5 rounded-full text-xs font-medium text-white
                                bg-emerald-600 hover:bg-emerald-700
                                transition-all duration-200 ease-out transform
                                shadow-[0_2px_0_rgba(4,120,87,0.9),0_6px_14px_rgba(0,0,0,0.12)]
                                hover:-translate-y-0.5
                                hover:shadow-[0_3px_0_rgba(4,120,87,0.9),0_10px_20px_rgba(0,0,0,0.18)]
                                active:translate-y-0
                                active:shadow-[0_1px_0_rgba(4,120,87,0.9),0_4px_10px_rgba(0,0,0,0.12)]
                                focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-1">
                                {item.item_code}
                              </span>
                            </div>

                            {/* <span className="text-[10px] font-bold tracking-wider text-neutral-500 uppercase">
                              Item Name:
                            </span> */}
                            {/* <div className="text-sm sm:text-base font-bold text-black">
                              {item.item_name}
                            </div> */}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => startEdit(item)}
                            className="p-1.5 rounded-lg hover:bg-neutral-100 border border-grey-200 text-neutral-500 dark:text-neutral-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            title="Edit Item"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            disabled={deletingId === item.id}
                            className="p-1.5 rounded-lg hover:bg-red-50 border border-red-300 text-red-500 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                            title="Delete Item"
                          >
                            {deletingId === item.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>

                        {/* <div className="flex items-center gap-1">
                          <button
                            onClick={() => startEdit(item)}
                            className="p-1.5 rounded-lg hover:bg-neutral-100 border border-grey-200 text-neutral-500 dark:text-neutral-400 transition-colors"
                            title="Edit Item"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            disabled={deletingId === item.id}
                            className="p-1.5 rounded-lg hover:bg-red-50 border border-red-300 text-red-500 transition-colors disabled:opacity-50"
                            title="Delete Item"
                          >
                            {deletingId === item.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div> */}
                      </div>
                      <div className="flex justify-between w-full min-w-0 flex-wrap gap-2">
                        <div className="text-sm sm:text-base font-bold text-black">
                            {item.item_name}
                          </div>
                        {/* <div className="text-center"> */}
                          {/* <span className="text-[10px] font-bold tracking-wider text-neutral-500 uppercase block">
                            Item Code
                          </span> */}
                          {/* <span className="px-3 py-1.5 rounded-full text-xs font-medium text-white
                            bg-emerald-600 hover:bg-emerald-700                         
                            transition-all duration-200 ease-out transform                          
                            shadow-[0_2px_0_rgba(4,120,87,0.9),0_6px_14px_rgba(0,0,0,0.12)]                        
                            hover:-translate-y-0.5
                            hover:shadow-[0_3px_0_rgba(4,120,87,0.9),0_10px_20px_rgba(0,0,0,0.18)]                       
                            active:translate-y-0
                            active:shadow-[0_1px_0_rgba(4,120,87,0.9),0_4px_10px_rgba(0,0,0,0.12)]                       
                            focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-1">
                            {item.item_code}
                          </span>
                        </div> */}
                        {/* <div className="flex items-center gap-1">
                          <button
                            onClick={() => startEdit(item)}
                            className="p-1.5 rounded-lg hover:bg-neutral-100 border border-grey-200 text-neutral-500 dark:text-neutral-400 transition-colors"
                            title="Edit Item"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            disabled={deletingId === item.id}
                            className="p-1.5 rounded-lg hover:bg-red-50 border border-red-300 text-red-500 transition-colors disabled:opacity-50"
                            title="Delete Item"
                          >
                            {deletingId === item.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div> */}
                        
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hidden file input for Excel upload — triggered programmatically from sidebar */}
      <input
        type="file"
        id="excel-upload"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={handleFileUpload}
      />
    </>
  );
});

export default SavedItemsSection;