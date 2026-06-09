'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Trash2, Plus, Loader2, AlertCircle, Info, Building2, MapPin, FileText, Pencil, Check, X, CheckCircle, Send, Save } from 'lucide-react';
import { masterDataService, fbrIntegrationService, type AllMasterData } from '@/lib/api/api-client';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';

interface InvoiceItem {
  hsCode: string;
  productDescription: string;
  rate: string;
  uoM: string;
  quantity: number;
  totalValues: number;
  valueSalesExcludingST: number;
  fixedNotifiedValueOrRetailPrice: string;
  salesTaxApplicable: number;
  salesTaxWithheldAtSource: string;
  extraTax: number;
  furtherTax: number;
  sroScheduleNo: string;
  fedPayable: number;
  discount: number;
  saleType: string;
  sroItemSerialNo: string;
}

interface SaleInvoiceFormProps {
  onSubmit: (data: any) => void;
  onCancel: () => void;
  isLoading?: boolean;
  isSubmitting?: boolean;
  initialData?: any;
  isEditMode?: boolean;
}

export function SaleInvoiceForm({
  onSubmit,
  onCancel,
  isLoading,
  isSubmitting,
  initialData,
  isEditMode = false
}: SaleInvoiceFormProps) {
  const router = useRouter();

  // Master data state
  const [masterData, setMasterData] = useState<AllMasterData | null>(null);
  const [masterDataLoading, setMasterDataLoading] = useState(true);
  const [masterDataError, setMasterDataError] = useState<string | null>(null);

  // Buyer verification state
  const [isVerifyingBuyer, setIsVerifyingBuyer] = useState(false);
  const [buyerVerificationMessage, setBuyerVerificationMessage] = useState<string | null>(null);

  // Invoice header state
  const [invoiceNo, setInvoiceNo] = useState('');
  const [invoiceType, setInvoiceType] = useState<'Sale Invoice' | 'Debit Note'>('Sale Invoice');
  const todayKarachi = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Karachi' });
  const [invoiceDate, setInvoiceDate] = useState(isEditMode ? '' : todayKarachi);
  const [invoiceRefNo, setInvoiceRefNo] = useState('');
  const [scenarioId, setScenarioId] = useState('SN001');
  const [environment, setEnvironment] = useState<'SANDBOX' | 'PRODUCTION'>('SANDBOX');
  const [transactionTypeId, setTransactionTypeId] = useState<string>('');

  // Seller information state
  const [sellerNTNCNIC, setSellerNTNCNIC] = useState('');
  const [sellerBusinessName, setSellerBusinessName] = useState('');
  const [sellerProvince, setSellerProvince] = useState('');
  const [sellerProvinceCode, setSellerProvinceCode] = useState('');
  const [sellerAddress, setSellerAddress] = useState('');

  // Buyer information state
  const [buyerNTNCNIC, setBuyerNTNCNIC] = useState('');
  const [buyerBusinessName, setBuyerBusinessName] = useState('');
  const [buyerProvince, setBuyerProvince] = useState('');
  const [buyerProvinceCode, setBuyerProvinceCode] = useState('');
  const [buyerAddress, setBuyerAddress] = useState('');
  const [buyerRegistrationType, setBuyerRegistrationType] = useState<'Registered' | 'Unregistered'>('Registered');

  // Saved buyers state for autocomplete
  const [savedBuyers, setSavedBuyers] = useState<Array<any>>([]);
  const [buyerSearchResults, setBuyerSearchResults] = useState<Array<any>>([]);
  const [showBuyerSuggestions, setShowBuyerSuggestions] = useState(false);
  const [buyerHighlightedIndex, setBuyerHighlightedIndex] = useState(-1);
  const [loadingSavedBuyers, setLoadingSavedBuyers] = useState(false);

  // Income Tax state
  const [incomeTax, setIncomeTax] = useState<'236G' | '236H'>('236G');

  // Invoice items state
  const [items, setItems] = useState<InvoiceItem[]>([]);

  // Saved items state
  const [savedItems, setSavedItems] = useState<Array<any>>([]);
  const [selectedSavedItems, setSelectedSavedItems] = useState<{ [key: number]: string }>({});
  const [loadingSavedData, setLoadingSavedData] = useState(false);
  const [manualFurtherTax, setManualFurtherTax] = useState<Set<number>>(new Set());

  // Item modal state
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null);
  // Temporary item state for the modal form
  const [modalItem, setModalItem] = useState<InvoiceItem>({
    hsCode: '',
    productDescription: '',
    rate: '',
    uoM: 'NOS',
    quantity: 1,
    totalValues: 0,
    valueSalesExcludingST: 0,
    fixedNotifiedValueOrRetailPrice: '0',
    salesTaxApplicable: 0,
    salesTaxWithheldAtSource: '0',
    extraTax: 0,
    furtherTax: 0,
    sroScheduleNo: '',
    fedPayable: 0,
    discount: 0,
    saleType: '01',
    sroItemSerialNo: ''
  });
  // Track saved item selection in modal
  const [modalSelectedSavedItem, setModalSelectedSavedItem] = useState<string>('');
  // Item entry mode: 'saved' = select from saved items (auto-fill), 'temporary' = manual entry
  const [itemEntryMode, setItemEntryMode] = useState<'saved' | 'temporary'>('saved');

  // Validate/Post workflow state
  const [isValidating, setIsValidating] = useState(false);
  const [isPosting, setIsPosting] = useState(false);
  const [savedInvoiceId, setSavedInvoiceId] = useState<string | null>(null);
  const [isValidated, setIsValidated] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Validation/Post result dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogData, setDialogData] = useState<{
    success: boolean;
    title: string;
    message: string;
    invoiceNumber?: string;
    fbrNumber?: string;
    errors?: any[];
    invoiceId?: string;
  }>({ success: false, title: '', message: '' });

  // Fetch master data on component mount
  useEffect(() => {
    const fetchMasterData = async () => {
      try {
        setMasterDataLoading(true);
        const data = await masterDataService.getAllMasterData();
        setMasterData(data);

        // Check if FBR-dependent fields are empty (indicates no FBR token configured)
        if (data.provinces.length === 0 || data.uom.length === 0 || data.invoice_types.length === 0) {
          setMasterDataError('Some dropdown options are unavailable. Please configure your FBR credentials in your profile to access all options.');
        } else {
          setMasterDataError(null);
        }
      } catch (error) {
        console.error('Failed to fetch master data:', error);
        setMasterDataError('Failed to load form options. Please refresh the page.');
      } finally {
        setMasterDataLoading(false);
      }
    };

    fetchMasterData();
  }, []);

  // Fetch saved items on component mount
  useEffect(() => {
    const fetchSavedData = async () => {
      try {
        setLoadingSavedData(true);

        // Fetch saved items (unified products)
        const itemsResponse = await api.auth.getSavedProducts(true);
        setSavedItems(itemsResponse || []);
      } catch (error) {
        console.error('Failed to fetch saved items:', error);
        // Don't show error to user, just log it
      } finally {
        setLoadingSavedData(false);
      }
    };

    fetchSavedData();
  }, []);

  // Fetch buyers from invoice history in background (non-blocking)
  useEffect(() => {
    const fetchBuyers = async () => {
      try {
        setLoadingSavedBuyers(true);
        const buyersResponse = await api.invoices.getBuyersFromHistory();
        setSavedBuyers(buyersResponse || []);
      } catch (error) {
        console.error('Failed to fetch buyers from history:', error);
        // Don't show error to user, just log it
      } finally {
        setLoadingSavedBuyers(false);
      }
    };

    fetchBuyers();
  }, []);

  // Auto-fill seller information from user profile
  useEffect(() => {
    const fetchUserProfile = async () => {
      // Only auto-fill if not in edit mode and masterData is loaded
      if (isEditMode || !masterData) return;

      try {
        const profile = await api.auth.getProfile();

        // Auto-fill seller information from user profile
        if (profile.fbr_seller_ntn) {
          setSellerNTNCNIC(profile.fbr_seller_ntn);
        }
        if (profile.fbr_business_name) {
          setSellerBusinessName(profile.fbr_business_name);
        }
        if (profile.fbr_seller_province) {
          setSellerProvince(profile.fbr_seller_province);

          // Also set the province code by looking it up in masterData
          const province = masterData?.provinces.find(p => p.name === profile.fbr_seller_province);
          if (province) {
            setSellerProvinceCode(province.code);
          }
        }
        if (profile.fbr_seller_address) {
          setSellerAddress(profile.fbr_seller_address);
        }

        // Auto-set environment based on configured FBR tokens
        // Fetch FBR credentials to check which tokens are configured
        try {
          const fbrCredentials = await api.auth.getFbrCredentials();
          const hasSandbox = !!fbrCredentials.fbr_sandbox_token;
          const hasProduction = !!fbrCredentials.fbr_production_token;

          // Logic: If both or only production → PRODUCTION, if only sandbox → SANDBOX
          if (hasProduction) {
            setEnvironment('PRODUCTION');
          } else if (hasSandbox) {
            setEnvironment('SANDBOX');
          }
          // If neither token exists, keep default SANDBOX
        } catch (error) {
          console.error('Failed to fetch FBR credentials:', error);
          // Keep default SANDBOX if fetch fails
        }
      } catch (error) {
        console.error('Failed to fetch user profile:', error);
      }
    };

    fetchUserProfile();
  }, [isEditMode, masterData]);

  // Auto-generate invoice number (only in create mode)
  useEffect(() => {
    const fetchNextInvoiceNumber = async () => {
      // Only auto-generate if NOT in edit mode and invoice number is empty
      if (isEditMode || invoiceNo) return;

      try {
        const response = await api.auth.getNextInvoiceNumber();
        if (response.invoice_number) {
          setInvoiceNo(response.invoice_number);
        }
      } catch (error) {
        console.error('Failed to fetch next invoice number:', error);
        // Fallback to timestamp-based number if API fails
        setInvoiceNo(`INV-${Date.now().toString().slice(-6)}`);
      }
    };

    fetchNextInvoiceNumber();
  }, [isEditMode, invoiceNo]);

  // Populate form with initial data when in edit mode
  useEffect(() => {
    if (isEditMode && initialData) {
      // Populate invoice header
      setInvoiceNo(initialData.external_id || '');
      setInvoiceType(initialData.invoice_type || 'Sale Invoice');
      setInvoiceDate(initialData.invoice_date || '');
      setInvoiceRefNo(initialData.invoice_ref_no || '');
      setScenarioId(initialData.scenario_id || '');
      setEnvironment(initialData.environment || 'SANDBOX');
      setIncomeTax(initialData.income_tax || '236G');

      // Handle transaction_type_id: if empty but items have sale_type, reverse map it
      let resolvedTransactionTypeId = initialData.transaction_type_id || '';

      if (!resolvedTransactionTypeId && initialData.items && initialData.items.length > 0 && masterData) {
        // For transferred invoices: derive transaction_type_id from sale_type
        const firstItemSaleType = initialData.items[0].saleType || initialData.items[0].sale_type;

        if (firstItemSaleType && masterData?.transaction_types) {
          // Check if sale_type is a code (numeric string) - use it directly
          const matchingByCode = masterData.transaction_types.find(
            (t: any) => t.code === firstItemSaleType
          );

          if (matchingByCode) {
            resolvedTransactionTypeId = matchingByCode.code;
          } else {
            // Fallback: try matching by name (for legacy data)
            const matchingByName = masterData.transaction_types.find(
              (t: any) => t.name?.trim() === firstItemSaleType.trim()
            );

            if (matchingByName) {
              resolvedTransactionTypeId = matchingByName.code;
            }
          }
        }
      }

      setTransactionTypeId(resolvedTransactionTypeId);

      // If transaction type exists (either from data or resolved), mark as selected
      if (resolvedTransactionTypeId) {

      }

      // Populate seller information
      setSellerNTNCNIC(initialData.seller_ntn_cnic || '');
      setSellerBusinessName(initialData.seller_business_name || '');
      setSellerProvince(initialData.seller_province || '');
      setSellerAddress(initialData.seller_address || '');

      // Resolve seller province code from masterData
      if (initialData.seller_province && masterData) {
        const province = masterData?.provinces.find(p => p.name === initialData.seller_province);
        if (province) {
          setSellerProvinceCode(province.code);
        }
      }

      // Populate buyer information
      setBuyerNTNCNIC(initialData.buyer_ntn_cnic || '');
      setBuyerBusinessName(initialData.buyer_business_name || '');
      setBuyerProvince(initialData.buyer_province || '');
      setBuyerAddress(initialData.buyer_address || '');
      setBuyerRegistrationType(initialData.buyer_registration_type || 'Registered');

      // Resolve buyer province code from masterData
      if (initialData.buyer_province && masterData) {
        const province = masterData?.provinces.find(p => p.name === initialData.buyer_province);
        if (province) {
          setBuyerProvinceCode(province.code);
        }
      }

      // Populate items
      if (initialData.items && Array.isArray(initialData.items)) {
        setItems(initialData.items.map((item: any) => ({
          hsCode: item.hsCode || item.hs_code || '',
          productDescription: item.productDescription || item.product_description || '',
          rate: item.rate || '18',
          uoM: item.uoM || item.uom || 'NOS',
          quantity: item.quantity || 1,
          totalValues: item.totalValues || item.total_values || 0,
          valueSalesExcludingST: item.valueSalesExcludingST || item.value_sales_excluding_st || 0,
          fixedNotifiedValueOrRetailPrice: String(item.fixedNotifiedValueOrRetailPrice ?? item.fixed_notified_value_or_retail_price ?? '0'),
          salesTaxApplicable: item.salesTaxApplicable || item.sales_tax_applicable || 0,
          salesTaxWithheldAtSource: item.salesTaxWithheldAtSource || item.sales_tax_withheld_at_source?.toString() || '',
          extraTax: item.extraTax || item.extra_tax || 0,
          furtherTax: item.furtherTax || item.further_tax || 0,
          sroScheduleNo: item.sroScheduleNo || item.sro_schedule_no || '',
          fedPayable: item.fedPayable || item.fed_payable || 0,
          discount: item.discount || 0,
          saleType: item.saleType || item.sale_type || '01',
          sroItemSerialNo: item.sroItemSerialNo || item.sro_item_serial_no || ''
        })));

        // Match items against saved items to restore dropdown selection
        if (savedItems.length > 0) {
          const matchedItems: { [key: number]: string } = {};

          initialData.items.forEach((item: any, index: number) => {
            const itemHsCode = (item.hsCode || item.hs_code || '').trim().toLowerCase();
            const itemDescription = (item.productDescription || item.product_description || '').trim().toLowerCase();
            const itemRate = (item.rate || '').toString().trim();

            // Try to find a matching saved item
            const matchedSavedItem = savedItems.find((savedItem: any) => {
              const savedHsCode = (savedItem.hs_code || '').trim().toLowerCase();
              const savedDescription = (savedItem.product_description || '').trim().toLowerCase();
              const savedRate = (savedItem.default_rate || '').toString().trim();

              // Match by HS code and description (primary match)
              return savedHsCode === itemHsCode && savedDescription === itemDescription;
            });

            if (matchedSavedItem) {
              matchedItems[index] = matchedSavedItem.id.toString();
            }
          });

          setSelectedSavedItems(matchedItems);
        }
      }
    }
  }, [isEditMode, initialData, masterData, savedItems]);

  // Verify buyer registration with FBR
  const verifyBuyerRegistration = useCallback(async (ntnCnic: string) => {
    if (!ntnCnic || ntnCnic.length < 7) {
      // Don't verify if NTN/CNIC is too short
      return;
    }

    setIsVerifyingBuyer(true);
    setBuyerVerificationMessage(null);

    try {
      const result = await fbrIntegrationService.verifyBuyer(ntnCnic, environment);

      if (result.success) {
        // Automatically update registration type based on FBR response
        setBuyerRegistrationType(result.registration_type as 'Registered' | 'Unregistered');

        // Show success message
        if (result.is_registered) {
          if (result.business_name) {
            setBuyerVerificationMessage(`✓ Registered: ${result.business_name}`);
          } else {
            setBuyerVerificationMessage('✓ Verified as Registered');
          }
        } else {
          setBuyerVerificationMessage('✓ Verified as Unregistered');
        }
      } else {
        // Show error but don't block the form
        setBuyerVerificationMessage(result.error || 'Could not verify buyer registration');
      }
    } catch (error) {
      // Don't show error if FBR credentials are not configured or authentication failed
      const errorMessage = error instanceof Error ? error.message : String(error);

      // Silently fail for these cases - don't show error to user
      if (errorMessage.includes('FBR access token not configured') ||
          errorMessage.includes('Authentication required') ||
          errorMessage.includes('Unauthorized') ||
          errorMessage.includes('Bad Request') ||
          errorMessage.includes('400')) {
        // User hasn't set up FBR credentials, session expired, or invalid request
        return;
      }

      // Only log to console, don't show error message to user
      console.error('Buyer verification failed:', error);
      // Don't set error message - let user continue without verification
    } finally {
      setIsVerifyingBuyer(false);
    }
  }, [environment]);

  // Debounced buyer NTN/CNIC change handler - DISABLED
  // useEffect(() => {
  //   // Only verify if buyer NTN is provided and has minimum length
  //   if (!buyerNTNCNIC || buyerNTNCNIC.trim().length < 7) {
  //     setBuyerVerificationMessage(null);
  //     return;
  //   }

  //   // Debounce the verification call
  //   const timeoutId = setTimeout(() => {
  //     verifyBuyerRegistration(buyerNTNCNIC);
  //   }, 1000); // Wait 1 second after user stops typing

  //   return () => clearTimeout(timeoutId);
  // }, [buyerNTNCNIC, verifyBuyerRegistration]);

  // Auto-calculate Further Tax for all items when buyer registration type changes
  useEffect(() => {
    setItems(prevItems => {
      return prevItems.map((item, idx) => {
        const valueExclTax = parseFloat(String(item.valueSalesExcludingST)) || 0;
        const salesTax = parseFloat(String(item.salesTaxApplicable)) || 0;
        const discount = Number(item.discount) || 0;

        const extraTax = Number(item.extraTax) || 0;

        if (buyerRegistrationType === 'Unregistered') {
          // Calculate 4% of Value Excl. Sales Tax (skip if user manually set furtherTax)
          if (valueExclTax > 0 && !manualFurtherTax.has(idx)) {
            const furtherTax = valueExclTax * 0.04;
            // Total Value = Value Excl. Tax + Sales Tax + Further Tax + Extra Tax - Discount
            const totalValue = valueExclTax + salesTax + furtherTax + extraTax - discount;
            return {
              ...item,
              furtherTax: parseFloat(furtherTax.toFixed(2)),
              totalValues: parseFloat(totalValue.toFixed(2))
            };
          }
        } else {
          // Clear Further Tax for Registered buyers and recalculate Total Value
          // Total Value = Value Excl. Tax + Sales Tax + Extra Tax - Discount (no Further Tax)
          const totalValue = valueExclTax + salesTax + extraTax - discount;
          return {
            ...item,
            furtherTax: 0,
            totalValues: parseFloat(totalValue.toFixed(2))
          };
        }
        return item;
      });
    });
  }, [buyerRegistrationType, manualFurtherTax]);

  const addItem = () => {
    // Find the transaction type name from the code
    const selectedTransactionType = masterData?.transaction_types.find(t => t.code === transactionTypeId);
    const transactionTypeName = selectedTransactionType?.name?.trim() || 'Goods at standard rate (default)';

    const newItem: InvoiceItem = {
      hsCode: '',
      productDescription: '',
      rate: '',
      uoM: 'NOS',
      quantity: 1,
      totalValues: 0,
      valueSalesExcludingST: 0,
      fixedNotifiedValueOrRetailPrice: '0',
      salesTaxApplicable: 0,
      salesTaxWithheldAtSource: '0',
      extraTax: 0,
      furtherTax: 0,
      sroScheduleNo: '',
      fedPayable: 0,
      discount: 0,
      saleType: transactionTypeName,
      sroItemSerialNo: ''
    };
    setModalItem(newItem);
    setModalSelectedSavedItem('');
    setItemEntryMode('saved');
    setEditingItemIndex(null); // null = adding new
    setIsItemModalOpen(true);
  };

  const openEditModal = (index: number) => {
    setModalItem({ ...items[index] });
    setModalSelectedSavedItem(selectedSavedItems[index] || '');
    setItemEntryMode(selectedSavedItems[index] ? 'saved' : 'temporary');
    setEditingItemIndex(index);
    setIsItemModalOpen(true);
  };

  const handleModalSave = () => {
    // Validate required fields
    if (!modalItem.hsCode.trim()) {
      toast.error('HS Code is required');
      return;
    }
    if (!modalItem.productDescription.trim()) {
      toast.error('Product Description is required');
      return;
    }
    if (!modalItem.rate.trim()) {
      toast.error('Tax Rate is required');
      return;
    }
    if (!modalItem.uoM.trim()) {
      toast.error('Unit of Measurement is required');
      return;
    }
    if (!modalItem.quantity || Number(modalItem.quantity) <= 0) {
      toast.error('Quantity must be greater than 0');
      return;
    }
    if (!modalItem.valueSalesExcludingST || Number(modalItem.valueSalesExcludingST) <= 0) {
      toast.error('Value Excl. Sales Tax is required');
      return;
    }
    if (!modalItem.fixedNotifiedValueOrRetailPrice || modalItem.fixedNotifiedValueOrRetailPrice.trim() === '') {
      toast.error('Fixed/Retail Price is required');
      return;
    }
    if (modalItem.salesTaxWithheldAtSource.trim() === '') {
      toast.error('Sales Tax Withheld is required');
      return;
    }
    if (buyerRegistrationType === 'Unregistered' && String(modalItem.furtherTax ?? '').trim() === '') {
      toast.error('Further Tax is required when buyer is Unregistered');
      return;
    }

    // Restrict non-first items to match the invoice's transaction type
    const isNonFirstItem = (editingItemIndex !== null && editingItemIndex > 0) || (editingItemIndex === null && items.length > 0);
    if (isNonFirstItem && transactionTypeId) {
      const ttName = masterData?.transaction_types.find(t => t.code === transactionTypeId)?.name;
      if (ttName && modalItem.saleType !== ttName) {
        toast.error(`Sale Type must match the invoice's Transaction Type: "${ttName}"`);
        return;
      }
    }

    if (editingItemIndex !== null) {
      // Update existing item — apply all modalItem fields
      const idx = editingItemIndex;
      setItems(prevItems => {
        const updatedItems = [...prevItems];
        updatedItems[idx] = { ...modalItem };
        return updatedItems;
      });
      // If saved item was selected, update that tracking too
      if (modalSelectedSavedItem) {
        setSelectedSavedItems(prev => ({ ...prev, [idx]: modalSelectedSavedItem }));
        // Also handle item select logic for transaction type on item 0
        if (idx === 0) {
          const selectedItem = savedItems.find(si => si.id.toString() === modalSelectedSavedItem);
          if (selectedItem) {
            const ttCode = selectedItem.transaction_type
              ? (masterData?.transaction_types.find(t => t.code === selectedItem.transaction_type)?.code ||
                 masterData?.transaction_types.find(t => t.name === selectedItem.transaction_type)?.code ||
                 selectedItem.transaction_type)
              : '';
            if (ttCode) {
              setTransactionTypeId(ttCode);
      
            }
          }
        }
      }
    } else {
      // Add new item
      setItems(prevItems => [...prevItems, modalItem]);
      if (modalSelectedSavedItem) {
        const newIndex = items.length;
        setSelectedSavedItems(prev => ({ ...prev, [newIndex]: modalSelectedSavedItem }));
        // Handle transaction type for first item
        if (newIndex === 0) {
          const selectedItem = savedItems.find(si => si.id.toString() === modalSelectedSavedItem);
          if (selectedItem) {
            const ttCode = selectedItem.transaction_type
              ? (masterData?.transaction_types.find(t => t.code === selectedItem.transaction_type)?.code ||
                 masterData?.transaction_types.find(t => t.name === selectedItem.transaction_type)?.code ||
                 selectedItem.transaction_type)
              : '';
            if (ttCode) {
              setTransactionTypeId(ttCode);
      
              setItems(prev =>
                prev.map(item => ({ ...item, saleType: selectedItem.transaction_type || item.saleType }))
              );
            }
          }
        }
      }
    }
    setIsItemModalOpen(false);
    setEditingItemIndex(null);
  };

  const handleModalItemSelect = (itemId: string) => {
    const selectedItem = savedItems.find(item => item.id.toString() === itemId);
    if (!selectedItem) return;

    const ttCode = selectedItem.transaction_type
      ? (masterData?.transaction_types.find(t => t.code === selectedItem.transaction_type)?.code ||
         masterData?.transaction_types.find(t => t.name === selectedItem.transaction_type)?.code ||
         selectedItem.transaction_type)
      : '';
    const ttName = selectedItem.transaction_type || '';

    // Validate transaction type for non-first items
    if (editingItemIndex !== null && editingItemIndex > 0 && ttCode && transactionTypeId && ttCode !== transactionTypeId) {
      toast.error(`Cannot select this item. Transaction type mismatch. Please select an item with matching transaction type.`);
      return;
    }

    setModalSelectedSavedItem(itemId);

    const uomCode = selectedItem.default_uom || 'NOS';
    const uomObj = masterData?.uom.find(u => u.code === uomCode);

    setModalItem(prev => ({
      ...prev,
      hsCode: selectedItem.hs_code,
      productDescription: selectedItem.product_description,
      rate: selectedItem.default_rate || '',
      uoM: uomObj?.name || uomCode,
      saleType: ttName || prev.saleType,
      sroScheduleNo: selectedItem.sro_schedule_no || '',
      sroItemSerialNo: selectedItem.sro_item_serial_no || '',
    }));

    toast.success(`Item "${selectedItem.item_name}" loaded successfully`);
  };

  const updateModalItem = (field: keyof InvoiceItem, value: any) => {
    setModalItem(prev => {
      const updated = { ...prev, [field]: value };

      // Auto-calculate when dependent fields change
      if (field === 'valueSalesExcludingST' || field === 'fixedNotifiedValueOrRetailPrice' || field === 'furtherTax' || field === 'discount' || field === 'extraTax' || field === 'rate') {
        const valueExclTax = Number(updated.valueSalesExcludingST) || 0;
        const fixedPrice = Number(updated.fixedNotifiedValueOrRetailPrice) || 0;
        const taxRate = parseFloat(updated.rate) || 0;
        const discount = Number(updated.discount) || 0;
        const baseValue = Math.max(valueExclTax, fixedPrice);

        if (baseValue > 0 && taxRate >= 0) {
          const salesTax = baseValue * (taxRate / 100);
          let furtherTax = Number(updated.furtherTax) || 0;
          if (field === 'furtherTax') {
            // Mark this item as manually edited to prevent auto-override by buyer type change
            const idx = editingItemIndex !== null ? editingItemIndex : items.length;
            setManualFurtherTax(prev => new Set(prev).add(idx));
          }
          if (field !== 'furtherTax' && field !== 'discount' && buyerRegistrationType === 'Unregistered') {
            furtherTax = baseValue * 0.04;
          }
          const extraTax = Number(updated.extraTax) || 0;
          const totalValue = baseValue + salesTax + furtherTax + extraTax - discount;

          if (field !== 'discount') {
            updated.salesTaxApplicable = parseFloat(salesTax.toFixed(2));
            updated.furtherTax = parseFloat(furtherTax.toFixed(2));
          }
          updated.totalValues = parseFloat(totalValue.toFixed(2));
        }
      }

      return updated;
    });
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemSelect = (index: number, itemId: string) => {
    const selectedItem = savedItems.find(item => item.id.toString() === itemId);
    if (!selectedItem) return;

    // Resolve transaction_type to code (supports both code and name storage)
    const ttCode = selectedItem.transaction_type
      ? (masterData?.transaction_types.find(t => t.code === selectedItem.transaction_type)?.code ||
         masterData?.transaction_types.find(t => t.name === selectedItem.transaction_type)?.code ||
         selectedItem.transaction_type)
      : '';
    const ttName = selectedItem.transaction_type || '';

    // If this is the first item (index 0), set the Transaction Type from the item
    if (index === 0 && ttCode) {
      setTransactionTypeId(ttCode);

      // Auto-set Sale Type for all items to the Transaction Type name
      setItems(prevItems =>
        prevItems.map(item => ({ ...item, saleType: ttName }))
      );
    }

    // If this is NOT the first item, validate transaction type matches
    if (index > 0 && ttCode && transactionTypeId) {
      if (ttCode !== transactionTypeId) {
        toast.error(`Cannot select this item. Transaction type mismatch. Please select an item with transaction type matching the first item.`);
        return; // Prevent selection
      }
    }

    // Store the selected item ID
    setSelectedSavedItems(prev => ({ ...prev, [index]: itemId }));

    // Auto-fill all fields from the saved item
    updateItem(index, 'hsCode', selectedItem.hs_code);
    updateItem(index, 'productDescription', selectedItem.product_description);
    updateItem(index, 'rate', selectedItem.default_rate || '');

    // Convert UOM code to name
    const uomCode = selectedItem.default_uom || 'NOS';
    const uomObj = masterData?.uom.find(u => u.code === uomCode);
    updateItem(index, 'uoM', uomObj?.name || uomCode);

    // Set sale type to the resolved Transaction Type name
    if (ttName) {
      updateItem(index, 'saleType', ttName);
    }

    // Set SRO fields if available
    if (selectedItem.sro_schedule_no) {
      updateItem(index, 'sroScheduleNo', selectedItem.sro_schedule_no);
    }
    if (selectedItem.sro_item_serial_no) {
      updateItem(index, 'sroItemSerialNo', selectedItem.sro_item_serial_no);
    }

    toast.success(`Item "${selectedItem.item_name}" loaded successfully`);
  };

  // Handle buyer business name input with autocomplete
  const handleBuyerBusinessNameChange = (value: string) => {
    setBuyerBusinessName(value);
    setBuyerHighlightedIndex(-1);

    // Filter saved buyers based on input
    if (value.trim().length > 0) {
      const filtered = savedBuyers.filter(buyer =>
        buyer.buyer_business_name.toLowerCase().includes(value.toLowerCase())
      );
      setBuyerSearchResults(filtered);
      setShowBuyerSuggestions(filtered.length > 0);
    } else {
      // Show all saved buyers when input is empty
      setBuyerSearchResults(savedBuyers);
      setShowBuyerSuggestions(savedBuyers.length > 0);
    }
  };

  // Handle selecting a saved buyer from suggestions
  const handleSelectSavedBuyer = (buyer: any) => {
    setBuyerBusinessName(buyer.buyer_business_name);
    setBuyerNTNCNIC(buyer.buyer_ntn_cnic);
    setBuyerAddress(buyer.buyer_address || '');
    setBuyerProvince(buyer.buyer_province || '');
    setBuyerRegistrationType(buyer.buyer_registration_type || 'Registered');

    // Find province code if province name is set
    if (buyer.buyer_province && masterData) {
      const province = masterData?.provinces.find(p => p.name === buyer.buyer_province);
      if (province) {
        setBuyerProvinceCode(province.code);
      }
    }

    setShowBuyerSuggestions(false);
    setBuyerHighlightedIndex(-1);
    toast.success(`Buyer "${buyer.buyer_business_name}" loaded successfully`);
  };

  const updateItem = useCallback((index: number, field: keyof InvoiceItem, value: any) => {
    setItems(prevItems => {
      const updatedItems = [...prevItems];
      updatedItems[index] = { ...updatedItems[index], [field]: value };

      // Auto-calculate when Value Excl. Sales Tax, Fixed/Retail Price, Further Tax, or Discount is updated
      if (field === 'valueSalesExcludingST' || field === 'fixedNotifiedValueOrRetailPrice' || field === 'furtherTax' || field === 'discount' || field === 'extraTax') {
        const valueExclTax = Number(updatedItems[index].valueSalesExcludingST) || 0;
        const fixedPrice = Number(updatedItems[index].fixedNotifiedValueOrRetailPrice) || 0;
        const taxRate = parseFloat(updatedItems[index].rate) || 0;
        const discount = Number(updatedItems[index].discount) || 0;

        // Use the greater value between Value Excl. Tax and Fixed/Retail Price
        const baseValue = Math.max(valueExclTax, fixedPrice);

        if (baseValue > 0 && taxRate >= 0) {
          // Calculate Sales Tax Applicable = Base Value × (Tax Rate / 100)
          const salesTax = baseValue * (taxRate / 100);

          // Calculate Further Tax (4%) for Unregistered buyers only when NOT manually edited
          let furtherTax = Number(updatedItems[index].furtherTax) || 0;
          if (field === 'furtherTax') {
            setManualFurtherTax(prev => new Set(prev).add(index));
          }
          if (!manualFurtherTax.has(index) && field !== 'discount' && buyerRegistrationType === 'Unregistered') {
            furtherTax = baseValue * 0.04;
          }

          const extraTax = Number(updatedItems[index].extraTax) || 0;
          // Total Value (Inc. Tax) = Base Value + Sales Tax + Further Tax + Extra Tax - Discount
          const totalValue = baseValue + salesTax + furtherTax + extraTax - discount;

          if (field !== 'discount') {
            updatedItems[index].salesTaxApplicable = parseFloat(salesTax.toFixed(2));
            updatedItems[index].furtherTax = parseFloat(furtherTax.toFixed(2));
          }
          updatedItems[index].totalValues = parseFloat(totalValue.toFixed(2));
        }
      }

      return updatedItems;
    });
  }, [buyerRegistrationType, manualFurtherTax]);

  const validateFormFields = (): boolean => {
    if (items.length === 0) {
      toast.error('Please add at least one item to the invoice');
      return false;
    }
    if (!invoiceNo.trim()) {
      toast.error('Invoice No is required');
      return false;
    }
    if (!invoiceDate) {
      toast.error('Invoice Date is required');
      return false;
    }
    if (!buyerBusinessName.trim()) {
      toast.error('Buyer Business Name is required');
      return false;
    }
    if (!buyerProvince) {
      toast.error('Buyer Province is required');
      return false;
    }
    if (!buyerAddress.trim()) {
      toast.error('Buyer Address is required');
      return false;
    }
    if (buyerRegistrationType === 'Unregistered') {
      const itemsWithoutFurtherTax = items.filter(item => String(item.furtherTax ?? '').trim() === '');
      if (itemsWithoutFurtherTax.length > 0) {
        toast.error('Further Tax is required for all items when buyer is Unregistered');
        return false;
      }
    }
    return true;
  };

  const buildInvoiceData = () => {
    const formattedItems = items.map(item => ({
      hs_code: item.hsCode,
      product_description: item.productDescription,
      rate: item.rate,
      uom: item.uoM,
      quantity: item.quantity,
      total_values: item.totalValues,
      value_sales_excluding_st: item.valueSalesExcludingST,
      fixed_notified_value_or_retail_price: item.fixedNotifiedValueOrRetailPrice,
      sales_tax_applicable: item.salesTaxApplicable,
      sales_tax_withheld_at_source: parseFloat(item.salesTaxWithheldAtSource) || 0,
      extra_tax: item.extraTax,
      further_tax: item.furtherTax,
      sro_schedule_no: item.sroScheduleNo || undefined,
      fed_payable: item.fedPayable,
      discount: item.discount,
      sale_type: item.saleType,
      sro_item_serial_no: item.sroItemSerialNo || undefined
    }));

    return {
      external_id: invoiceNo || `INV-${Date.now()}`,
      invoice_type: invoiceType,
      invoice_date: invoiceDate,
      transaction_type_id: transactionTypeId || undefined,
      seller_ntn_cnic: sellerNTNCNIC,
      seller_business_name: sellerBusinessName,
      seller_province: sellerProvince,
      seller_address: sellerAddress,
      buyer_ntn_cnic: buyerNTNCNIC,
      buyer_business_name: buyerBusinessName,
      buyer_province: buyerProvince,
      buyer_address: buyerAddress,
      buyer_registration_type: buyerRegistrationType,
      invoice_ref_no: invoiceRefNo || undefined,
      scenario_id: scenarioId || undefined,
      income_tax: incomeTax,
      items: formattedItems,
      environment: environment
    };
  };

  const handleSaveDraft = async () => {
    if (!validateFormFields()) return;

    setIsSaving(true);
    try {
      const invoiceData = buildInvoiceData();

      let invoiceResponse: any;
      if (isEditMode && initialData?.id) {
        invoiceResponse = await api.invoices.update(initialData.id, invoiceData);
      } else {
        invoiceResponse = await api.invoices.create(invoiceData);
      }

      const invoiceId = invoiceResponse.id || invoiceResponse.invoice?.id;
      if (invoiceId) {
        setSavedInvoiceId(invoiceId);
      }

      toast.success('Invoice saved as draft');
      router.push('/invoices/history');
    } catch (error) {
      console.error('Save draft error:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      toast.error(`Failed to save: ${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleValidate = async () => {
    if (!validateFormFields()) return;

    setIsValidating(true);
    try {
      const invoiceData = buildInvoiceData();

      // Save invoice to database
      let invoiceResponse: any;
      if (isEditMode && initialData?.id) {
        invoiceResponse = await api.invoices.update(initialData.id, invoiceData);
      } else {
        invoiceResponse = await api.invoices.create(invoiceData);
      }

      // Extract invoice ID from response
      const invoiceId = invoiceResponse.id || invoiceResponse.invoice?.id;
      if (!invoiceId) {
        toast.error('Failed to get invoice ID from server');
        setIsValidating(false);
        return;
      }
      setSavedInvoiceId(invoiceId);

      // Validate with FBR
      toast.info('Validating invoice with FBR...');
      const validateResponse = await api.invoices.validate(invoiceId);

      if (validateResponse.success) {
        setIsValidated(true);
      }

      setDialogData({
        success: validateResponse.success,
        title: validateResponse.success ? 'Validation Successful' : 'Validation Failed',
        message: validateResponse.message || (validateResponse.success ? 'Invoice validated successfully' : 'Validation failed'),
        invoiceNumber: invoiceNo,
        errors: validateResponse.errors || [],
        invoiceId: invoiceId
      });
      setDialogOpen(true);
    } catch (error) {
      console.error('Validation error:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setDialogData({
        success: false,
        title: 'Validation Error',
        message: errorMessage,
        invoiceNumber: invoiceNo,
        errors: [],
        invoiceId: savedInvoiceId || undefined
      });
      setDialogOpen(true);
    } finally {
      setIsValidating(false);
    }
  };

  const handlePost = async () => {
    if (!savedInvoiceId) {
      toast.error('No invoice to post. Please validate first.');
      return;
    }

    setIsPosting(true);
    try {
      toast.info('Posting invoice to FBR...');
      const postResponse = await api.invoices.post(savedInvoiceId);

      if (postResponse.success) {
        toast.success(`Invoice posted successfully! FBR Number: ${postResponse.fbr_invoice_number || 'N/A'}`);
      }

      setDialogData({
        success: postResponse.success,
        title: postResponse.success ? 'Invoice Posted Successfully' : 'Posting Failed',
        message: postResponse.message || (postResponse.success ? 'Invoice posted successfully' : 'Posting failed'),
        invoiceNumber: invoiceNo,
        fbrNumber: postResponse.fbr_invoice_number,
        errors: []
      });
      setDialogOpen(true);
    } catch (error) {
      console.error('Post error:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setDialogData({
        success: false,
        title: 'Posting Error',
        message: errorMessage,
        invoiceNumber: invoiceNo,
        errors: []
      });
      setDialogOpen(true);
    } finally {
      setIsPosting(false);
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    handleValidate();
  };

  return (
    <form onSubmit={handleFormSubmit} className="space-y-6 h-full">
      {/* Loading state */}
      {/* Error state */}
      {masterDataError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-4">
            <p className="text-red-600">{masterDataError}</p>
          </CardContent>
        </Card>
      )}

      {/* Form content - show immediately, disable fields until master data loads */}
      <div className="flex flex-col md:flex-row gap-4">
          {/* Action Sidebar — Left (stacks horizontally on mobile, vertical sidebar on desktop) */}
          <div className="shrink-0 flex md:flex-col gap-2 md:sticky top-4 self-start order-1 md:order-none pt-0 md:pt-18 justify-center md:justify-start">
            {/* Save Draft Button */}
            <Button
              variant="outline"
              size="icon"
              type="button"
              onClick={handleSaveDraft}
              disabled={isLoading || isSubmitting || isSaving || isValidating || isPosting}
              className="h-8 w-8 border border-amber-200 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Save as Draft"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
            </Button>

            {/* Validate / Post Button */}
            {!isValidated ? (
              <Button
                variant="outline"
                size="icon"
                type="button"
                onClick={handleValidate}
                disabled={isLoading || isSubmitting || isValidating || isPosting || isSaving}
                className="h-8 w-8 border border-green-400 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Validate with FBR"
              >
                {isValidating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
              </Button>
            ) : (
              <Button
                variant="outline"
                size="icon"
                type="button"
                onClick={handlePost}
                disabled={isLoading || isSubmitting || isPosting || isValidating}
                className="h-8 w-8 border-[#1e40af] text-[#1e40af]  disabled:opacity-30 disabled:cursor-not-allowed"
                title="Post to FBR"
              >
                {isPosting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            )}

            {/* Cancel Button */}
            <Button
              variant="outline"
              size="icon"
              type="button"
              onClick={onCancel}
              disabled={isLoading || isSubmitting || isSaving || isValidating || isPosting}
              className="h-8 w-8 text-red-500 hover:text-red-600 border-red-300 dark:border-red-800 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Main Form Content */}
          <div className="flex-1 min-w-0 space-y-1">
          {/* Invoice Header */}
          <Card>
            <CardContent>
              <div className="flex flex-wrap gap-2 xl:flex-nowrap xl:gap-0 xl:justify-between px-2">
                <div className='w-full min-w-[140px] sm:w-[48%] md:w-[23%] xl:w-[150px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="invoiceNo">Invoice No *</Label>
                  <Input
                    id="invoiceNo"
                    value={invoiceNo}
                    onChange={(e) => setInvoiceNo(e.target.value)}
                    placeholder="e.g., INV-2024-001"
                    required
                    className='w-full xl:w-[150px] text-[12px] h-[30px]'
                  />
                </div>

                <div className='w-full min-w-[140px] sm:w-[48%] md:w-[23%] xl:w-[150px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="invoiceType">Invoice Type *</Label>
                  <Select value={invoiceType} onValueChange={(val) => setInvoiceType(val as 'Sale Invoice' | 'Debit Note')}>
                    <SelectTrigger disabled={(masterData?.invoice_types.length ?? 0) === 0} className="text-[12px] h-[30px]">
                      <span className="flex-1 text-left">
                        {invoiceType
                          ? (masterData?.invoice_types.find(t => t.code === invoiceType)?.name || invoiceType)
                          : ((masterData?.invoice_types.length ?? 0) === 0 ? "Configure FBR token in profile" : "Select invoice type")
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {(masterData?.invoice_types.length ?? 0) === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        masterData?.invoice_types.map((type) => (
                          <SelectItem key={type.code} value={type.code}>{type.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className='w-full min-w-[140px] sm:w-[48%] md:w-[23%] xl:w-[150px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="invoiceDate">Invoice Date *</Label>
                  <Input
                    className='w-full xl:w-[150px] text-[12px] h-[30px]'
                    id="invoiceDate"
                    type="date"
                    value={invoiceDate}
                    onChange={(e) => setInvoiceDate(e.target.value)}
                    required
                  />
                </div>

                <div className='w-full min-w-[180px] sm:w-[48%] md:w-[23%] xl:w-[210px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="transactionType">Transaction Type *</Label>
                  <Select value={transactionTypeId} onValueChange={(val) => {
                    setTransactionTypeId(val);


                    // Find the transaction type name from the code
                    const selectedTransactionType = masterData?.transaction_types.find(t => t.code === val);
                    const transactionTypeName = selectedTransactionType?.name?.trim() || '';

                    // Auto-set Sale Type for all items to match Transaction Type NAME (not code)
                    setItems(prevItems =>
                      prevItems.map(item => ({ ...item, saleType: transactionTypeName }))
                    );
                  }}>
                    <SelectTrigger disabled={true} className="bg-gray-50 dark:bg-gray-800">
                      <span className="flex-1 text-left text-[11px]">
                        {transactionTypeId
                          ? masterData?.transaction_types.find(t => t.code === transactionTypeId)?.name || transactionTypeId
                          : "Will be set by item selection"
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {(masterData?.transaction_types.length ?? 0) === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        masterData?.transaction_types.map((type) => (
                          <SelectItem key={type.code} value={type.code}>{type.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {environment === 'SANDBOX' && (
                  <>
                    <div className='w-full min-w-[110px] sm:w-[48%] md:w-[23%] xl:w-[120px]'>
                      <Label className='pl-3 text-[14px] font-bold' htmlFor="environment">Environment</Label>
                      <Input
                        id="environment"
                        value={environment}
                        readOnly
                        disabled
                        className='w-full xl:w-[120px] text-[12px] h-[30px] bg-gray-50 dark:bg-gray-800 cursor-not-allowed'
                      />
                    </div>
                    <div className='w-full min-w-[110px] sm:w-[48%] md:w-[23%] xl:w-[120px]'>
                      <Label className='pl-3 text-[14px] font-bold' htmlFor="scenarioId">Scenario ID *</Label>
                      <Input
                        id="scenarioId"
                        value={scenarioId}
                        onChange={(e) => setScenarioId(e.target.value)}
                        placeholder="e.g., SN001"
                        required
                        className='w-full xl:w-[120px] text-[12px] h-[30px]'
                      />
                    </div>
                  </>
                )}

                {(() => {
                  const resolvedName = masterData?.invoice_types.find(t => t.code === invoiceType)?.name || invoiceType;
                  return resolvedName === 'Debit Note';
                })() && (
                  <div className='w-full min-w-[160px] sm:w-[48%] md:w-[23%] xl:w-[180px]'>
                    <Label className='pl-3 text-[14px] font-bold' htmlFor="invoiceRefNo">Invoice Ref No *</Label>
                    <Input
                      id="invoiceRefNo"
                      value={invoiceRefNo}
                      onChange={(e) => setInvoiceRefNo(e.target.value)}
                      placeholder="22 or 28 digits"
                      required
                      className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* <div className='text-black font-extrabold px-2 flex justify-center'>
            Buyer Information
          </div> */}
          
          {/* Buyer Information */}
          <Card className='w-full mt-2'>
            {/* <CardHeader> */}
              {/* <CardTitle>Buyer Information</CardTitle> */}
            {/* </CardHeader> */}
            <CardContent>
              <div className='flex flex-wrap gap-2 xl:flex-nowrap xl:gap-0 xl:justify-between px-2 mb-2'>
                {/* Buyer Business Name */}
                <div className="relative w-full sm:w-[48%] md:w-[48%] xl:w-[490px]">
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="buyerBusinessName">Business Name *</Label>
                  <Input
                    className='w-full xl:w-[490px] text-[12px] h-[30px]'
                    id="buyerBusinessName"
                    value={buyerBusinessName}
                    onChange={(e) => handleBuyerBusinessNameChange(e.target.value)}
                    onKeyDown={(e) => {
                      if (!showBuyerSuggestions || buyerSearchResults.length === 0) {
                        // Open suggestions on ArrowDown/ArrowUp when closed
                        if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && savedBuyers.length > 0 && !showBuyerSuggestions) {
                          e.preventDefault();
                          const results = buyerBusinessName.trim().length > 0
                            ? savedBuyers.filter(b => b.buyer_business_name.toLowerCase().includes(buyerBusinessName.toLowerCase()))
                            : savedBuyers;
                          setBuyerSearchResults(results);
                          setShowBuyerSuggestions(true);
                          setBuyerHighlightedIndex(e.key === 'ArrowDown' ? 0 : results.length - 1);
                        }
                        return;
                      }

                      if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        setBuyerHighlightedIndex(prev => {
                          const next = prev + 1;
                          return next >= buyerSearchResults.length ? 0 : next;
                        });
                      } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        setBuyerHighlightedIndex(prev => {
                          const next = prev - 1;
                          return next < 0 ? buyerSearchResults.length - 1 : next;
                        });
                      } else if (e.key === 'Enter') {
                        e.preventDefault();
                        if (buyerHighlightedIndex >= 0 && buyerHighlightedIndex < buyerSearchResults.length) {
                          handleSelectSavedBuyer(buyerSearchResults[buyerHighlightedIndex]);
                        }
                      } else if (e.key === 'Escape') {
                        e.preventDefault();
                        setShowBuyerSuggestions(false);
                        setBuyerHighlightedIndex(-1);
                      }
                    }}
                    onFocus={() => {
                      setBuyerHighlightedIndex(-1);
                      // Show all saved buyers when field is focused
                      if (savedBuyers.length > 0) {
                        if (buyerBusinessName.trim().length > 0) {
                          // Filter based on current input
                          const filtered = savedBuyers.filter(buyer =>
                            buyer.buyer_business_name.toLowerCase().includes(buyerBusinessName.toLowerCase())
                          );
                          setBuyerSearchResults(filtered);
                          setShowBuyerSuggestions(filtered.length > 0);
                        } else {
                          // Show all saved buyers when input is empty
                          setBuyerSearchResults(savedBuyers);
                          setShowBuyerSuggestions(true);
                        }
                      }
                    }}
                    onBlur={() => {
                      // Delay hiding to allow click on suggestion
                      setTimeout(() => {
                        setShowBuyerSuggestions(false);
                        setBuyerHighlightedIndex(-1);
                      }, 200);
                    }}
                    placeholder="Enter business name"
                    required
                    autoComplete="off"
                    role="combobox"
                    aria-expanded={showBuyerSuggestions}
                    aria-autocomplete="list"
                  />
                  {showBuyerSuggestions && buyerSearchResults.length > 0 && (
                    <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-y-auto" role="listbox">
                      {buyerSearchResults.map((buyer, index) => (
                        <div
                          key={`${buyer.buyer_ntn_cnic}-${buyer.buyer_business_name}-${index}`}
                          role="option"
                          aria-selected={buyerHighlightedIndex === index}
                          data-highlighted={buyerHighlightedIndex === index ? '' : undefined}
                          className="px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer data-[highlighted]:bg-blue-50 data-[highlighted]:dark:bg-blue-900/30"
                          onClick={() => handleSelectSavedBuyer(buyer)}
                          onMouseEnter={() => setBuyerHighlightedIndex(index)}
                        >
                          <div className="font-medium text-sm">{buyer.buyer_business_name}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            NTN/CNIC: {buyer.buyer_ntn_cnic}
                            {buyer.buyer_province && ` • ${buyer.buyer_province}`}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {/* Buyer Cnic */}
                <div className='w-full min-w-[120px] sm:w-[48%] md:w-[23%] xl:w-[140px]'>
                  <Label className='pl-3 text-[14px] font-bold text-nowrap' htmlFor="buyerNTNCNIC">
                    Ntn/Cnic {buyerRegistrationType === 'Registered' ? '*' : '(Optional)'}
                  </Label>
                  <div className="relative">
                    <Input
                      id="buyerNTNCNIC"
                      value={buyerNTNCNIC}
                      onChange={(e) => setBuyerNTNCNIC(e.target.value)}
                      placeholder="Enter Ntn/Cnic"
                      required={buyerRegistrationType === 'Registered'}
                      className='w-full xl:w-[140px] text-[12px] h-[30px]'
                      // className={isVerifyingBuyer ? 'pr-10' : ''}
                    />
                    {isVerifyingBuyer && (
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                      </div>
                    )}
                  </div>
                  {buyerVerificationMessage && (
                    <p className={`text-xs mt-1 ${buyerVerificationMessage.startsWith('✓') ? 'text-green-600' : 'text-amber-600'}`}>
                      {buyerVerificationMessage}
                    </p>
                  )}
                </div>
                {/* Buyer Type */}
                <div className='w-full min-w-[100px] sm:w-[48%] md:w-[23%] xl:w-[120px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="buyerRegistrationType">Type *</Label>
                  <Select value={buyerRegistrationType} onValueChange={(val) => setBuyerRegistrationType(val as 'Registered' | 'Unregistered')}>
                    <SelectTrigger disabled={isVerifyingBuyer}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {masterData?.registration_types.map((type) => (
                        <SelectItem key={type.code} value={type.name}>{type.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {/* Buyer Province */}
                <div className='w-full min-w-[180px] sm:w-[48%] md:w-[23%] xl:w-[220px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="buyerProvince">Province *</Label>
                  <Select  value={buyerProvince} onValueChange={(val) => {
                    setBuyerProvince(val);
                    // Find and store province code
                    const province = masterData?.provinces.find(p => p.name === val);
                    if (province) {
                      setBuyerProvinceCode(province.code);
                    }
                  }}>
                    <SelectTrigger disabled={(masterData?.provinces.length ?? 0) === 0}>
                      <SelectValue placeholder={(masterData?.provinces.length ?? 0) === 0 ? "Configure FBR token in profile" : "Select province"} />
                    </SelectTrigger>
                    <SelectContent>
                      {(masterData?.provinces.length ?? 0) === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        masterData?.provinces.map((province) => (
                          <SelectItem key={province.code} value={province.name}>{province.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
                    
              {/* Buyer Address */}      
              <div className='px-2'>
                <Label className='pl-3 text-[14px] font-bold' htmlFor="buyerAddress">Address *</Label>
                <textarea
                  className='w-full text-[12px] h-[60px] resize-none min-h-[60px] rounded-md border-2 border-[#c9cccf] px-3 py-2 shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50'
                  id="buyerAddress"
                  value={buyerAddress}
                  onChange={(e) => setBuyerAddress(e.target.value)}
                  placeholder="Enter business address"
                  required
                />
              </div>
            </CardContent>
          </Card>

        
      
          {/* Item Heading */}
          <div className="flex items-center justify-between">
            <div className="text-black font-extrabold px-2">Item Information</div>
            {/* <Button
              type="button"
              onClick={addItem}
              size="sm"
              className="h-8 w-8 rounded-lg border-slate-200 dark:border-neutral-800 shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              
            </Button> */}
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={addItem}
              className="h-8 w-8 rounded-lg border-blue-300 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100"
              title="Add Item"
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>

          {/* Invoice Items */}

          {/*table 1 if invoice not exist*/}
          {items.length === 0 ? (
            <div className="overflow-x-auto xl:overflow-visible">
              <table className="w-[720px] xl:w-full table-fixed bg-[#7c97f0] rounded-4xl flex-shrink-0">
              <thead>
                  <tr>
                    <th className="border-r-2 border-[#FFFFFF] w-[155px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Item Name</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[50px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Qty</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[85px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Value Excl. Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[40px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Rate</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[75px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Sales Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[70px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Further Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[85px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Total (Inc. Tax)</th>
                    <th className=" w-[45px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Actions</th>
                  </tr>
                </thead>
                </table>
              <div className="text-center py-12 text-[#6d7175] dark:text-[#8c9196]">
              <p className="text-lg font-medium">No items added yet</p>
              <p className="text-sm mt-1">Click "+" to add invoice items</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto xl:overflow-visible">
              <div className='max-h-50 overflow-y-auto rounded-2xl min-w-[720px] xl:min-w-0'>
                {/*table 2 if invoice exist*/}
                <table className='w-[720px] xl:w-full table-fixed'>
                  <thead className="sticky top-0 bg-[#7c97f0] z-10">
                    <tr>
                      <th className="border-r-2 border-[#FFFFFF] w-[155px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Item Name</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[50px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Qty</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[85px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Value Excl. Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[40px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Rate</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[75px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Sales Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[70px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Further Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[85px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Total (Inc. Tax)</th>
                      <th className="w-[45px] px-2 py-1 text-center text-xs font-bold text-black uppercase tracking-wider align-middle">Actions</th>
                    </tr>
                  </thead>
                  <tbody className='divide-y divide-[#FFFFFF]'>
                    {items.map((item, index) => (
                      <tr key={index} className="group transition-colors duration-150 text-sm text-black bg-[#e7eaf1]">
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[155px] " title={item.productDescription}>{item.productDescription || '—'}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[50px] text-center">{item.quantity || 0}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[85px] text-right">{Number(item.valueSalesExcludingST).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[40px] text-center">{item.rate || '—'}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[75px] text-right">{Number(item.salesTaxApplicable).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[70px] text-right">{Number(item.furtherTax).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[85px] text-right">{Number(item.totalValues).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="py-1 px-2 align-middle w-[45px]">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              type="button"
                              onClick={() => openEditModal(index)}
                              className="h-8 w-8 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-[#6d7175] hover:border-[#008060] hover:text-[#008060] dark:hover:border-[#00a876] dark:hover:text-[#00a876] hover:bg-[#f0f9f6] dark:hover:bg-[#0d3d2f]/30 transition-colors cursor-pointer"
                              title="Edit item"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => removeItem(index)}
                              className="h-8 w-8 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-red-500 hover:text-red-600 hover:border-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
                              title="Remove item"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="overflow-x-auto xl:overflow-visible">
                {/*table 3 footer*/}
                <table className="w-[720px] xl:w-full table-fixed border-2 border-blue-300 rounded-2xl border-separate border-spacing-0 bg-[#FFFFFF]">
                  <tfoot>
                    <tr className="font-normal text-black text-[15px]">
                      <td className="py-1 px-2 w-[205px] text-center">Totals:</td>
                      <td className="py-1 px-2 w-[85px] text-right">
                        {items.reduce((sum, item) => sum + (Number(item.valueSalesExcludingST) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className='py-1 px-2 w-[40px]'></td>
                      <td className="py-1 px-2 w-[75px] text-right">
                        {items.reduce((sum, item) => sum + (Number(item.salesTaxApplicable) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-1 px-2 w-[70px] text-right">
                        {items.reduce((sum, item) => sum + (Number(item.furtherTax) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-1 px-2 w-[85px] text-right">
                        {items.reduce((sum, item) => sum + (Number(item.totalValues) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className='py-1 px-2 w-[45px]'></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        

      {/* Item Modal / Popup */}
      {isItemModalOpen && (
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
          `}</style>
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-5 overflow-y-auto">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => {
              setIsItemModalOpen(false);
              setEditingItemIndex(null);
            }}
          />
          {/* Modal Content */}
          <div className="relative z-50 w-[95vw] max-w-6xl bg-white dark:bg-[#161616] rounded-2xl shadow-2xl border-2 border-black dark:border-[#2e2e2e] mb-10 mx-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-1 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
              <h4 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">
                {editingItemIndex !== null ? `Edit Item ${editingItemIndex + 1}` : 'Add New Item'}
              </h4>
              <button
                type="button"
                onClick={() => {
                  setIsItemModalOpen(false);
                  setEditingItemIndex(null);
                }}
                className="p-2 rounded-lg hover:bg-[#f3f4f6] dark:hover:bg-[#2e2e2e] text-[#6d7175] transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 pt-5 pb-5 space-y-6">
              {/* Item Entry Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mr-2">Item Type:</span>
                <button
                  type="button"
                  onClick={() => {
                    setItemEntryMode('saved');
                    setModalSelectedSavedItem('');
                  }}
                  className={`px-4 py-1.5 text-sm font-medium rounded-lg border transition-all duration-150 ${
                    itemEntryMode === 'saved'
                      ? 'bg-[#008060] text-white border-[#008060] dark:bg-[#00a876] dark:border-[#00a876] shadow-sm'
                      : 'bg-white dark:bg-[#1a1a1a] text-[#6d7175] dark:text-[#8c9196] border-[#c9cccf] dark:border-[#3e3e3e] hover:border-[#008060] hover:text-[#008060] dark:hover:border-[#00a876] dark:hover:text-[#00a876]'
                  }`}
                >
                  Existing Saved Items
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setItemEntryMode('temporary');
                    setModalSelectedSavedItem('');
                  }}
                  className={`px-4 py-1.5 text-sm font-medium rounded-lg border transition-all duration-150 ${
                    itemEntryMode === 'temporary'
                      ? 'bg-[#008060] text-white border-[#008060] dark:bg-[#00a876] dark:border-[#00a876] shadow-sm'
                      : 'bg-white dark:bg-[#1a1a1a] text-[#6d7175] dark:text-[#8c9196] border-[#c9cccf] dark:border-[#3e3e3e] hover:border-[#008060] hover:text-[#008060] dark:hover:border-[#00a876] dark:hover:text-[#00a876]'
                  }`}
                >
                  Temporary Item
                </button>
              </div>

              {/* Saved Items Quick Select — only when mode is 'saved' */}
              {itemEntryMode === 'saved' && savedItems.length > 0 && (
                <div className={`p-2 border rounded-xl ${
                  editingItemIndex !== null && editingItemIndex > 0 && transactionTypeId && modalSelectedSavedItem && (() => {
                    const si = savedItems.find(item => item.id.toString() === modalSelectedSavedItem);
                    return si && si.transaction_type && si.transaction_type !== transactionTypeId;
                  })()
                    ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-800'
                    : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                }`}>
                  <Label className="text-sm font-semibold mb-2 block">Quick Select from Saved Items</Label>
                  <Select value={modalSelectedSavedItem} onValueChange={handleModalItemSelect}>
                    <SelectTrigger>
                      {modalSelectedSavedItem ? (
                        <span>{savedItems.find(item => item.id.toString() === modalSelectedSavedItem)?.item_name || 'Select a saved item to auto-fill...'}</span>
                      ) : (
                        <span className="text-muted-foreground">Select a saved item to auto-fill...</span>
                      )}
                    </SelectTrigger>
                    <SelectContent>
                      {savedItems.map((savedItem) => (
                        <SelectItem key={savedItem.id} value={savedItem.id.toString()}>
                          <div className="flex flex-col">
                            <span className="font-medium">{savedItem.item_name}</span>
                            <span className="text-xs text-gray-500">
                              {savedItem.hs_code} - {savedItem.product_description}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {editingItemIndex !== null && editingItemIndex > 0 && transactionTypeId && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-2 flex items-center gap-1 font-medium">
                      <AlertCircle className="h-3 w-3" />
                      Only items with matching transaction type can be selected
                    </p>
                  )}
                  {editingItemIndex === 0 && !transactionTypeId && (
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                      Select an item to automatically set the transaction type and fill all fields
                    </p>
                  )}
                  {editingItemIndex === 0 && transactionTypeId && (
                    <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                      Transaction type set. All items must match this transaction type.
                    </p>
                  )}
                </div>
              )}

              {/* Temporary Item notice */}
              {itemEntryMode === 'temporary' && (
                <div className="p-3 border rounded-xl bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800">
                  <p className="text-sm text-amber-700 dark:text-amber-300 flex items-center gap-2">
                    <Info className="h-4 w-4" />
                    Temporary item — please fill all fields manually below.
                  </p>
                </div>
              )}

              {/* Item Fields Grid */}
              <div>

                <div className='flex flex-wrap gap-2 xl:flex-nowrap xl:justify-between'>
                <div className='w-full sm:w-[48%] md:w-[23%] xl:w-[115px]'>
                  <Label className='pl-3 text-[14px] font-bold'>HS Code *</Label>
                  <Input
                    className='w-full xl:w-[100px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.hsCode}
                    onChange={(e) => updateModalItem('hsCode', e.target.value)}
                    placeholder="HS Code"
                    required
                  />
                </div>

                <div className="w-full sm:w-[48%] md:w-[48%] xl:w-[600px]">
                  <Label className='pl-3 text-[14px] font-bold'>Product Description *</Label>
                  <Input
                    className='w-full xl:w-[600px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.productDescription}
                    onChange={(e) => updateModalItem('productDescription', e.target.value)}
                    placeholder="Enter product description"
                    required
                  />
                </div>

                <div className='w-full sm:w-[48%] md:w-[23%] xl:w-[100px]'>
                  <Label>Tax Rate *</Label>
                  <Input
                    className='w-full xl:w-[80px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.rate}
                    onChange={(e) => updateModalItem('rate', e.target.value)}
                    placeholder="e.g., 18"
                    required
                  />
                </div>

                <div className='w-full sm:w-[48%] md:w-[23%] xl:w-[180px]'>
                  <Label>Unit of Measurement *</Label>
                  {itemEntryMode === 'temporary' ? (
                    <Select value={modalItem.uoM} onValueChange={(val) => updateModalItem('uoM', val)}>
                      <SelectTrigger className="text-[12px] h-[30px] w-full xl:w-[170px]">
                        <SelectValue placeholder="Select UOM" />
                      </SelectTrigger>
                      <SelectContent>
                        {(masterData?.uom ?? []).map((uom) => (
                          <SelectItem key={uom.code} value={uom.name}>
                            {uom.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      className='w-full xl:w-[170px] text-[12px] h-[30px]'
                      type="text"
                      value={modalItem.uoM}
                      onChange={(e) => updateModalItem('uoM', e.target.value)}
                      placeholder="e.g., NOS, KG, MT"
                      required
                    />
                  )}
                </div>
                </div>

                <div className='flex flex-wrap gap-2 xl:flex-nowrap xl:justify-between'>
                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Quantity *</Label>
                  <Input
                    className='w-full xl:w-[130px] text-[12px] h-[30px]'
                    type="number"
                    step="0.0001"
                    value={modalItem.quantity || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateModalItem('quantity', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Value Excl. Sales Tax *</Label>
                  <Input
                    className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    type="number"
                    step="0.01"
                    value={modalItem.valueSalesExcludingST || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateModalItem('valueSalesExcludingST', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Sales Tax Applicable *</Label>
                  <Input
                    className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    type="number"
                    step="0.01"
                    value={modalItem.salesTaxApplicable || ''}
                    readOnly
                    required
                  />
                  {/* <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Auto-calculated from value excl. tax
                  </p> */}
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Total Value (Inc. Tax) *</Label>
                  <Input
                    className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    type="number"
                    step="0.01"
                    value={modalItem.totalValues || ''}
                    readOnly
                    required
                  />
                  {/* <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    Auto-calculated (inc. tax + further tax - discount)
                  </p> */}
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Fixed/Retail Price *</Label>
                  <Input
                    className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.fixedNotifiedValueOrRetailPrice ?? '0'}
                    onChange={(e) => {
                      updateModalItem('fixedNotifiedValueOrRetailPrice', e.target.value);
                    }}
                    required
                  />
                </div>
                </div>

                <div className='flex flex-wrap gap-2 xl:flex-nowrap xl:justify-between'>
                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Sales Tax Withheld *</Label>
                  <Input
                    className='w-full xl:w-[160px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.salesTaxWithheldAtSource}
                    onChange={(e) => updateModalItem('salesTaxWithheldAtSource', e.target.value)}
                    placeholder="Enter amount (e.g., 0, 100.50)"
                    required
                  />
                </div>

                

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Further Tax {buyerRegistrationType === 'Unregistered' && '*'}</Label>
                  <Input
                    className='w-full xl:w-[120px] text-[12px] h-[30px]'
                    type="text"
                    value={modalItem.furtherTax ?? '0'}
                    onChange={(e) => {
                      updateModalItem('furtherTax', e.target.value);
                    }}
                    required={buyerRegistrationType === 'Unregistered'}
                  />
                  {/* {buyerRegistrationType === 'Unregistered' && (
                    <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                      Auto-filled at 4% of Value Excl. Sales Tax (editable)
                    </p>
                  )} */}
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>SRO Schedule No</Label>
                  <Input
                    className='w-full xl:w-[180px] text-[12px] h-[30px]'
                    value={modalItem.sroScheduleNo}
                    onChange={(e) => updateModalItem('sroScheduleNo', e.target.value)}
                    placeholder={modalItem.rate ? "No SRO schedules available" : "Select Item"}
                    disabled={!modalItem.rate}
                  />
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>SRO Item Serial No</Label>
                  <Input
                    className='w-full xl:w-[150px] text-[12px] h-[30px]'
                    value={modalItem.sroItemSerialNo}
                    onChange={(e) => updateModalItem('sroItemSerialNo', e.target.value)}
                    placeholder="Optional"
                  />
                </div>

                <div className='w-full sm:w-[48%] lg:w-[18%] xl:w-[180px]'>
                  <Label>Discount</Label>
                  <Input
                    className='w-full xl:w-[120px] text-[12px] h-[30px]'
                    type="number"
                    step="0.01"
                    value={modalItem.discount || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateModalItem('discount', val === '' ? 0 : parseFloat(val));
                    }}
                  />
                </div>
                </div>

                <div className='flex flex-wrap gap-2 xl:flex-nowrap xl:justify-between'>



                  <div className='w-full sm:w-[48%] lg:w-[30%] xl:w-[150px]'>
                    <Label>Extra Tax</Label>
                    <Input
                      className='w-full xl:w-[120px] text-[12px] h-[30px]'
                      type="text"
                      value={modalItem.extraTax ?? '0'}
                      onChange={(e) => {
                        updateModalItem('extraTax', e.target.value);
                      }}
                    />
                  </div>

                  <div className='w-full sm:w-[48%] lg:w-[30%] xl:w-[170px]'>
                    <Label>Sale Type</Label>
                    {itemEntryMode === 'temporary' ? (
                      <Select value={modalItem.saleType} onValueChange={(val) => updateModalItem('saleType', val)}>
                        <SelectTrigger className="text-[12px] h-[30px] w-full xl:w-[220px]">
                          <SelectValue placeholder="Select sale type" />
                        </SelectTrigger>
                        <SelectContent className='h-[200px]'>
                          {(masterData?.transaction_types ?? []).map((type) => (
                            <SelectItem key={type.code} value={type.name}>
                              {type.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        className='w-full xl:w-[220px] text-[12px] h-[30px] cursor-not-allowed'
                        value={modalItem.saleType}
                        disabled
                      />
                    )}
                  </div>

                  <div className='w-full sm:w-[48%] lg:w-[30%] xl:w-[160px]'>
                    <Label>FED Payable</Label>
                    <Input
                      className='w-full xl:w-[120px] text-[12px] h-[30px]'
                      type="number"
                      step="0.01"
                      value={modalItem.fedPayable || ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        updateModalItem('fedPayable', val === '' ? 0 : parseFloat(val));
                      }}
                    />
                  </div>

                  {/* <div className='w-[150px]'>
                      <Label htmlFor="modalIncomeTax">Income Tax Type *</Label>
                      <Select value={incomeTax} onValueChange={(val) => setIncomeTax(val as '236G' | '236H')}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select income tax type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="236G">236G</SelectItem>
                          <SelectItem value="236H">236H</SelectItem>
                        </SelectContent>
                      </Select>
                  </div>

                  <div className='w-[180px]'>
                      <Label>Withholding Tax (Info)</Label>
                      <Input
                        type="text"
                        value={`${(() => {
                          // Sum all saved items, but swap in modal values for the item being edited
                          const sumExclTax = items.reduce((sum, item, i) => {
                            if (i === editingItemIndex) {
                              return sum + (Number(modalItem.valueSalesExcludingST) || 0);
                            }
                            return sum + (Number(item.valueSalesExcludingST) || 0);
                          }, 0) + (editingItemIndex === null ? (Number(modalItem.valueSalesExcludingST) || 0) : 0);
                          const rate = incomeTax === '236G' ? 0.001 : 0.005;
                          return (sumExclTax * rate).toFixed(2);
                        })()}`}
                        readOnly
                        className="w-[160px] text-[12px] h-[30px]"
                      />
                  </div> */}
                </div>
              
            </div>

            {/* Income Tax */}
              {/* <div className="border rounded-xl p-4 bg-[#f9fafb] dark:bg-[#0d0d0d]">
                <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-3">Income Tax</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className='w-[220px]'>
                    <Label htmlFor="modalIncomeTax">Income Tax Type *</Label>
                    <Select value={incomeTax} onValueChange={(val) => setIncomeTax(val as '236G' | '236H')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select income tax type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="236G">236G</SelectItem>
                        <SelectItem value="236H">236H</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className='w-[220px]'>
                    <Label>Withholding Tax (Info)</Label>
                    <Input
                      type="text"
                      value={`${(() => {
                        const sumExclTax = items.reduce((sum, item) => sum + (Number(item.valueSalesExcludingST) || 0), 0);
                        const rate = incomeTax === '236G' ? 0.001 : 0.005;
                        return (sumExclTax * rate).toFixed(2);
                      })()}`}
                      readOnly
                      className="w-[220px] text-[12px] h-[30px]"
                    />
                    <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                      {incomeTax === '236G' ? '0.1%' : '0.5%'} of sum of Value Excl. Sales Tax from all items
                    </p>
                  </div>
                </div>
              </div> */}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e] bg-[#f9fafb] dark:bg-[#0d0d0d] rounded-b-2xl">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsItemModalOpen(false);
                  setEditingItemIndex(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleModalSave}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                {editingItemIndex !== null ? 'Save Changes' : 'Add Item'}
              </Button>
            </div>
          </div>
        </div>
        </>
      )}

      {/* Validation/Post Result Dialog */}
      <ValidationResultDialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        success={dialogData.success}
        title={dialogData.title}
        message={dialogData.message}
        invoiceNumber={dialogData.invoiceNumber}
        fbrNumber={dialogData.fbrNumber}
        errors={dialogData.errors}
        invoiceId={dialogData.invoiceId}
        onRetry={dialogData.invoiceId ? () => handleValidate() : undefined}
      />

          </div>
        </div>
    </form>
  );
}