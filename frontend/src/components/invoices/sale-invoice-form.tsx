'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Trash2, Plus, Loader2 } from 'lucide-react';
import { masterDataService, fbrIntegrationService, type AllMasterData } from '@/lib/api/api-client';
import { api } from '@/lib/api';

interface InvoiceItem {
  hsCode: string;
  productDescription: string;
  rate: string;
  uoM: string;
  quantity: number;
  totalValues: number;
  valueSalesExcludingST: number;
  fixedNotifiedValueOrRetailPrice: number;
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
  const [invoiceDate, setInvoiceDate] = useState('');
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

  // Invoice items state
  const [items, setItems] = useState<InvoiceItem[]>([{
    hsCode: '',
    productDescription: '',
    rate: '',
    uoM: 'NOS',
    quantity: 0,
    totalValues: 0,
    valueSalesExcludingST: 0,
    fixedNotifiedValueOrRetailPrice: 0,
    salesTaxApplicable: 0,
    salesTaxWithheldAtSource: '',
    extraTax: 0,
    furtherTax: 0,
    sroScheduleNo: '',
    fedPayable: 0,
    discount: 0,
    saleType: '01',
    sroItemSerialNo: ''
  }]);

  // Dynamic tax rate fetching state
  const [dynamicTaxRates, setDynamicTaxRates] = useState<Array<{rate: string, name: string}>>([]);
  const [fetchingTaxRates, setFetchingTaxRates] = useState(false);
  const [taxRateError, setTaxRateError] = useState<string | null>(null);
  const [hasSelectedTransactionType, setHasSelectedTransactionType] = useState(false);

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
          const province = masterData.provinces.find(p => p.name === profile.fbr_seller_province);
          if (province) {
            setSellerProvinceCode(province.code);
          }
        }
        if (profile.fbr_seller_address) {
          setSellerAddress(profile.fbr_seller_address);
        }
      } catch (error) {
        console.error('Failed to fetch user profile:', error);
      }
    };

    fetchUserProfile();
  }, [isEditMode, masterData]);

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
      setTransactionTypeId(initialData.transaction_type_id || '');

      // If transaction type exists in initial data, mark as selected
      if (initialData.transaction_type_id) {
        setHasSelectedTransactionType(true);
      }

      // Populate seller information
      setSellerNTNCNIC(initialData.seller_ntn_cnic || '');
      setSellerBusinessName(initialData.seller_business_name || '');
      setSellerProvince(initialData.seller_province || '');
      setSellerAddress(initialData.seller_address || '');

      // Resolve seller province code from masterData
      if (initialData.seller_province && masterData) {
        const province = masterData.provinces.find(p => p.name === initialData.seller_province);
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
        const province = masterData.provinces.find(p => p.name === initialData.buyer_province);
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
          fixedNotifiedValueOrRetailPrice: item.fixedNotifiedValueOrRetailPrice || item.fixed_notified_value_or_retail_price || 0,
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
      }
    }
  }, [isEditMode, initialData, masterData]);

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

  // Debounced buyer NTN/CNIC change handler
  useEffect(() => {
    // Only verify if buyer NTN is provided and has minimum length
    if (!buyerNTNCNIC || buyerNTNCNIC.trim().length < 7) {
      setBuyerVerificationMessage(null);
      return;
    }

    // Debounce the verification call
    const timeoutId = setTimeout(() => {
      verifyBuyerRegistration(buyerNTNCNIC);
    }, 1000); // Wait 1 second after user stops typing

    return () => clearTimeout(timeoutId);
  }, [buyerNTNCNIC, verifyBuyerRegistration]);

  // Fetch dynamic tax rates from FBR API
  const fetchTaxRates = useCallback(async () => {
    // Only fetch if user has explicitly selected a transaction type
    if (!hasSelectedTransactionType) {
      return;
    }

    // Only fetch if all required fields are present
    if (!transactionTypeId || !invoiceDate || !sellerProvinceCode) {
      setDynamicTaxRates([]);
      setTaxRateError(null);
      return;
    }

    setFetchingTaxRates(true);
    setTaxRateError(null);

    try {
      // Convert date format: YYYY-MM-DD to DD-MMM-YYYY
      const [year, month, day] = invoiceDate.split('-');
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const formattedDate = `${day}-${monthNames[parseInt(month) - 1]}-${year}`;

      const rates = await masterDataService.getSaleTypeToRate(
        formattedDate,
        parseInt(transactionTypeId),
        parseInt(sellerProvinceCode)
      );

      if (rates && rates.length > 0) {
        setDynamicTaxRates(rates);
        setTaxRateError(null);
      } else {
        // Use fallback rates
        setDynamicTaxRates([]);
        setTaxRateError('Using default tax rates');
      }
    } catch (error) {
      console.error('Error fetching tax rates:', error);
      setDynamicTaxRates([]);
      setTaxRateError('Failed to fetch tax rates, using defaults');
    } finally {
      setFetchingTaxRates(false);
    }
  }, [transactionTypeId, invoiceDate, sellerProvinceCode, hasSelectedTransactionType]);

  // Trigger tax rate fetching when required fields change
  useEffect(() => {
    fetchTaxRates();
  }, [fetchTaxRates]);

  const addItem = () => {
    setItems([...items, {
      hsCode: '',
      productDescription: '',
      rate: '',
      uoM: 'NOS',
      quantity: 1,
      totalValues: 0,
      valueSalesExcludingST: 0,
      fixedNotifiedValueOrRetailPrice: 0,
      salesTaxApplicable: 0,
      salesTaxWithheldAtSource: '',
      extraTax: 0,
      furtherTax: 0,
      sroScheduleNo: '',
      fedPayable: 0,
      discount: 0,
      saleType: '01',
      sroItemSerialNo: ''
    }]);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = useCallback((index: number, field: keyof InvoiceItem, value: any) => {
    setItems(prevItems => {
      const updatedItems = [...prevItems];
      updatedItems[index] = { ...updatedItems[index], [field]: value };

      // Auto-calculate when Total Value (Inc. Tax) is updated
      if (field === 'totalValues' && value) {
        const totalValue = parseFloat(value) || 0;
        const taxRate = parseFloat(updatedItems[index].rate) || 0;

        if (totalValue > 0 && taxRate >= 0) {
          // Calculate Sales Tax Applicable = Total Value × (Tax Rate / 100)
          const salesTax = totalValue * (taxRate / 100);
          // Calculate Value Excl. Sales Tax = Total Value - Sales Tax
          const valueExclTax = totalValue - salesTax;

          updatedItems[index].valueSalesExcludingST = parseFloat(valueExclTax.toFixed(2));
          updatedItems[index].salesTaxApplicable = parseFloat(salesTax.toFixed(2));
        }
      }

      return updatedItems;
    });
  }, []);

  // State to track which items are fetching HS code descriptions
  const [fetchingHSCode, setFetchingHSCode] = useState<{ [key: number]: boolean }>({});
  const [hsCodeSuggestions, setHsCodeSuggestions] = useState<{ [key: number]: Array<{code: string, description: string}> }>({});

  // State for dynamically fetched data based on user selections
  const [filteredUoms, setFilteredUoms] = useState<{ [key: number]: Array<{code: string, name: string}> }>({});
  const [sroSchedules, setSroSchedules] = useState<{ [key: number]: Array<{id: string, description: string}> }>({});
  const [fetchingDynamicData, setFetchingDynamicData] = useState<{ [key: number]: boolean }>({});

  // Function to fetch valid UOMs for a specific HS code
  const fetchValidUomsForHsCode = useCallback(async (index: number, hsCode: string) => {
    if (!hsCode || hsCode.length < 4) return;

    setFetchingDynamicData(prev => ({ ...prev, [index]: true }));

    try {
      // Assuming annexure_id = 3 (you may need to make this dynamic based on your requirements)
      const validUoms = await masterDataService.getHsUom(hsCode, 3);

      if (validUoms && validUoms.length > 0) {
        setFilteredUoms(prev => ({ ...prev, [index]: validUoms }));
      } else {
        // If no specific UOMs returned, use all UOMs from master data
        setFilteredUoms(prev => ({ ...prev, [index]: [] }));
      }
    } catch (error) {
      console.error('Error fetching valid UOMs for HS code:', error);
      // On error, allow all UOMs
      setFilteredUoms(prev => ({ ...prev, [index]: [] }));
    } finally {
      setFetchingDynamicData(prev => ({ ...prev, [index]: false }));
    }
  }, []);

  // Function to fetch SRO schedules based on tax rate
  const fetchSroSchedules = useCallback(async (index: number, rateId: string) => {
    if (!rateId || !invoiceDate) return;

    setFetchingDynamicData(prev => ({ ...prev, [index]: true }));

    try {
      // Format date as DD-MMM-YYYY (e.g., "04-Feb-2024")
      const formattedDate = new Date(invoiceDate).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      }).replace(/ /g, '-');

      // Assuming origination_supplier_csv = 1 (you may need to make this dynamic)
      const schedules = await masterDataService.getSroSchedule(
        parseInt(rateId),
        formattedDate,
        1
      );

      if (schedules && schedules.length > 0) {
        setSroSchedules(prev => ({ ...prev, [index]: schedules }));
      } else {
        setSroSchedules(prev => ({ ...prev, [index]: [] }));
      }
    } catch (error) {
      console.error('Error fetching SRO schedules:', error);
      setSroSchedules(prev => ({ ...prev, [index]: [] }));
    } finally {
      setFetchingDynamicData(prev => ({ ...prev, [index]: false }));
    }
  }, [invoiceDate]);

  // Function to filter and find HS code description locally
  const handleHSCodeChange = useCallback((index: number, value: string) => {
    updateItem(index, 'hsCode', value);

    // If masterData has HS codes, filter and show suggestions
    if (masterData && masterData.hs_codes && masterData.hs_codes.length > 0) {
      if (value.length >= 2) {
        // Filter HS codes that start with or contain the entered value
        const filtered = masterData.hs_codes
          .filter(hs =>
            hs.code.toLowerCase().includes(value.toLowerCase()) ||
            hs.description.toLowerCase().includes(value.toLowerCase())
          )
          .slice(0, 10); // Limit to 10 suggestions

        setHsCodeSuggestions(prev => ({ ...prev, [index]: filtered }));

        // If exact match found, fetch valid UOMs (description is manual)
        const exactMatch = masterData.hs_codes.find(hs =>
          hs.code.toLowerCase() === value.toLowerCase()
        );

        if (exactMatch) {
          setHsCodeSuggestions(prev => ({ ...prev, [index]: [] })); // Clear suggestions

          // Fetch valid UOMs for this HS code
          fetchValidUomsForHsCode(index, exactMatch.code);
        }
      } else {
        setHsCodeSuggestions(prev => ({ ...prev, [index]: [] }));
      }
    }
  }, [masterData, updateItem, fetchValidUomsForHsCode]);

  // Function to select an HS code from suggestions
  const selectHSCode = useCallback((index: number, hsCode: {code: string, description: string}) => {
    updateItem(index, 'hsCode', hsCode.code);
    setHsCodeSuggestions(prev => ({ ...prev, [index]: [] })); // Clear suggestions

    // Fetch valid UOMs for this HS code
    fetchValidUomsForHsCode(index, hsCode.code);
  }, [updateItem, fetchValidUomsForHsCode]);

  // Function to handle tax rate change
  const handleTaxRateChange = useCallback((index: number, rateValue: string) => {
    updateItem(index, 'rate', rateValue);

    // Auto-select Sale Type based on tax rate
    const rate = parseFloat(rateValue);
    let autoSaleType = '01'; // Default: Goods at standard rate

    if (rate === 0) {
      autoSaleType = '03'; // Goods at zero rate
    } else if (rate > 0 && rate < 18) {
      autoSaleType = '02'; // Goods at reduced rate
    } else if (rate === 18) {
      autoSaleType = '01'; // Goods at standard rate (default)
    }

    updateItem(index, 'saleType', autoSaleType);

    // Fetch SRO schedules for this tax rate
    if (rateValue && invoiceDate) {
      fetchSroSchedules(index, rateValue);
    }
  }, [updateItem, fetchSroSchedules, invoiceDate]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Convert items from camelCase to snake_case for backend
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

    const invoiceData = {
      external_id: invoiceNo || `INV-${Date.now()}`, // Use user-provided invoice no or auto-generate
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
      items: formattedItems,
      environment: environment
    };

    onSubmit(invoiceData);
  };

  return (
    <form onSubmit={handleFormSubmit} className="space-y-6">
      {/* Loading state */}
      {masterDataLoading && (
        <Card>
          <CardContent className="py-8">
            <div className="flex items-center justify-center space-x-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading form options...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {masterDataError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-4">
            <p className="text-red-600">{masterDataError}</p>
          </CardContent>
        </Card>
      )}

      {/* Form content - only show when master data is loaded */}
      {!masterDataLoading && masterData && (
        <>
          {/* Invoice Header */}
          <Card>
            <CardHeader>
              <CardTitle>Invoice Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="invoiceNo">Invoice No *</Label>
                  <Input
                    id="invoiceNo"
                    value={invoiceNo}
                    onChange={(e) => setInvoiceNo(e.target.value)}
                    placeholder="e.g., INV-2024-001"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Unique invoice number for your records</p>
                </div>

                <div>
                  <Label htmlFor="invoiceType">Invoice Type *</Label>
                  <Select value={invoiceType} onValueChange={(val) => setInvoiceType(val as 'Sale Invoice' | 'Debit Note')}>
                    <SelectTrigger disabled={masterData.invoice_types.length === 0}>
                      <SelectValue placeholder={masterData.invoice_types.length === 0 ? "Configure FBR token in profile" : "Select invoice type"} />
                    </SelectTrigger>
                    <SelectContent>
                      {masterData.invoice_types.length === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        masterData.invoice_types.map((type) => (
                          <SelectItem key={type.code} value={type.name}>{type.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="transactionType">Transaction Type *</Label>
                  <Select value={transactionTypeId} onValueChange={(val) => {
                    setTransactionTypeId(val);
                    setHasSelectedTransactionType(true);
                  }}>
                    <SelectTrigger disabled={masterData.transaction_types.length === 0}>
                      <span className="flex-1 text-left">
                        {transactionTypeId
                          ? masterData.transaction_types.find(t => t.code === transactionTypeId)?.name || transactionTypeId
                          : masterData.transaction_types.length === 0
                            ? "Configure FBR token in profile"
                            : "Select transaction type"
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {masterData.transaction_types.length === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        masterData.transaction_types.map((type) => (
                          <SelectItem key={type.code} value={type.code}>{type.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-500 mt-1">Required for automatic tax rate calculation</p>
                </div>

            <div>
              <Label htmlFor="invoiceDate">Invoice Date *</Label>
              <Input
                id="invoiceDate"
                type="date"
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                required
              />
            </div>

            <div>
              <Label htmlFor="environment">Environment *</Label>
              <Select value={environment} onValueChange={(val) => setEnvironment(val as 'SANDBOX' | 'PRODUCTION')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="SANDBOX">Sandbox</SelectItem>
                  <SelectItem value="PRODUCTION">Production</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {invoiceType === 'Debit Note' && (
            <div>
              <Label htmlFor="invoiceRefNo">Invoice Reference Number *</Label>
              <Input
                id="invoiceRefNo"
                value={invoiceRefNo}
                onChange={(e) => setInvoiceRefNo(e.target.value)}
                placeholder="Reference invoice number (22 or 28 digits)"
                required
              />
              <p className="text-xs text-gray-500 mt-1">22 digits for NTN, 28 digits for CNIC</p>
            </div>
          )}

          {environment === 'SANDBOX' && (
            <div>
              <Label htmlFor="scenarioId">Scenario ID *</Label>
              <Input
                id="scenarioId"
                value={scenarioId}
                onChange={(e) => setScenarioId(e.target.value)}
                placeholder="e.g., SN001"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Required for sandbox testing. Default: SN001 (Goods at standard rate to registered buyers)
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Seller Information */}
      <Card>
        <CardHeader>
          <CardTitle>Seller Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="sellerNTNCNIC">Seller NTN/CNIC *</Label>
              <Input
                id="sellerNTNCNIC"
                value={sellerNTNCNIC}
                onChange={(e) => setSellerNTNCNIC(e.target.value)}
                placeholder="Enter NTN or CNIC"
                required
              />
            </div>

            <div>
              <Label htmlFor="sellerBusinessName">Business Name *</Label>
              <Input
                id="sellerBusinessName"
                value={sellerBusinessName}
                onChange={(e) => setSellerBusinessName(e.target.value)}
                placeholder="Enter business name"
                required
              />
            </div>

            <div>
              <Label htmlFor="sellerProvince">Province *</Label>
              <Select value={sellerProvince} onValueChange={(val) => {
                setSellerProvince(val);
                // Find and store province code
                const province = masterData.provinces.find(p => p.name === val);
                if (province) {
                  setSellerProvinceCode(province.code);
                }
              }}>
                <SelectTrigger disabled={masterData.provinces.length === 0}>
                  <SelectValue placeholder={masterData.provinces.length === 0 ? "Configure FBR token in profile" : "Select province"} />
                </SelectTrigger>
                <SelectContent>
                  {masterData.provinces.length === 0 ? (
                    <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                  ) : (
                    masterData.provinces.map((province) => (
                      <SelectItem key={province.code} value={province.name}>{province.name}</SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="sellerAddress">Address *</Label>
              <Input
                id="sellerAddress"
                value={sellerAddress}
                onChange={(e) => setSellerAddress(e.target.value)}
                placeholder="Enter business address"
                required
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Buyer Information */}
      <Card>
        <CardHeader>
          <CardTitle>Buyer Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="buyerRegistrationType">Registration Type *</Label>
              <Select value={buyerRegistrationType} onValueChange={(val) => setBuyerRegistrationType(val as 'Registered' | 'Unregistered')}>
                <SelectTrigger disabled={isVerifyingBuyer}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {masterData.registration_types.map((type) => (
                    <SelectItem key={type.code} value={type.name}>{type.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 mt-1">Auto-detected from FBR when NTN/CNIC is entered</p>
            </div>

            <div>
              <Label htmlFor="buyerNTNCNIC">
                Buyer NTN/CNIC {buyerRegistrationType === 'Registered' ? '*' : '(Optional)'}
              </Label>
              <div className="relative">
                <Input
                  id="buyerNTNCNIC"
                  value={buyerNTNCNIC}
                  onChange={(e) => setBuyerNTNCNIC(e.target.value)}
                  placeholder="Enter NTN or CNIC"
                  required={buyerRegistrationType === 'Registered'}
                  className={isVerifyingBuyer ? 'pr-10' : ''}
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

            <div>
              <Label htmlFor="buyerBusinessName">Business Name *</Label>
              <Input
                id="buyerBusinessName"
                value={buyerBusinessName}
                onChange={(e) => setBuyerBusinessName(e.target.value)}
                placeholder="Enter business name"
                required
              />
            </div>

            <div>
              <Label htmlFor="buyerProvince">Province *</Label>
              <Select value={buyerProvince} onValueChange={(val) => {
                setBuyerProvince(val);
                // Find and store province code
                const province = masterData.provinces.find(p => p.name === val);
                if (province) {
                  setBuyerProvinceCode(province.code);
                }
              }}>
                <SelectTrigger disabled={masterData.provinces.length === 0}>
                  <SelectValue placeholder={masterData.provinces.length === 0 ? "Configure FBR token in profile" : "Select province"} />
                </SelectTrigger>
                <SelectContent>
                  {masterData.provinces.length === 0 ? (
                    <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                  ) : (
                    masterData.provinces.map((province) => (
                      <SelectItem key={province.code} value={province.name}>{province.name}</SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="md:col-span-2">
              <Label htmlFor="buyerAddress">Address *</Label>
              <Input
                id="buyerAddress"
                value={buyerAddress}
                onChange={(e) => setBuyerAddress(e.target.value)}
                placeholder="Enter business address"
                required
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoice Items */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Invoice Items</CardTitle>
            <Button type="button" variant="outline" size="sm" onClick={addItem}>
              <Plus className="h-4 w-4 mr-2" />
              Add Item
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {items.map((item, index) => (
            <div key={index} className="border rounded-lg p-4 space-y-4">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-medium">Item {index + 1}</h4>
                {items.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeItem(index)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative">
                  <Label>HS Code *</Label>
                  <Input
                    value={item.hsCode}
                    onChange={(e) => handleHSCodeChange(index, e.target.value)}
                    placeholder="e.g., 0101.2100"
                    required
                  />
                  {hsCodeSuggestions[index] && hsCodeSuggestions[index].length > 0 && (
                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                      {hsCodeSuggestions[index].map((suggestion, suggestionIndex) => (
                        <div
                          key={suggestionIndex}
                          className="px-3 py-2 hover:bg-indigo-50 cursor-pointer border-b last:border-b-0"
                          onClick={() => selectHSCode(index, suggestion)}
                        >
                          <div className="font-medium text-sm text-indigo-600">{suggestion.code}</div>
                          <div className="text-xs text-gray-600 truncate">{suggestion.description}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="md:col-span-2">
                  <div className="flex items-center gap-2">
                    <Label>Product Description *</Label>
                    {fetchingHSCode[index] && (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    )}
                  </div>
                  <Input
                    value={item.productDescription}
                    onChange={(e) => updateItem(index, 'productDescription', e.target.value)}
                    placeholder="Details of product or service"
                    required
                  />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <Label>Tax Rate *</Label>
                    {fetchingTaxRates && (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    )}
                  </div>
                  <Select value={item.rate} onValueChange={(val) => handleTaxRateChange(index, val)}>
                    <SelectTrigger disabled={dynamicTaxRates.length === 0}>
                      <span className="flex-1 text-left">
                        {item.rate && dynamicTaxRates.length > 0
                          ? dynamicTaxRates.find(r => r.rate === item.rate)?.name || item.rate
                          : dynamicTaxRates.length === 0
                            ? "No tax rate found"
                            : "Select tax rate"
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {dynamicTaxRates.length === 0 ? (
                        <SelectItem value="none" disabled>No tax rates available</SelectItem>
                      ) : (
                        dynamicTaxRates.map((rate) => (
                          <SelectItem key={rate.rate} value={rate.rate}>{rate.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {dynamicTaxRates.length === 0 && !fetchingTaxRates && (
                    <p className="text-xs text-gray-500 mt-1">Fill transaction type, date & province</p>
                  )}
                  {taxRateError && (
                    <p className="text-xs text-amber-600 mt-1">{taxRateError}</p>
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <Label>Unit of Measurement *</Label>
                    {fetchingDynamicData[index] && (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    )}
                  </div>
                  <Select value={item.uoM} onValueChange={(val) => updateItem(index, 'uoM', val)}>
                    <SelectTrigger disabled={masterData.uom.length === 0}>
                      <span className="flex-1 text-left">
                        {item.uoM
                          ? (filteredUoms[index] && filteredUoms[index].length > 0
                              ? filteredUoms[index].find(u => u.code === item.uoM)?.name
                              : masterData.uom.find(u => u.code === item.uoM)?.name
                            ) || item.uoM
                          : masterData.uom.length === 0
                            ? "Configure FBR token in profile"
                            : "Select UOM"
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {masterData.uom.length === 0 ? (
                        <SelectItem value="none" disabled>No options available - Configure FBR token</SelectItem>
                      ) : (
                        // Show filtered UOMs if available (from HS code lookup), otherwise show all UOMs
                        (filteredUoms[index] && filteredUoms[index].length > 0 ? filteredUoms[index] : masterData.uom).map((uom) => (
                          <SelectItem key={uom.code} value={uom.code}>{uom.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {filteredUoms[index] && filteredUoms[index].length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      Showing {filteredUoms[index].length} valid UOM(s) for selected HS code
                    </p>
                  )}
                </div>

                <div>
                  <Label>Quantity *</Label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={item.quantity || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'quantity', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div>
                  <Label>Total Value (Inc. Tax) *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.totalValues || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'totalValues', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div>
                  <Label>Value Excl. Sales Tax *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.valueSalesExcludingST || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'valueSalesExcludingST', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div>
                  <Label>Fixed/Retail Price *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.fixedNotifiedValueOrRetailPrice || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'fixedNotifiedValueOrRetailPrice', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div>
                  <Label>Sales Tax Applicable *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.salesTaxApplicable || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'salesTaxApplicable', val === '' ? 0 : parseFloat(val));
                    }}
                    required
                  />
                </div>

                <div>
                  <Label>Sales Tax Withheld *</Label>
                  <Input
                    type="text"
                    value={item.salesTaxWithheldAtSource}
                    onChange={(e) => updateItem(index, 'salesTaxWithheldAtSource', e.target.value)}
                    placeholder="Enter amount (e.g., 0, 100.50)"
                    required
                  />
                </div>

                <div>
                  <Label>Extra Tax</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.extraTax || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'extraTax', val === '' ? 0 : parseFloat(val));
                    }}
                  />
                </div>

                <div>
                  <Label>Further Tax</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.furtherTax || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'furtherTax', val === '' ? 0 : parseFloat(val));
                    }}
                  />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <Label>SRO Schedule No</Label>
                    {fetchingDynamicData[index] && (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    )}
                  </div>
                  {sroSchedules[index] && sroSchedules[index].length > 0 ? (
                    <Select value={item.sroScheduleNo} onValueChange={(val) => updateItem(index, 'sroScheduleNo', val)}>
                      <SelectTrigger>
                        <span className="flex-1 text-left">
                          {item.sroScheduleNo
                            ? sroSchedules[index].find(s => s.id === item.sroScheduleNo)?.description || item.sroScheduleNo
                            : "Select SRO schedule"
                          }
                        </span>
                      </SelectTrigger>
                      <SelectContent>
                        {sroSchedules[index].map((schedule) => (
                          <SelectItem key={schedule.id} value={schedule.id}>
                            {schedule.description}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      value={item.sroScheduleNo}
                      onChange={(e) => updateItem(index, 'sroScheduleNo', e.target.value)}
                      placeholder={item.rate ? "No SRO schedules available for selected rate" : "Select tax rate first"}
                      disabled={!item.rate}
                    />
                  )}
                  {sroSchedules[index] && sroSchedules[index].length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      {sroSchedules[index].length} SRO schedule(s) available for selected tax rate
                    </p>
                  )}
                </div>

                <div>
                  <Label>FED Payable</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.fedPayable || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'fedPayable', val === '' ? 0 : parseFloat(val));
                    }}
                  />
                </div>

                <div>
                  <Label>Discount</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={item.discount || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      updateItem(index, 'discount', val === '' ? 0 : parseFloat(val));
                    }}
                  />
                </div>

                <div>
                  <Label>Sale Type *</Label>
                  <Select value={item.saleType} onValueChange={(val) => updateItem(index, 'saleType', val)}>
                    <SelectTrigger>
                      <span className="flex-1 text-left">
                        {item.saleType
                          ? masterData.sale_types.find(t => t.code === item.saleType)?.name || item.saleType
                          : "Select sale type"
                        }
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {masterData.sale_types.map((type) => (
                        <SelectItem key={type.code} value={type.code}>{type.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>SRO Item Serial No</Label>
                  <Input
                    value={item.sroItemSerialNo}
                    onChange={(e) => updateItem(index, 'sroItemSerialNo', e.target.value)}
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Form Actions */}
      <div className="flex justify-between">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading || isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading || isSubmitting}>
          {isLoading || isSubmitting
            ? (isEditMode ? 'Updating Invoice...' : 'Creating Invoice...')
            : (isEditMode ? 'Update Invoice' : 'Create Invoice')
          }
        </Button>
      </div>
        </>
      )}
    </form>
  );
}