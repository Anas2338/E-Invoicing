'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Trash2, Plus, Loader2, AlertCircle, Building2, MapPin, FileText, Pencil, Check, X, CheckCircle, Send, Save, XCircle } from 'lucide-react';
import { masterDataService, fbrIntegrationService, type AllMasterData } from '@/lib/api/api-client';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { ValidationResultDialog } from '@/components/invoices/validation-result-dialog';

interface InvoiceItem {
  hsCode: string;
  productDescription: string;
  rate: string;
  uoM: string;
  quantity: number | '';
  itemRate: number;  // Unit price = valueSalesExcludingST / quantity (editable)
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
  // Internal fields (not sent to FBR)
  incomeTaxType: string;
  withholdingTaxAmount: number;
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

  // Invoice items state
  // Note: income tax type is now per-item (incomeTaxType field on each item)
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
    itemRate: 0,
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
    sroItemSerialNo: '',
    incomeTaxType: '236G',
    withholdingTaxAmount: 0
  });
  // Track saved item selection in modal
  const [modalSelectedSavedItem, setModalSelectedSavedItem] = useState<string>('');

  // Track focus state for Value Excl. Sales Tax display formatting
  const [valueExclTaxFocused, setValueExclTaxFocused] = useState(false);

  // Raw input tracking for Quantity & Item Rate (to allow partial decimals while typing)
  const [rawQuantity, setRawQuantity] = useState('');
  const [rawItemRate, setRawItemRate] = useState('');

  // Track which amount fields are focused for float formatting
  const [focusedFields, setFocusedFields] = useState<Set<string>>(new Set());

  // Track validation errors for field borders
  const [fieldErrors, setFieldErrors] = useState<Set<string>>(new Set());

  const errorBorder = (field: string) =>
    fieldErrors.has(field) ? 'border-red-500 focus-visible:ring-red-500' : '';

  const formatAmount = (field: string, value: number | string): string => {
    if (focusedFields.has(field)) return String(value);
    const num = Number(value) || 0;
    if (num === 0) return '';
    return num.toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Sub-modal state for creating a new saved item
  const [isAddSavedItemModalOpen, setIsAddSavedItemModalOpen] = useState(false);
  const addSavedItemModalRef = useRef<HTMLDivElement>(null);

  // Focus trap and auto-focus for Add Saved Item sub-modal
  useEffect(() => {
    if (isAddSavedItemModalOpen) {
      // Auto-focus the first input after a short delay for rendering
      const timer = setTimeout(() => {
        document.getElementById('newItemCode')?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isAddSavedItemModalOpen]);
  const [newItemCode, setNewItemCode] = useState('');
  const [newItemName, setNewItemName] = useState('');
  const [newHsCode, setNewHsCode] = useState('');
  const [newHsCodeValid, setNewHsCodeValid] = useState<boolean | null>(null);
  const [newHsCodeError, setNewHsCodeError] = useState('');
  const [newProductDescription, setNewProductDescription] = useState('');
  const [newDefaultUom, setNewDefaultUom] = useState('');
  const [newDefaultRate, setNewDefaultRate] = useState('');
  const [newTransactionType, setNewTransactionType] = useState('');
  const [newSroScheduleNo, setNewSroScheduleNo] = useState('');
  const [newSroItemSerialNo, setNewSroItemSerialNo] = useState('');
  const [isSavingNewItem, setIsSavingNewItem] = useState(false);
  const [isValidatingNewHsCode, setIsValidatingNewHsCode] = useState(false);

  // HS Code → UOM filtered options for Add Saved Item sub-modal
  const [newHsCodeUoms, setNewHsCodeUoms] = useState<Array<{code: string, name: string}>>([]);
  const [newHsCodeUomsLoading, setNewHsCodeUomsLoading] = useState(false);

  // Transaction Type → Tax Rate filtered options for Add Saved Item sub-modal
  const [newTaxRateOptions, setNewTaxRateOptions] = useState<Array<{rate: string, name: string}>>([]);
  const [newTaxRatesLoading, setNewTaxRatesLoading] = useState(false);

  // HS Code autocomplete state for Add Saved Item sub-modal
  const [newHsCodeOptions, setNewHsCodeOptions] = useState<{ code: string; description: string }[]>([]);
  const [newHsCodeSearchOpen, setNewHsCodeSearchOpen] = useState(false);
  const [newHsCodeHighlightIndex, setNewHsCodeHighlightIndex] = useState(-1);
  const [newHsCodeSearching, setNewHsCodeSearching] = useState(false);
  const newHsCodeSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const newHsCodeDropdownRef = useRef<HTMLDivElement>(null);

  // Validate/Post workflow state
  const [isValidating, setIsValidating] = useState(false);
  const [isPosting, setIsPosting] = useState(false);
  const [savedInvoiceId, setSavedInvoiceId] = useState<string | null>(null);
  const [isValidated, setIsValidated] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Form reset state — incrementing formKey triggers re-fetch of profile & invoice number
  const [formKey, setFormKey] = useState(0);
  const [pendingReset, setPendingReset] = useState(false);

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
  }, [isEditMode, masterData, formKey]);

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
      // income_tax is now per-item — no invoice-level state needed

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
          itemRate: item.itemRate || item.item_rate ||
            (item.quantity && item.value_sales_excluding_st
              ? parseFloat((Number(item.value_sales_excluding_st) / Number(item.quantity)).toFixed(2))
              : 0),
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
          sroItemSerialNo: item.sroItemSerialNo || item.sro_item_serial_no || '',
          incomeTaxType: item.incomeTaxType || item.income_tax_type || '236G',
          withholdingTaxAmount: item.withholdingTaxAmount || item.withholding_tax_amount || 0
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
      quantity: '',
      itemRate: 0,
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
      sroItemSerialNo: '',
      incomeTaxType: '236G',
      withholdingTaxAmount: 0
    };
    setModalItem(newItem);
    setModalSelectedSavedItem('');
    setEditingItemIndex(null); // null = adding new
    setIsItemModalOpen(true);
  };

  const openEditModal = (index: number) => {
    setModalItem({ ...items[index] });
    setModalSelectedSavedItem(selectedSavedItems[index] || '');
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

    // Validate Fixed/Retail Price >= Value Excl. Sales Tax
    const valueExclTax = Number(modalItem.valueSalesExcludingST) || 0;
    const fixedPrice = Number(modalItem.fixedNotifiedValueOrRetailPrice) || 0;
    if (fixedPrice < valueExclTax) {
      toast.error('Fixed/Retail Price must be equal to or greater than Value Excl. Sales Tax');
      return;
    }

    // Validate Discount <= Value Excl. Sales Tax
    const discount = Number(modalItem.discount) || 0;
    if (discount > valueExclTax) {
      toast.error('Discount cannot exceed Value Excl. Sales Tax');
      return;
    }

    // Validate Sales Tax Withheld <= Sales Tax Applicable
    const salesTaxApplicable = Number(modalItem.salesTaxApplicable) || 0;
    const salesTaxWithheld = Number(modalItem.salesTaxWithheldAtSource) || 0;
    if (salesTaxWithheld > salesTaxApplicable) {
      toast.error('Sales Tax Withheld cannot exceed Sales Tax Applicable');
      return;
    }

    // Restrict non-first items to match the first item's sale type
    const isNonFirstItem = (editingItemIndex !== null && editingItemIndex > 0) || (editingItemIndex === null && items.length > 0);
    if (isNonFirstItem && items.length > 0) {
      const firstItemSaleType = items[0].saleType;
      if (firstItemSaleType && modalItem.saleType !== firstItemSaleType) {
        const ttName = masterData?.transaction_types.find(t => t.name === firstItemSaleType)?.name || firstItemSaleType;
        toast.error(`Sale Type must match the first item's Transaction Type: "${ttName}"`);
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

    // Validate transaction type for non-first items — compare against first item's saleType
    if (editingItemIndex !== null && editingItemIndex > 0 && items.length > 0) {
      const firstItemSaleType = items[0].saleType;
      if (firstItemSaleType && ttName && ttName.trim() !== firstItemSaleType.trim()) {
        toast.error(`Cannot select this item. Transaction type mismatch. Please select an item with matching transaction type.`);
        return;
      }
    }
    // Also validate for new items (editingItemIndex === null) when there are existing items
    if (editingItemIndex === null && items.length > 0) {
      const firstItemSaleType = items[0].saleType;
      if (firstItemSaleType && ttName && ttName.trim() !== firstItemSaleType.trim()) {
        toast.error(`Cannot select this item. Transaction type mismatch. Please select an item with matching transaction type.`);
        return;
      }
    }

    setModalSelectedSavedItem(itemId);

    const uomCode = selectedItem.default_uom || 'NOS';
    const uomObj = masterData?.uom.find(u => u.code === uomCode);

    // Calculate withholding tax from current modalItem values
    const valueExclTax = Number(modalItem.valueSalesExcludingST) || 0;
    const whtRate = (modalItem.incomeTaxType || '236G') === '236H' ? 0.005 : 0.001;

    setModalItem(prev => ({
      ...prev,
      hsCode: selectedItem.hs_code,
      productDescription: selectedItem.product_description,
      rate: selectedItem.default_rate || '',
      uoM: uomObj?.name || uomCode,
      saleType: ttName || prev.saleType,
      sroScheduleNo: selectedItem.sro_schedule_no || '',
      sroItemSerialNo: selectedItem.sro_item_serial_no || '',
      withholdingTaxAmount: parseFloat((valueExclTax * whtRate).toFixed(2)),
    }));

    toast.success(`Item "${selectedItem.item_name}" loaded successfully`);
  };

  const updateModalItem = (field: keyof InvoiceItem, value: any) => {
    setModalItem(prev => {
      const updated = { ...prev, [field]: value };

      // Auto-calculate withholding tax when income_tax_type or value_sales_excluding_st changes
      if (field === 'incomeTaxType' || field === 'valueSalesExcludingST') {
        const valueExclTax = Number(updated.valueSalesExcludingST) || 0;
        const rate = updated.incomeTaxType === '236H' ? 0.005 : 0.001;
        updated.withholdingTaxAmount = parseFloat((valueExclTax * rate).toFixed(2));
      }

      // Auto-calculate item rate when quantity or value_sales_excluding_st changes
      if (field === 'quantity' || field === 'valueSalesExcludingST') {
        const qty = Number(updated.quantity) || 0;
        const val = Number(updated.valueSalesExcludingST) || 0;
        updated.itemRate = qty > 0 ? parseFloat((val / qty).toFixed(2)) : 0;
      }

      // Auto-calculate when dependent fields change
      if (field === 'valueSalesExcludingST' || field === 'fixedNotifiedValueOrRetailPrice' || field === 'furtherTax' || field === 'discount' || field === 'extraTax' || field === 'fedPayable' || field === 'salesTaxWithheldAtSource' || field === 'rate') {
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
          } else if (
            field !== 'discount' &&
            buyerRegistrationType === 'Unregistered' &&
            // Only auto-calc for new items, or existing items not previously marked manual
            (editingItemIndex === null || !manualFurtherTax.has(editingItemIndex))
          ) {
            furtherTax = baseValue * 0.04;
          }
          const extraTax = Number(updated.extraTax) || 0;
          const fedPayable = Number(updated.fedPayable) || 0;
          const salesTaxWithheldVal = Number(updated.salesTaxWithheldAtSource) || 0;
          const totalValue = baseValue + salesTax + furtherTax + extraTax + fedPayable - salesTaxWithheldVal - discount;

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

  // --- Helpers for "Add Saved Item" sub-popup ---

  // ── Next Item Code auto-generation ──
  const getNextItemCode = (): string => {
    if (savedItems.length === 0) return 'ITEM-001';

    const prefixCounts: Record<string, { maxNum: number; count: number }> = {};
    for (const item of savedItems) {
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

    const prefixes = Object.keys(prefixCounts);
    if (prefixes.length === 0) return 'ITEM-001';

    const bestPrefix = prefixes.reduce((a, b) =>
      prefixCounts[a].count >= prefixCounts[b].count ? a : b
    );

    const nextNum = prefixCounts[bestPrefix].maxNum + 1;
    const padLength = String(prefixCounts[bestPrefix].maxNum).length;
    return `${bestPrefix}${String(nextNum).padStart(padLength, '0')}`;
  };

  // ── HS Code autocomplete functions for Add Saved Item sub-modal ──
  const searchNewHSCodes = (query: string) => {
    if (newHsCodeSearchRef.current) {
      clearTimeout(newHsCodeSearchRef.current);
    }
    if (!query || query.trim().length === 0) {
      setNewHsCodeOptions([]);
      setNewHsCodeSearchOpen(false);
      return;
    }
    newHsCodeSearchRef.current = setTimeout(async () => {
      try {
        setNewHsCodeSearching(true);
        const results = await masterDataService.getHSCodes(query.trim(), 15);
        setNewHsCodeOptions(results);
        setNewHsCodeHighlightIndex(-1);
        setNewHsCodeSearchOpen(results.length > 0);
      } catch {
        setNewHsCodeOptions([]);
        setNewHsCodeSearchOpen(false);
      } finally {
        setNewHsCodeSearching(false);
      }
    }, 250);
  };

  const selectNewHsCode = async (code: string) => {
    setNewHsCode(code);
    setNewHsCodeOptions([]);
    setNewHsCodeSearchOpen(false);
    setNewHsCodeHighlightIndex(-1);
    validateNewHsCode(code);
    // Auto-focus Product Description
    setTimeout(() => {
      document.getElementById('newProductDescription')?.focus();
    }, 100);
  };

  const handleNewHsCodeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!newHsCodeSearchOpen || newHsCodeOptions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setNewHsCodeHighlightIndex((prev) =>
        prev < newHsCodeOptions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setNewHsCodeHighlightIndex((prev) =>
        prev > 0 ? prev - 1 : newHsCodeOptions.length - 1
      );
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (newHsCodeHighlightIndex >= 0 && newHsCodeHighlightIndex < newHsCodeOptions.length) {
        selectNewHsCode(newHsCodeOptions[newHsCodeHighlightIndex].code);
      }
    } else if (e.key === 'Escape') {
      setNewHsCodeSearchOpen(false);
      setNewHsCodeHighlightIndex(-1);
    }
  };

  const validateNewHsCode = async (code: string) => {
    if (!code || code.trim() === '') {
      setNewHsCodeValid(null);
      setNewHsCodeError('');
      setNewHsCodeUoms([]);
      setNewDefaultUom('');
      return;
    }
    setIsValidatingNewHsCode(true);
    try {
      const result = await masterDataService.validateHSCode(code.trim());
      if (result.valid) {
        setNewHsCodeValid(true);
        setNewHsCodeError('');

        // Fetch relevant UOMs for this HS code
        try {
          setNewHsCodeUomsLoading(true);
          setNewDefaultUom('');
          const uoms = await masterDataService.getHsUom(code.trim(), 3);
          if (uoms && uoms.length > 0) {
            setNewHsCodeUoms(uoms);
            if (uoms.length === 1) {
              setNewDefaultUom(uoms[0].name);
            }
          } else {
            setNewHsCodeUoms([]);
          }
        } catch {
          setNewHsCodeUoms([]);
        } finally {
          setNewHsCodeUomsLoading(false);
        }
      } else {
        setNewHsCodeValid(false);
        setNewHsCodeError('HS Code not found in FBR database');
        setNewHsCodeUoms([]);
      }
    } catch (error) {
      console.error('Error validating HS code:', error);
      setNewHsCodeValid(false);
      setNewHsCodeError('Error validating HS Code');
      setNewHsCodeUoms([]);
    } finally {
      setIsValidatingNewHsCode(false);
    }
  };

  // Fetch tax rates when transaction type changes in Add Saved Item sub-modal
  useEffect(() => {
    if (!newTransactionType || !masterData?.transaction_types?.length) {
      setNewTaxRateOptions([]);
      return;
    }

    const fetchTaxRates = async () => {
      try {
        setNewTaxRatesLoading(true);
        const tt = masterData.transaction_types.find(
          (t: any) => t.name === newTransactionType || t.code === newTransactionType
        );
        if (tt) {
          const rates = await masterDataService.getTaxRatesByTransactionType(tt.code);
          if (rates && rates.length > 0) {
            setNewTaxRateOptions(rates);
            if (rates.length === 1) {
              setNewDefaultRate(rates[0].rate);
            }
            return;
          }
        }
        setNewTaxRateOptions([]);
      } catch {
        setNewTaxRateOptions([]);
      } finally {
        setNewTaxRatesLoading(false);
      }
    };

    fetchTaxRates();
  }, [newTransactionType, masterData?.transaction_types]);

  const resetNewItemForm = () => {
    setNewItemCode('');
    setNewItemName('');
    setNewHsCode('');
    setNewHsCodeValid(null);
    setNewHsCodeError('');
    setNewProductDescription('');
    setNewDefaultUom('');
    setNewDefaultRate('');
    setNewTransactionType('');
    setNewSroScheduleNo('');
    setNewSroItemSerialNo('');
    setNewHsCodeUoms([]);
    setNewHsCodeUomsLoading(false);
    setNewTaxRateOptions([]);
    setNewTaxRatesLoading(false);
    setNewHsCodeOptions([]);
    setNewHsCodeSearchOpen(false);
    setNewHsCodeHighlightIndex(-1);
  };

  const handleAddSavedItem = async () => {
    if (!newItemCode || !newItemName || !newHsCode || !newProductDescription || !newDefaultUom || !newDefaultRate || !newTransactionType) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setIsSavingNewItem(true);

      const createdItem = await api.auth.createSavedProduct({
        item_code: newItemCode,
        item_name: newItemName,
        hs_code: newHsCode,
        product_description: newProductDescription,
        default_uom: newDefaultUom,
        default_rate: newDefaultRate,
        default_sale_type: newTransactionType,
        transaction_type: newTransactionType,
        sro_schedule_no: newSroScheduleNo || undefined,
        sro_item_serial_no: newSroItemSerialNo || undefined,
      });

      if (createdItem.fbr_validated) {
        toast.success('Item created and HS Code validated with FBR!');
      } else {
        toast.warning('Item created but HS Code validation failed');
      }

      // Refresh saved items list
      const updatedItems = await api.auth.getSavedProducts(true);
      setSavedItems(updatedItems || []);

      // Auto-select the newly created item in the main modal
      if (createdItem && createdItem.id) {
        const newId = createdItem.id.toString();
        setModalSelectedSavedItem(newId);
        setModalItem(prev => ({
          ...prev,
          hsCode: createdItem.hs_code || '',
          productDescription: createdItem.product_description || '',
          rate: createdItem.default_rate || '',
          uoM: createdItem.default_uom || 'NOS',
          saleType: createdItem.transaction_type || prev.saleType,
          sroScheduleNo: createdItem.sro_schedule_no || '',
          sroItemSerialNo: createdItem.sro_item_serial_no || '',
        }));
      }

      setIsAddSavedItemModalOpen(false);
      resetNewItemForm();
    } catch (error: any) {
      console.error('Error creating saved item:', error);
      toast.error(error.message || 'Failed to create item');
    } finally {
      setIsSavingNewItem(false);
    }
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

    // If this is NOT the first item, validate transaction type matches first item
    if (index > 0 && items.length > 0) {
      const firstItemSaleType = items[0].saleType;
      if (firstItemSaleType && ttName && ttName.trim() !== firstItemSaleType.trim()) {
        toast.error(`Cannot select this item. Transaction type mismatch. Please select an item with transaction type matching the first item.`);
        return;
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

    // Filter saved buyers based on input (search by name or NTN/CNIC)
    if (value.trim().length > 0) {
      const searchTerm = value.toLowerCase();
      const filtered = savedBuyers.filter(buyer =>
        buyer.buyer_business_name.toLowerCase().includes(searchTerm) ||
        (buyer.buyer_ntn_cnic && buyer.buyer_ntn_cnic.toLowerCase().includes(searchTerm))
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

      // Auto-calculate withholding tax when income_tax_type or value_sales_excluding_st changes
      if (field === 'incomeTaxType' || field === 'valueSalesExcludingST') {
        const valueExclTax = Number(updatedItems[index].valueSalesExcludingST) || 0;
        const rate = updatedItems[index].incomeTaxType === '236H' ? 0.005 : 0.001;
        updatedItems[index].withholdingTaxAmount = parseFloat((valueExclTax * rate).toFixed(2));
      }

      // Auto-calculate item rate when quantity or value_sales_excluding_st changes
      if (field === 'quantity' || field === 'valueSalesExcludingST') {
        const qty = Number(updatedItems[index].quantity) || 0;
        const val = Number(updatedItems[index].valueSalesExcludingST) || 0;
        updatedItems[index].itemRate = qty > 0 ? parseFloat((val / qty).toFixed(2)) : 0;
      }

      // Auto-calculate when Value Excl. Sales Tax, Fixed/Retail Price, Further Tax, Discount, Extra Tax, or FED Payable is updated
      if (field === 'valueSalesExcludingST' || field === 'fixedNotifiedValueOrRetailPrice' || field === 'furtherTax' || field === 'discount' || field === 'extraTax' || field === 'fedPayable' || field === 'salesTaxWithheldAtSource') {
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
          } else if (!manualFurtherTax.has(index) && field !== 'discount' && buyerRegistrationType === 'Unregistered') {
            furtherTax = baseValue * 0.04;
          }

          const extraTax = Number(updatedItems[index].extraTax) || 0;
          const fedPayable = Number(updatedItems[index].fedPayable) || 0;
          const salesTaxWithheldVal = Number(updatedItems[index].salesTaxWithheldAtSource) || 0;
          // Total Value (Inc. Tax) = Base Value + Sales Tax + Further Tax + Extra Tax + FED Payable - Sales Tax Withheld - Discount
          const totalValue = baseValue + salesTax + furtherTax + extraTax + fedPayable - salesTaxWithheldVal - discount;

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
    if (buyerRegistrationType === 'Registered' && !buyerNTNCNIC.trim()) {
      toast.error('Buyer NTN/CNIC is required for registered buyers');
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
      item_rate: item.itemRate || 0,
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
      sro_item_serial_no: item.sroItemSerialNo || undefined,
      // Internal fields (not sent to FBR)
      income_tax_type: item.incomeTaxType || '236G',
      withholding_tax_amount: item.withholdingTaxAmount || 0
    }));

    // Derive invoice-level income_tax from first item (backward compat)
    const invoiceIncomeTax = items.length > 0 ? (items[0].incomeTaxType || '236G') : '236G';

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
      income_tax: invoiceIncomeTax,
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
      } else if (savedInvoiceId) {
        // Already saved by Validate flow — update instead of creating duplicate
        invoiceResponse = await api.invoices.update(savedInvoiceId, invoiceData);
      } else {
        invoiceResponse = await api.invoices.create(invoiceData);
      }

      const invoiceId = invoiceResponse.id || invoiceResponse.invoice?.id;
      if (invoiceId) {
        setSavedInvoiceId(invoiceId);
      }

      toast.success('Invoice saved as draft');
      clearForm();
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
        setPendingReset(true);
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

  /** Clear the entire form after a successful post so it's ready for a new invoice */
  const clearForm = () => {
    setInvoiceNo('');
    setInvoiceType('Sale Invoice');
    setInvoiceDate(new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Karachi' }));
    setInvoiceRefNo('');
    setScenarioId('SN001');
    setTransactionTypeId('');
    setSellerNTNCNIC('');
    setSellerBusinessName('');
    setSellerProvince('');
    setSellerProvinceCode('');
    setSellerAddress('');
    setBuyerNTNCNIC('');
    setBuyerBusinessName('');
    setBuyerProvince('');
    setBuyerProvinceCode('');
    setBuyerAddress('');
    setBuyerRegistrationType('Registered');
    setItems([]);
    setSavedInvoiceId(null);
    setIsValidated(false);
    setFieldErrors(new Set());
    setManualFurtherTax(new Set());
    setSelectedSavedItems({});
    setBuyerVerificationMessage(null);
    setRawQuantity('');
    setRawItemRate('');
    setValueExclTaxFocused(false);
    setFocusedFields(new Set());
    // Don't reset environment — it's auto-set from credentials
    // Trigger re-fetch of profile (seller info) and invoice number
    setPendingReset(false);
    setFormKey(prev => prev + 1);
  };

  /** Track last Enter press for double-enter detection on buttons/selects */
  const lastEnterRef = useRef<{ element: HTMLElement; time: number } | null>(null);

  /** Focus the next focusable element after the current target */
  const focusNextField = (form: HTMLElement, current: HTMLElement) => {
    const focusable = form.querySelectorAll<HTMLElement>(
      'input:not([disabled]):not([readonly]):not([tabindex="-1"]), ' +
      'select:not([disabled]):not([tabindex="-1"]), ' +
      'button:not([disabled]):not([tabindex="-1"]), ' +
      'textarea:not([disabled]):not([readonly]):not([tabindex="-1"]), ' +
      '[tabindex]:not([tabindex="-1"])'
    );
    const currentIndex = Array.from(focusable).indexOf(current);
    if (currentIndex >= 0 && currentIndex < focusable.length - 1) {
      focusable[currentIndex + 1]?.focus();
    }
  };

  const handleFormKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      const target = e.target as HTMLElement;
      // Textareas — Enter advances to next field; use Shift+Enter for new line
      if (target.tagName === 'TEXTAREA') {
        e.preventDefault();
        focusNextField(e.currentTarget, target);
        return;
      }

      // Buttons (including shadcn Select triggers) — double-Enter to advance,
      // first Enter lets the button handle normally (open dropdown / submit)
      if (target.tagName === 'BUTTON') {
        const now = Date.now();
        const last = lastEnterRef.current;
        if (last && last.element === target && now - last.time < 1000) {
          // Second Enter on the same button — advance to next field
          lastEnterRef.current = null;
          e.preventDefault();
          focusNextField(e.currentTarget, target);
          return;
        }
        lastEnterRef.current = { element: target, time: now };
        return; // First Enter — let the button handle it
      }

      // Inputs, selects, and other elements — single Enter advances
      e.preventDefault();
      focusNextField(e.currentTarget, target);
    }
  };

  return (
    <form onSubmit={handleFormSubmit} onKeyDown={handleFormKeyDown} className="space-y-6 h-full">
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
          <div className="shrink-0 flex md:flex-col gap-2 md:sticky top-4 self-center md:self-start order-1 md:order-none pt-0 md:pt-18 justify-center md:justify-start w-full md:w-auto">
            {/* Save Draft Button */}
            <Button
              variant="outline"
              size="icon"
              type="button"
              onClick={handleSaveDraft}
              disabled={isLoading || isSubmitting || isSaving || isValidating || isPosting || isValidated}
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
          <div className="flex-1 min-w-0 space-y-1 pb-24 sm:pb-4">
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
                    max={todayKarachi}
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
              <div className='flex gap-2 flex-wrap md:flex-nowrap xl:gap-0 xl:justify-between px-2 mb-2'>
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
                            ? savedBuyers.filter(b =>
                                b.buyer_business_name.toLowerCase().includes(buyerBusinessName.toLowerCase()) ||
                                (b.buyer_ntn_cnic && b.buyer_ntn_cnic.toLowerCase().includes(buyerBusinessName.toLowerCase()))
                              )
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
                          // Filter based on current input (name or NTN/CNIC)
                          const searchTerm = buyerBusinessName.toLowerCase();
                          const filtered = savedBuyers.filter(buyer =>
                            buyer.buyer_business_name.toLowerCase().includes(searchTerm) ||
                            (buyer.buyer_ntn_cnic && buyer.buyer_ntn_cnic.toLowerCase().includes(searchTerm))
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
                    <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-[156px] overflow-y-auto" role="listbox">
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
                <div className='w-full min-w-[80px] sm:w-[48%] md:w-[17%] xl:w-[120px]'>
                  <Label className='pl-3 text-[14px] font-bold' htmlFor="buyerRegistrationType">Type *</Label>
                  <Select value={buyerRegistrationType} onValueChange={(val) => setBuyerRegistrationType(val as 'Registered' | 'Unregistered')}>
                    <SelectTrigger className='!w-full' disabled={isVerifyingBuyer}>
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
                    <SelectTrigger disabled={(masterData?.provinces.length ?? 0) === 0} className="!text-[10px]">
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
            <div className="overflow-x-auto">
              <table className="w-full min-w-[605px] table-fixed bg-[#7c97f0] rounded-4xl flex-shrink-0">
              <thead>
                  <tr>
                    <th className="border-r-2 border-[#FFFFFF] w-[23%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Item Name</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[9%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Qty</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[14%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Value Excl. Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[8%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Rate</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[13%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Sales Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[13%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Further Tax</th>
                    <th className="border-r-2 border-[#FFFFFF] w-[11%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Total (Inc. Tax)</th>
                    <th className="w-[9%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Actions</th>
                  </tr>
                </thead>
                </table>
              <div className="text-center py-12 text-[#6d7175] dark:text-[#8c9196]">
              <p className="text-lg font-medium">No items added yet</p>
              <p className="text-sm mt-1">Click "+" to add invoice items</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div className='max-h-50 overflow-y-auto rounded-2xl min-w-[605px]'>
                {/*table 2 if invoice exist*/}
                <table className='w-full table-fixed'>
                  <thead className="sticky top-0 bg-[#7c97f0] z-10">
                    <tr>
                      <th className="border-r-2 border-[#FFFFFF] w-[23%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Item Name</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[9%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Qty</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[14%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Value Excl. Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[8%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Rate</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[13%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Sales Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[13%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Further Tax</th>
                      <th className="border-r-2 border-[#FFFFFF] w-[11%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Total (Inc. Tax)</th>
                      <th className="w-[9%] px-2 py-1 text-center text-[10px] lg:text-xs font-bold text-black uppercase tracking-wider align-middle">Actions</th>
                    </tr>
                  </thead>
                  <tbody className='divide-y divide-[#FFFFFF]'>
                    {items.map((item, index) => (
                      <tr key={index} className="group transition-colors duration-150 text-black bg-[#e7eaf1]">
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[23%] text-[11px] lg:text-[13px] truncate" title={item.productDescription}>{item.productDescription || '—'}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[9%] text-center text-[10px] lg:text-[11px]">{item.quantity || 0}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[14%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">{Number(item.valueSalesExcludingST).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[8%] text-center text-[11px] lg:text-[13px]">{item.rate || '—'}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[13%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">{Number(item.salesTaxApplicable).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[13%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">{Number(item.furtherTax).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="border-r-2 border-[#FFFFFF] py-1 px-2 align-middle w-[11%] text-right text-[9px] lg:text-[10px] whitespace-nowrap">{Number(item.totalValues).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="py-1 px-2 align-middle w-[9%]">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              type="button"
                              onClick={() => openEditModal(index)}
                              className="h-6 w-6 lg:h-7 lg:w-7 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-[#6d7175] hover:border-[#008060] hover:text-[#008060] dark:hover:border-[#00a876] dark:hover:text-[#00a876] hover:bg-[#f0f9f6] dark:hover:bg-[#0d3d2f]/30 transition-colors cursor-pointer"
                              title="Edit item"
                            >
                              <Pencil className="h-3 w-3 lg:h-3.5 lg:w-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => removeItem(index)}
                              className="h-6 w-6 lg:h-7 lg:w-7 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-red-500 hover:text-red-600 hover:border-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
                              title="Remove item"
                            >
                              <Trash2 className="h-3 w-3 lg:h-3.5 lg:w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="overflow-x-auto">
                {/*table 3 footer*/}
                <table className="w-full min-w-[605px] table-fixed border-2 border-blue-300 rounded-2xl border-separate border-spacing-0 bg-[#FFFFFF]">
                  <tfoot>
                    <tr className="font-normal text-black">
                      <td className="py-1 px-2 w-[32%] text-center font-bold">Totals:</td>
                      <td className="py-1 px-2 w-[14%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">
                        {items.reduce((sum, item) => sum + (Number(item.valueSalesExcludingST) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className='py-1 px-2 w-[8%]'></td>
                      <td className="py-1 px-2 w-[13%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">
                        {items.reduce((sum, item) => sum + (Number(item.salesTaxApplicable) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-1 px-2 w-[13%] text-right text-[10px] lg:text-[11px] whitespace-nowrap">
                        {items.reduce((sum, item) => sum + (Number(item.furtherTax) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-1 px-2 w-[11%] text-right text-[9px] lg:text-[10px] whitespace-nowrap">
                        {items.reduce((sum, item) => sum + (Number(item.totalValues) || 0), 0).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className='py-1 px-2 w-[9%]'></td>
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
                    
            /* Moves a single tiny gradient block around the 4 edges of the box */
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
                    
              /* 1st layer: Input background mask
                 2nd layer: A small glowing blue dot block
              */
              background-image:
                linear-gradient(#ffffff, #ffffff),
                linear-gradient(135deg, #60a5fa, #2563eb);
                    
              background-origin: border-box;
              background-clip: padding-box, border-box;
                    
              /* Crucial: Prevent the dot from repeating, and size it to a small 16px square */
              background-repeat: no-repeat, no-repeat;
              background-size: 100% 100%, 16px 16px;
                    
              animation: borderTravel 2.5s linear infinite;
            }
                    
            /* Dark mode support */
            html.dark .glow-border:focus {
              background-image:
                linear-gradient(#1e1e1e, #1e1e1e),
                linear-gradient(135deg, #93c5fd, #3b82f6);
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
            <div className="flex items-center justify-between px-6 py-1 border-b border-[#e1e3e5] dark:border-[#2e2e2e] bg-blue-100 rounded-t-2xl">
              <h4 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">
                {editingItemIndex !== null ? `Edit Item ${editingItemIndex + 1}` : 'Item Wise Sale'}
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
            <div className="px-6 pt-5 pb-5">
              <div className="flex flex-col md:flex-row gap-4">
                {/* LEFT COLUMN - 70% */}
                <div className="w-full md:w-[70%] flex flex-col justify-between">
                  {/* Header row with plus icon */}
                  {/* <div className="flex items-center justify-between mb-2 border-2 rounded-xl bg-blue-50 px-1">
                    <Label className="text-sm font-semibold">Quick Select from Saved Items</Label>
                    <div className='flex gap-2 text-sm font-semibold'>
                    <button
                      type="button"
                      onClick={() => {
                        setNewItemCode(getNextItemCode());
                        setNewTransactionType((masterData?.transaction_types?.[0]?.name) || '');
                        setIsAddSavedItemModalOpen(true);
                      }}
                      className="h-7 w-7 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-[#008060] hover:bg-[#f0f9f6] dark:hover:bg-[#0d3d2f]/30 transition-colors cursor-pointer"
                      title="Add new saved item"
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                    <label className='text-black pt-1'>Add New Item</label>
                    </div>
                  </div> */}
                  <div className='border-2 border-blue-500 rounded-2xl px-1 py-1 flex flex-col hover:bg-blue-50 focus-within:bg-blue-50'>
                    <div className='flex justify-between pr-1'>
                      {/* Saved Items Quick Select */}
                      <div className={`py-2 px-1 rounded-xl w-full ${
                          editingItemIndex !== null && editingItemIndex > 0 && items.length > 0 && modalSelectedSavedItem && (() => {
                            const si = savedItems.find(item => item.id.toString() === modalSelectedSavedItem);
                            const firstSaleType = items[0]?.saleType;
                            return si && si.transaction_type && firstSaleType && si.transaction_type.trim() !== firstSaleType.trim();
                          })()
                            ? 'bg-red-50 border-red-300'
                            : ''
                        }`}>
                          {/* Header row with plus icon */}
                          {/* <div className="flex items-center justify-between mb-2 border-2 rounded-xl bg-blue-100 px-1">
                            <Label className="text-sm font-semibold">Quick Select from Saved Items</Label>
                            <div className='flex gap-2 text-sm font-semibold'>
                            <button
                              type="button"
                              onClick={() => { setIsAddSavedItemModalOpen(true); }}
                              className="h-7 w-7 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-[#008060] hover:bg-[#f0f9f6] dark:hover:bg-[#0d3d2f]/30 transition-colors cursor-pointer"
                              title="Add new saved item"
                            >
                              <Plus className="h-3.5 w-3.5" />
                            </button>
                            <label className='text-black pt-1'>Add New Item</label>
                            </div>
                          </div> */}
                          {savedItems.length > 0 ? (
                            <Select value={modalSelectedSavedItem} onValueChange={handleModalItemSelect}>
                              <SelectTrigger className="glow-border">
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
                                      <span className="text-xs text-gray-500 ">
                                        {savedItem.hs_code} - {savedItem.product_description}
                                      </span>
                                    </div>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>

                          ) : (
                            <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                              No saved items yet. Click "+" to create one.
                            </p>
                          )}
                          {editingItemIndex !== null && editingItemIndex > 0 && items.length > 0 && (
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
                        
                      <div className='pt-2'>
                        <button
                        type="button"
                        onClick={() => {
                          setNewItemCode(getNextItemCode());
                          setNewTransactionType((masterData?.transaction_types?.[0]?.name) || '');
                          setIsAddSavedItemModalOpen(true);
                        }}
                        className=" h-7 w-7 rounded-lg border border-[#c9cccf] dark:border-[#3e3e3e] bg-white dark:bg-[#1a1a1a] flex items-center justify-center text-[#008060] hover:bg-[#f0f9f6] dark:hover:bg-[#0d3d2f]/30 transition-colors cursor-pointer"
                        title="Add new saved item"
                        >
                        <Plus className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                      
                    {/* Product Description */}
                    <div className="px-1">
                      <Label className="text-[14px] font-bold">Product Description *</Label>
                      <Input
                        className="w-full text-[12px] h-[30px] glow-border"
                        type="text"
                        value={modalItem.productDescription}
                        onChange={(e) => updateModalItem('productDescription', e.target.value)}
                        placeholder="Enter product description"
                        required
                      />
                    </div>                    
                  </div>

                  {/* Quantity + Item Rate */}
                  <div className="flex flex-wrap sm:flex-nowrap justify-between gap-2 border-2 border-blue-600 rounded-2xl px-1 py-1 hover:bg-blue-50 focus-within:bg-blue-50">
                    <div className="flex-1 min-w-[100px]">
                      <Label>Quantity *</Label>
                      <Input
                        className="w-full text-[12px] h-[30px] text-right glow-border"
                        type="text"
                        inputMode="decimal"
                        maxLength={10}
                        value={(() => {
                          if (focusedFields.has('quantity')) return rawQuantity;
                          const num = modalItem.quantity;
                          if (!num) return '';
                          return Number(num).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        })()}
                        onFocus={() => {
                          setFocusedFields(prev => new Set(prev).add('quantity'));
                          setRawQuantity(modalItem.quantity ? String(modalItem.quantity) : '');
                        }}
                        onBlur={() => {
                          setFocusedFields(prev => { const next = new Set(prev); next.delete('quantity'); return next; });
                          setRawQuantity('');
                          // Commit final parsed value
                          const qty = parseFloat(rawQuantity);
                          if (!isNaN(qty) && qty >= 0) {
                            updateModalItem('quantity', qty);
                          }
                          // Auto-calculate Value Excl. Sales Tax from Quantity × Item Rate
                          const finalQty = !isNaN(qty) && qty > 0 ? qty : (Number(modalItem.quantity) || 0);
                          const rate = Number(modalItem.itemRate) || 0;
                          if (finalQty > 0 && rate > 0) {
                            updateModalItem('valueSalesExcludingST', parseFloat((finalQty * rate).toFixed(2)));
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value;
                          // Allow partial decimal input like "12." or ".5"
                          if (val !== '' && !/^\d*\.?\d*$/.test(val)) return;
                          if (val === '') {
                            setRawQuantity('');
                            updateModalItem('quantity', 0);
                            return;
                          }
                          setRawQuantity(val);
                          // Only update actual quantity when it's a valid number
                          const num = parseFloat(val);
                          if (!isNaN(num) && num <= 9999999) {
                            updateModalItem('quantity', num);
                          }
                        }}
                        required
                      />
                    </div>
                    <div className="flex-1 min-w-[100px]">
                      <Label>Item Rate</Label>
                      <Input
                        className="w-full text-[12px] h-[30px] text-right glow-border"
                        type="text"
                        inputMode="decimal"
                        maxLength={14}
                        value={(() => {
                          if (focusedFields.has('itemRate')) return rawItemRate;
                          if (!modalItem.itemRate) return '';
                          return Number(modalItem.itemRate).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        })()}
                        onFocus={() => {
                          setFocusedFields(prev => new Set(prev).add('itemRate'));
                          setRawItemRate(modalItem.itemRate ? String(modalItem.itemRate) : '');
                        }}
                        onBlur={() => {
                          setFocusedFields(prev => { const next = new Set(prev); next.delete('itemRate'); return next; });
                          setRawItemRate('');
                          // Commit final parsed value
                          const rate = parseFloat(rawItemRate);
                          if (!isNaN(rate) && rate >= 0) {
                            updateModalItem('itemRate', rate);
                          }
                          // Auto-calculate Value Excl. Sales Tax from Quantity × Item Rate
                          const finalRate = !isNaN(rate) && rate > 0 ? rate : (Number(modalItem.itemRate) || 0);
                          const qty = Number(modalItem.quantity) || 0;
                          if (qty > 0 && finalRate > 0) {
                            updateModalItem('valueSalesExcludingST', parseFloat((qty * finalRate).toFixed(2)));
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value;
                          // Allow partial decimal input like "1." or ".5"
                          if (val !== '' && !/^\d*\.?\d*$/.test(val)) return;
                          if (val === '' || val === '-') {
                            setRawItemRate('');
                            updateModalItem('itemRate', 0);
                            return;
                          }
                          setRawItemRate(val);
                          // Only update actual rate when it's a valid number
                          const num = parseFloat(val);
                          if (!isNaN(num) && num <= 99999999999) {
                            updateModalItem('itemRate', num);
                          }
                        }}
                        placeholder="Per unit Rate"
                      />
                      {/* <p className="text-[10px] text-gray-400 mt-0.5">
                        Value Excl. Tax / Quantity
                      </p> */}
                    </div>
                  </div>

                  {/* Value Excl. Sales Tax + Fixed/Retail Price + Discount */}
                  <div className="flex flex-wrap sm:flex-nowrap justify-between gap-2 border-2 border-blue-600 rounded-2xl px-1 py-1 hover:bg-blue-50 focus-within:bg-blue-50">
                    <div className='w-full min-w-[120px] flex-1'>
                      <Label>Value Excl. Sales Tax *</Label>
                      <Input
                        className="w-full text-[12px] h-[30px] text-right glow-border"
                        type="text"
                        inputMode="decimal"
                        maxLength={14}
                        value={(() => {
                          const num = modalItem.valueSalesExcludingST;
                          if (num === 0) return '0';
                          if (valueExclTaxFocused) return num.toString();
                          return Number(num).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        })()}
                        onFocus={(e) => { setValueExclTaxFocused(true); e.target.select(); }}
                        onBlur={() => setValueExclTaxFocused(false)}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === '' || val === '-') {
                            updateModalItem('valueSalesExcludingST', 0);
                            return;
                          }
                          if (/^\d*\.?\d*$/.test(val)) {
                            const cleaned = val.replace(/^0+(\d)/, '$1');
                            const num = parseFloat(cleaned);
                            if (isNaN(num)) return;
                            if (num > 99999999999) return;
                            updateModalItem('valueSalesExcludingST', num);
                          }
                        }}
                        required
                      />
                    </div>
                    <div className='w-full min-w-[120px] flex-1'>
                      <Label>Fixed/Retail Price *</Label>
                      <Input
                        className={`w-full text-[12px] h-[30px] text-right glow-border ${errorBorder('fixedPrice')}`}
                        type="text"
                        inputMode="decimal"
                        maxLength={14}
                        value={formatAmount('fixedPrice', modalItem.fixedNotifiedValueOrRetailPrice ?? '0')}
                        onFocus={(e) => {
                          setFocusedFields(prev => new Set(prev).add('fixedPrice'));
                          if (modalItem.fixedNotifiedValueOrRetailPrice === '0') e.target.select();
                        }}
                        onBlur={() => {
                          setFocusedFields(prev => { const next = new Set(prev); next.delete('fixedPrice'); return next; });
                          const v = Number(modalItem.valueSalesExcludingST) || 0;
                          const f = Number(modalItem.fixedNotifiedValueOrRetailPrice) || 0;
                          if (f > 0 && f < v) {
                            setFieldErrors(prev => new Set(prev).add('fixedPrice'));
                            toast.error('Fixed/Retail Price must be equal to or greater than Value Excl. Sales Tax');
                          } else {
                            setFieldErrors(prev => { const next = new Set(prev); next.delete('fixedPrice'); return next; });
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val.length > 14) return;
                          setFieldErrors(prev => { const next = new Set(prev); next.delete('fixedPrice'); return next; });
                          if (val === '' || val === '-') {
                            updateModalItem('fixedNotifiedValueOrRetailPrice', '0');
                            return;
                          }
                          // Only allow valid decimal input and strip leading zeros (like Value Excl. Sales Tax does via parseFloat)
                          if (/^\d*\.?\d*$/.test(val)) {
                            const cleaned = val.replace(/^0+(\d)/, '$1');
                            updateModalItem('fixedNotifiedValueOrRetailPrice', cleaned);
                          }
                        }}
                        required
                      />
                    </div>
                    <div className='w-full min-w-[120px] flex-1'>
                      <Label>Discount</Label>
                      <Input
                        className={`w-full text-[12px] h-[30px] text-right glow-border ${errorBorder('discount')}`}
                        type="text"
                        inputMode="decimal"
                        maxLength={14}
                        value={formatAmount('discount', modalItem.discount ?? 0)}
                        onFocus={() => setFocusedFields(prev => new Set(prev).add('discount'))}
                        onBlur={() => {
                          setFocusedFields(prev => { const next = new Set(prev); next.delete('discount'); return next; });
                          const v = Number(modalItem.valueSalesExcludingST) || 0;
                          const d = Number(modalItem.discount) || 0;
                          if (d > v) {
                            setFieldErrors(prev => new Set(prev).add('discount'));
                            toast.error('Discount cannot exceed Value Excl. Sales Tax');
                          } else {
                            setFieldErrors(prev => { const next = new Set(prev); next.delete('discount'); return next; });
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === '' || val === '-') {
                            setFieldErrors(prev => { const next = new Set(prev); next.delete('discount'); return next; });
                            updateModalItem('discount', 0);
                            return;
                          }
                          if (val.length > 14) return;
                          const num = parseFloat(val);
                          if (isNaN(num)) return;
                          if (num > 99999999999) return;
                          setFieldErrors(prev => { const next = new Set(prev); next.delete('discount'); return next; });
                          updateModalItem('discount', num);
                        }}
                      />
                    </div>
                  </div>

                  {/* Sales Tax Applicable + Further Tax + Sales Tax Withheld */}
                  <div className='border-2 border-blue-600 rounded-2xl px-1 py-1 hover:bg-blue-50 focus-within:bg-blue-50'>
                    <div className="flex flex-wrap sm:flex-nowrap justify-between gap-2">
                      <div className="flex-1 min-w-[100px]">
                        <Label>Sales Tax Applicable *</Label>
                        <Input
                          className="w-full text-[12px] h-[30px] text-right glow-border"
                          type="text"
                          value={modalItem.salesTaxApplicable ? Number(modalItem.salesTaxApplicable).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''}
                          readOnly
                          required
                        />
                      </div>
                      <div className="flex-1 min-w-[100px]">
                        <Label>Further Tax {buyerRegistrationType === 'Unregistered' && '*'}</Label>
                        <Input
                          className="w-full text-[12px] h-[30px] text-right glow-border"
                          type="text"
                          inputMode="decimal"
                          maxLength={13}
                          value={formatAmount('furtherTax', modalItem.furtherTax ?? 0)}
                          onFocus={() => setFocusedFields(prev => new Set(prev).add('furtherTax'))}
                          onBlur={() => setFocusedFields(prev => { const next = new Set(prev); next.delete('furtherTax'); return next; })}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val.length > 13) return;
                            updateModalItem('furtherTax', val);
                          }}
                          required={buyerRegistrationType === 'Unregistered'}
                        />
                      </div>
                      <div className="flex-1 min-w-[100px]">
                        <Label>Sales Tax Withheld *</Label>
                        <Input
                          className={`w-full text-[12px] h-[30px] text-right glow-border ${errorBorder('salesTaxWithheld')}`}
                          type="text"
                          inputMode="decimal"
                          maxLength={11}
                          value={formatAmount('salesTaxWithheld', modalItem.salesTaxWithheldAtSource)}
                          onFocus={() => setFocusedFields(prev => new Set(prev).add('salesTaxWithheld'))}
                          onBlur={() => {
                            setFocusedFields(prev => { const next = new Set(prev); next.delete('salesTaxWithheld'); return next; });
                            const s = Number(modalItem.salesTaxApplicable) || 0;
                            const w = Number(modalItem.salesTaxWithheldAtSource) || 0;
                            if (w > s) {
                              setFieldErrors(prev => new Set(prev).add('salesTaxWithheld'));
                              toast.error('Sales Tax Withheld cannot exceed Sales Tax Applicable');
                            } else {
                              setFieldErrors(prev => { const next = new Set(prev); next.delete('salesTaxWithheld'); return next; });
                            }
                          }}
                          onChange={(e) => {
                            setFieldErrors(prev => { const next = new Set(prev); next.delete('salesTaxWithheld'); return next; });
                            updateModalItem('salesTaxWithheldAtSource', e.target.value);
                          }}
                          placeholder="0"
                          required
                        />
                      </div>
                    </div>

                    {/* Extra Tax + FED Payable */}
                    <div className="flex flex-wrap sm:flex-nowrap justify-between gap-2">
                      <div className="flex-1 min-w-[100px]">
                        <Label>Extra Tax</Label>
                        <Input
                          className="w-full text-[12px] h-[30px] text-right glow-border"
                          type="text"
                          inputMode="decimal"
                          maxLength={11}
                          value={formatAmount('extraTax', modalItem.extraTax ?? 0)}
                          onFocus={() => setFocusedFields(prev => new Set(prev).add('extraTax'))}
                          onBlur={() => setFocusedFields(prev => { const next = new Set(prev); next.delete('extraTax'); return next; })}
                          onChange={(e) => {
                            updateModalItem('extraTax', e.target.value);
                          }}
                        />
                      </div>
                      <div className="flex-1 min-w-[100px]">
                        <Label>FED Payable</Label>
                        <Input
                          className="w-full text-[12px] h-[30px] text-right glow-border"
                          type="text"
                          inputMode="decimal"
                          maxLength={14}
                          value={formatAmount('fedPayable', modalItem.fedPayable ?? 0)}
                          onFocus={() => setFocusedFields(prev => new Set(prev).add('fedPayable'))}
                          onBlur={() => setFocusedFields(prev => { const next = new Set(prev); next.delete('fedPayable'); return next; })}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val === '' || val === '-') {
                              updateModalItem('fedPayable', 0);
                              return;
                            }
                            if (val.length > 14) return;
                            const num = parseFloat(val);
                            if (isNaN(num)) return;
                            updateModalItem('fedPayable', num);
                          }}
                        />
                      </div>
                      <div className="flex-1 min-w-[100px] hidden sm:block"></div>
                    </div>
                  </div>

                  {/* Income Tax Type + Withholding Tax (per item, internal only) */}
                  <div className='border-2 border-blue-600 rounded-2xl px-1 py-1 hover:bg-blue-50 focus-within:bg-blue-50'>
                    <div className="flex flex-wrap sm:flex-nowrap justify-between gap-2">
                      <div className="w-full flex-1 min-w-[100px]">
                        <Label htmlFor="modalIncomeTax">Income Tax Type</Label>
                        <Select value={modalItem.incomeTaxType || '236G'} onValueChange={(val) => updateModalItem('incomeTaxType', val)}>
                          <SelectTrigger className="text-[12px] h-[30px] glow-border">
                            <SelectValue placeholder="236G" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="236G">236G (0.1%)</SelectItem>
                            <SelectItem value="236H">236H (0.5%)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="w-full flex-1 min-w-[100px]">
                        <Label>Withholding Tax</Label>
                        <Input
                          type="text"
                          inputMode="decimal"
                          maxLength={11}
                          value={formatAmount('withholdingTax', modalItem.withholdingTaxAmount ?? 0)}
                          onFocus={() => setFocusedFields(prev => new Set(prev).add('withholdingTax'))}
                          onBlur={() => setFocusedFields(prev => { const next = new Set(prev); next.delete('withholdingTax'); return next; })}
                          onChange={(e) => {
                            updateModalItem('withholdingTaxAmount', e.target.value);
                          }}
                          className="w-full text-[12px] h-[30px] text-right glow-border"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* RIGHT COLUMN - 30% */}
                <div className="w-full md:w-[30%] flex flex-col gap-3 border-2 border-blue-600 rounded-2xl p-3 bg-blue-50">
                  {/* Sale Type */}
                  <div>
                    <Label>Sale Type</Label>
                    <Select value={modalItem.saleType}>
                      <SelectTrigger disabled tabIndex={-1} className="text-[12px] h-[30px] w-full bg-gray-50 dark:bg-gray-800 cursor-not-allowed">
                        <SelectValue placeholder="Goods at standard rate (default)" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[200px]">
                        {(masterData?.transaction_types ?? []).map((type) => (
                          <SelectItem key={type.code} value={type.name}>
                            {type.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* HS Code + Tax Rate */}
                  <div className="flex justify-between gap-2">
                    <div className="flex-1">
                      <Label className="text-[14px] font-bold">HS Code *</Label>
                      <Input
                        className="w-full text-[12px] h-[30px]"
                        type="text"
                        value={modalItem.hsCode}
                        onChange={(e) => updateModalItem('hsCode', e.target.value)}
                        placeholder="HS Code"
                        required
                        readOnly
                        tabIndex={-1}
                      />
                    </div>
                    <div className="flex-1">
                      <Label>Tax Rate *</Label>
                      <Input
                        className="w-full text-[12px] h-[30px]"
                        type="text"
                        value={modalItem.rate}
                        onChange={(e) => updateModalItem('rate', e.target.value)}
                        placeholder="e.g., 18"
                        required
                        readOnly
                        tabIndex={-1}
                      />
                    </div>
                  </div>

                  {/* Unit of Measurement + Total Value */}
                  <div className="flex-1">
                    <Label>Unit of Measurement *</Label>
                    <Input
                      className="w-full text-[12px] h-[30px]"
                      type="text"
                      value={modalItem.uoM}
                      readOnly
                      tabIndex={-1}
                      required
                    />
                  </div>
                  <div className="flex-1">
                    <Label>Total Value (Inc. Tax) *</Label>
                    <Input
                      className="w-full text-[12px] h-[30px] text-right"
                      type="text"
                      value={modalItem.totalValues ? Number(modalItem.totalValues).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''}
                      readOnly
                      tabIndex={-1}
                      required
                    />
                  </div>

                  {/* SRO Schedule No + SRO Item Serial No */}
                  <div className="flex-1">
                    <Label>SRO Schedule No</Label>
                    <Input
                      className="w-full text-[12px] h-[30px]"
                      value={modalItem.sroScheduleNo}
                      onChange={(e) => updateModalItem('sroScheduleNo', e.target.value)}
                      placeholder="Select Item"
                      disabled={!modalItem.rate}
                      tabIndex={-1}
                    />
                  </div>
                  <div className="flex-1">
                    <Label>SRO Item Serial No</Label>
                    <Input
                      className="w-full text-[12px] h-[30px]"
                      value={modalItem.sroItemSerialNo}
                      onChange={(e) => updateModalItem('sroItemSerialNo', e.target.value)}
                      placeholder="Optional"
                      readOnly
                      tabIndex={-1}
                    />
                  </div>

                  {/* Footer Buttons */}
                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e] mt-auto">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => {
                        setIsItemModalOpen(false);
                        setEditingItemIndex(null);
                      }}
                      className="h-8 w-8 text-red-500 hover:text-red-600 border-red-300 dark:border-red-800"
                      title="Cancel"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleModalSave}
                      className="h-8 w-8 rounded-lg border-blue-300 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100"
                      title={editingItemIndex !== null ? 'Save Changes' : 'Add Item'}
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Sub-popup for creating a new saved item */}
              {isAddSavedItemModalOpen && (
                <>
                  {/* Sub-backdrop */}
                  <div
                    className="fixed inset-0 z-[60] bg-black/30"
                    onClick={() => {
                      setIsAddSavedItemModalOpen(false);
                      resetNewItemForm();
                    }}
                  />
                  {/* Sub-modal content */}
                  <div className="fixed inset-0 z-[60] flex items-start justify-center pt-2 sm:pt-10 overflow-y-auto">
                    <div
                      ref={addSavedItemModalRef}
                      className="relative w-[95vw] max-w-2xl bg-white dark:bg-[#161616] rounded-2xl shadow-2xl border-2 border-black dark:border-[#2e2e2e] mb-10"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') {
                          setIsAddSavedItemModalOpen(false);
                          resetNewItemForm();
                          return;
                        }
                        if (e.key !== 'Tab') return;
                        const modal = addSavedItemModalRef.current;
                        if (!modal) return;
                        const focusable = modal.querySelectorAll<HTMLElement>(
                          'input:not([disabled]):not([readonly]):not([tabindex="-1"]), select:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])'
                        );
                        if (focusable.length === 0) return;
                        const first = focusable[0];
                        const last = focusable[focusable.length - 1];
                        if (e.shiftKey) {
                          if (document.activeElement === first) {
                            e.preventDefault();
                            last.focus();
                          }
                        } else {
                          if (document.activeElement === last) {
                            e.preventDefault();
                            first.focus();
                          }
                        }
                      }}
                    >
                      {/* Sub-modal Header */}
                      <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e2e] bg-blue-100 rounded-t-xl">
                        <h4 className="text-base sm:text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">
                          Add New Saved Item
                        </h4>
                        <button
                          type="button"
                          onClick={() => {
                            setIsAddSavedItemModalOpen(false);
                            resetNewItemForm();
                          }}
                          className="p-2 rounded-lg hover:bg-[#f3f4f6] dark:hover:bg-[#2e2e2e] text-[#6d7175] transition-colors"
                        >
                          <X className="h-5 w-5" />
                        </button>
                      </div>

                      {/* Sub-modal Body */}
                      <div className="p-4 sm:p-6 max-h-[70vh] sm:max-h-[80vh] overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                        {/* Item Code */}
                        <div>
                          <Label htmlFor="newItemCode">Item Code *</Label>
                          <Input
                            id="newItemCode"
                            type="text"
                            value={newItemCode}
                            onChange={(e) => setNewItemCode(e.target.value)}
                            placeholder="e.g., ITEM-001"
                            className="mt-1 text-[12px] h-[30px] w-full glow-border"
                            required
                          />
                        </div>

                        {/* Item Name */}
                        <div>
                          <Label htmlFor="newItemName">Item Name *</Label>
                          <Input
                            id="newItemName"
                            type="text"
                            value={newItemName}
                            onChange={(e) => setNewItemName(e.target.value)}
                            placeholder="e.g., Laptop Computer"
                            className="mt-1 text-[12px] h-[30px] w-full glow-border"
                            required
                          />
                        </div>

                        {/* HS Code with FBR validation + autocomplete */}
                        <div ref={newHsCodeDropdownRef}>
                          <Label htmlFor="newHsCode" className="flex items-center gap-2">
                            HS Code *
                            {newHsCodeValid === true && (
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            )}
                            {newHsCodeValid === false && (
                              <XCircle className="h-4 w-4 text-red-600" />
                            )}
                          </Label>
                          <div className="relative">
                            <Input
                              id="newHsCode"
                              type="text"
                              value={newHsCode}
                              onChange={(e) => {
                                setNewHsCode(e.target.value);
                                setNewHsCodeValid(null);
                                setNewHsCodeError('');
                                setNewHsCodeUoms([]);
                                setNewDefaultUom('');
                                searchNewHSCodes(e.target.value);
                              }}
                              onFocus={() => {
                                if (newHsCodeOptions.length > 0) setNewHsCodeSearchOpen(true);
                              }}
                              onBlur={() => {
                                setTimeout(() => {
                                  setNewHsCodeSearchOpen(false);
                                  setNewHsCodeOptions([]);
                                }, 200);
                                if (newHsCode.trim()) validateNewHsCode(newHsCode);
                              }}
                              onKeyDown={handleNewHsCodeKeyDown}
                              placeholder="Type to search HS Code..."
                              className="mt-1 pr-10 text-[12px] h-[30px] w-full glow-border"
                              autoComplete="off"
                              required
                            />
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 mt-0.5 pointer-events-none">
                              {(isValidatingNewHsCode || newHsCodeSearching) && (
                                <Loader2 className="h-4 w-4 animate-spin text-[#008060]" />
                              )}
                            </div>
                            {newHsCodeSearchOpen && newHsCodeOptions.length > 0 && (
                              <div className="absolute left-0 right-0 top-full mt-1 z-[70] bg-white dark:bg-[#1e1e1e] border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                {newHsCodeOptions.map((opt, idx) => (
                                  <button
                                    key={opt.code}
                                    type="button"
                                    className={`w-full text-left px-3 py-1.5 flex items-start gap-2 transition-colors ${
                                      idx === newHsCodeHighlightIndex
                                        ? 'bg-[#008060]/10 text-[#008060] dark:bg-[#008060]/20 dark:text-[#00a876]'
                                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                                    }`}
                                    onMouseDown={(e) => {
                                      e.preventDefault();
                                      selectNewHsCode(opt.code);
                                    }}
                                    onMouseEnter={() => setNewHsCodeHighlightIndex(idx)}
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
                          {newHsCodeError && (
                            <p className="text-xs text-red-600 mt-1">{newHsCodeError}</p>
                          )}
                          {newHsCodeValid === true && (
                            <p className="text-xs text-green-600 mt-1">
                              HS Code validated against FBR database
                            </p>
                          )}
                        </div>

                        {/* Product Description */}
                        <div>
                          <Label htmlFor="newProductDescription">Product Description *</Label>
                          <Input
                            id="newProductDescription"
                            type="text"
                            value={newProductDescription}
                            onChange={(e) => setNewProductDescription(e.target.value)}
                            placeholder="Enter product description"
                            className="mt-1 text-[12px] h-[30px] w-full glow-border"
                            required
                          />
                        </div>

                        {/* UOM */}
                        <div className='w-full'>
                          <Label htmlFor="newDefaultUom">
                            Unit of Measurement *
                            {newHsCodeUomsLoading && (
                              <Loader2 className="inline h-3 w-3 ml-1 animate-spin text-[#008060]" />
                            )}
                          </Label>
                          <Select value={newDefaultUom} onValueChange={setNewDefaultUom}>
                            <SelectTrigger className="mt-1 text-[12px] h-[30px] glow-border">
                              {newHsCodeUomsLoading ? (
                                <span className="text-muted-foreground">Loading UOMs for HS Code...</span>
                              ) : newDefaultUom ? (
                                <span>{newDefaultUom}</span>
                              ) : (
                                <span className="text-muted-foreground">Select UOM</span>
                              )}
                            </SelectTrigger>
                            <SelectContent>
                              {(newHsCodeUomsLoading
                                ? []
                                : newHsCode
                                  ? newHsCodeUoms
                                  : (masterData?.uom ?? [])
                              ).map((uom) => (
                                <SelectItem key={uom.code} value={uom.name}>
                                  {uom.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {newHsCode && newHsCodeUoms.length > 0 && (
                            <p className="text-xs text-green-600 mt-1">
                              {newHsCodeUoms.length} UOM(s) found for this HS Code
                            </p>
                          )}
                        </div>

                        {/* Transaction Type */}
                        <div className='w-full'>
                          <Label htmlFor="newTransactionType">Transaction Type *</Label>
                          <Select value={newTransactionType} onValueChange={(value) => {
                            if (value !== newTransactionType) {
                              setNewTransactionType(value);
                              setNewDefaultRate('');
                              setNewTaxRateOptions([]);
                            }
                          }}>
                            <SelectTrigger className="mt-1 text-[12px] h-[30px] glow-border">
                              {newTransactionType ? (
                                <span>{newTransactionType}</span>
                              ) : (
                                <span className="text-muted-foreground">Select transaction type</span>
                              )}
                            </SelectTrigger>
                            <SelectContent>
                              {(masterData?.transaction_types ?? []).map((type) => (
                                <SelectItem key={type.code} value={type.name}>
                                  {type.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Tax Rate */}
                        <div>
                          <Label htmlFor="newDefaultRate">
                            Tax Rate *
                            {newTaxRatesLoading && (
                              <Loader2 className="inline h-3 w-3 ml-1 animate-spin text-[#008060]" />
                            )}
                          </Label>
                          {newTaxRateOptions.length > 0 ? (
                            <Select value={newDefaultRate} onValueChange={setNewDefaultRate}>
                              <SelectTrigger className="mt-1 text-[12px] h-[30px] glow-border">
                                {newDefaultRate ? (
                                  <span>{newTaxRateOptions.find(r => r.rate === newDefaultRate)?.name || newDefaultRate}</span>
                                ) : (
                                  <span className="text-muted-foreground">Select tax rate</span>
                                )}
                              </SelectTrigger>
                              <SelectContent>
                                {newTaxRateOptions.map((rate) => (
                                  <SelectItem key={rate.rate} value={rate.rate}>
                                    {rate.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input
                              id="newDefaultRate"
                              type="text"
                              value={newDefaultRate}
                              onChange={(e) => setNewDefaultRate(e.target.value)}
                              placeholder={newTaxRatesLoading ? 'Loading tax rates...' : 'e.g., 18'}
                              className="mt-1 text-[12px] h-[30px] w-full glow-border"
                              disabled={newTaxRatesLoading}
                              required
                            />
                          )}
                          {newTransactionType && newTaxRateOptions.length > 0 && (
                            <p className="text-xs text-green-600 mt-1">
                              {newTaxRateOptions.length} rate(s) for this transaction type
                            </p>
                          )}
                        </div>

                        {/* SRO Schedule No */}
                        <div>
                          <Label htmlFor="newSroScheduleNo">SRO Schedule No (Optional)</Label>
                          <Input
                            id="newSroScheduleNo"
                            type="text"
                            value={newSroScheduleNo}
                            onChange={(e) => setNewSroScheduleNo(e.target.value)}
                            placeholder="Enter SRO schedule number"
                            className="mt-1 text-[12px] h-[30px] w-full glow-border"
                          />
                        </div>

                        {/* SRO Item Serial No */}
                        <div>
                          <Label htmlFor="newSroItemSerialNo">SRO Item Serial No (Optional)</Label>
                          <Input
                            id="newSroItemSerialNo"
                            type="text"
                            value={newSroItemSerialNo}
                            onChange={(e) => setNewSroItemSerialNo(e.target.value)}
                            placeholder="Enter SRO item serial number"
                            className="mt-1 text-[12px] h-[30px] w-full glow-border"
                          />
                        </div>

                        {/* Sub-modal Footer */}
                        <div className="flex justify-end gap-3 pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e] col-span-1 sm:col-span-2">
                          <Button
                            type="button"
                            variant="outline"
                            size='icon'
                            onClick={() => {
                              setIsAddSavedItemModalOpen(false);
                              resetNewItemForm();
                            }}
                            disabled={isSavingNewItem}
                            className="h-8 w-8 text-red-500 hover:text-red-600 border-red-300 dark:border-red-800 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <X className="h-3.5 w-3.5 sm:h-4 sm:w-4"/>
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size='icon'
                            disabled={isSavingNewItem}
                            onClick={handleAddSavedItem}
                            className="h-8 w-8 rounded-lg border-blue-300 dark:border-neutral-800 hover:text-emerald-500 dark:hover:text-emerald-400 shadow-sm transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            {isSavingNewItem ? (
                              <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 animate-spin" />
                            ) : (
                              <Plus className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        </>
      )}

      {/* Validation/Post Result Dialog */}
      <ValidationResultDialog
        isOpen={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          if (pendingReset) {
            clearForm();
          }
        }}
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