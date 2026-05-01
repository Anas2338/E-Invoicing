'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { api, ApiError } from '@/lib/api';
import { authService } from '@/lib/api/api-client';
import { adminApi } from '@/services/adminApi';
import { Key, Building, Hash, User, Mail, Eye, EyeOff, Trash2, MapPin, Home, ArrowLeft, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'react-toastify';
import SavedHSCodesSection from '@/components/profile/SavedHSCodesSection';
import SavedProductDescriptionsSection from '@/components/profile/SavedProductDescriptionsSection';
import SavedUOMsSection from '@/components/profile/SavedUOMsSection';
import SavedTaxRatesSection from '@/components/profile/SavedTaxRatesSection';
import InvoiceSettingsSection from '@/components/profile/InvoiceSettingsSection';

export default function ProfilePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // User profile state
  const [userProfile, setUserProfile] = useState<any>(null);

  // FBR Credentials state
  const [fbrAccessToken, setFbrAccessToken] = useState('');
  const [sandboxToken, setSandboxToken] = useState('');
  const [productionToken, setProductionToken] = useState('');
  const [systemSyncToken, setSystemSyncToken] = useState('');
  const [showSandboxToken, setShowSandboxToken] = useState(false);
  const [showProductionToken, setShowProductionToken] = useState(false);
  const [showSystemSyncToken, setShowSystemSyncToken] = useState(false);
  const [fbrEnvironment, setFbrEnvironment] = useState('SANDBOX');
  const [fbrSellerNtn, setFbrSellerNtn] = useState('');
  const [fbrBusinessName, setFbrBusinessName] = useState('');
  const [fbrSellerProvince, setFbrSellerProvince] = useState('');
  const [fbrSellerAddress, setFbrSellerAddress] = useState('');
  const [hasSandboxToken, setHasSandboxToken] = useState(false);
  const [hasProductionToken, setHasProductionToken] = useState(false);
  const [hasSystemSyncToken, setHasSystemSyncToken] = useState(false);

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<any>(null);

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);

      // Fetch user profile
      const profileResponse = await authService.getCurrentUser();
      setUserProfile(profileResponse);

      // Fetch FBR credentials
      const fbrResponse = await api.auth.getFbrCredentials();
      setFbrEnvironment(fbrResponse.fbr_environment || 'SANDBOX');
      setFbrSellerNtn(fbrResponse.fbr_seller_ntn || '');
      setFbrBusinessName(fbrResponse.fbr_business_name || '');
      setFbrSellerProvince(fbrResponse.fbr_seller_province || '');
      setFbrSellerAddress(fbrResponse.fbr_seller_address || '');
      setSandboxToken(fbrResponse.fbr_sandbox_token || '');
      setProductionToken(fbrResponse.fbr_production_token || '');
      setHasSandboxToken(fbrResponse.has_sandbox_token || false);
      setHasProductionToken(fbrResponse.has_production_token || false);

      // Admin only: System sync token
      if (profileResponse.role === 'admin') {
        setSystemSyncToken(fbrResponse.fbr_system_sync_token || '');
        setHasSystemSyncToken(fbrResponse.has_system_sync_token || false);
      }
    } catch (err) {
      console.error('Error fetching profile data:', err);
      toast.error('Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveFbrCredentials = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!fbrAccessToken) {
      toast.error('Please enter your FBR access token');
      return;
    }

    try {
      setSaving(true);

      const credentials: any = {
        fbr_environment: fbrEnvironment,
        fbr_seller_ntn: fbrSellerNtn,
        fbr_business_name: fbrBusinessName,
        fbr_seller_province: fbrSellerProvince,
        fbr_seller_address: fbrSellerAddress,
        fbr_access_token: fbrAccessToken,
      };

      const response = await api.auth.updateFbrCredentials(credentials);

      toast.success(`FBR credentials updated successfully for ${fbrEnvironment}!`);
      setHasSandboxToken(response.has_sandbox_token);
      setHasProductionToken(response.has_production_token);

      // Admin only: Update system sync token status
      if (userProfile?.role === 'admin' && response.has_system_sync_token !== undefined) {
        setHasSystemSyncToken(response.has_system_sync_token);
      }

      setFbrAccessToken(''); // Clear the token input for security

      // Refresh credentials
      await fetchProfileData();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error('Failed to update FBR credentials');
      }
      console.error('Error updating FBR credentials:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFbrToken = async (environment: 'SANDBOX' | 'PRODUCTION' | 'SYSTEM') => {
    const envName = environment === 'SANDBOX' ? 'Sandbox' : environment === 'PRODUCTION' ? 'Production' : 'System Sync';
    if (!confirm(`Are you sure you want to delete your ${envName} FBR access token? You will need to enter it again to use ${envName} FBR features.`)) {
      return;
    }

    try {
      setDeleting(true);

      await api.auth.deleteFbrCredentials(environment);

      toast.success(`${envName} FBR access token deleted successfully!`);

      // Update local state
      if (environment === 'SANDBOX') {
        setSandboxToken('');
        setHasSandboxToken(false);
        setShowSandboxToken(false);
      } else if (environment === 'PRODUCTION') {
        setProductionToken('');
        setHasProductionToken(false);
        setShowProductionToken(false);
      } else if (environment === 'SYSTEM') {
        setSystemSyncToken('');
        setHasSystemSyncToken(false);
        setShowSystemSyncToken(false);
      }

      // Refresh credentials
      await fetchProfileData();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error(`Failed to delete ${envName} FBR access token`);
      }
      console.error('Error deleting FBR token:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleSaveSystemSyncToken = async (e: React.FormEvent) => {
    e.preventDefault();

    const systemTokenInput = (e.target as HTMLFormElement).system_token.value;

    if (!systemTokenInput || !systemTokenInput.trim()) {
      toast.error('Please enter the system sync token');
      return;
    }

    try {
      setSaving(true);

      const credentials = {
        fbr_system_sync_token: systemTokenInput.trim(),
      };

      await api.auth.updateFbrCredentials(credentials);

      toast.success('System sync token updated successfully!');

      // Clear the input
      (e.target as HTMLFormElement).system_token.value = '';

      // Refresh credentials
      await fetchProfileData();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error('Failed to update system sync token');
      }
      console.error('Error updating system sync token:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleManualSync = async () => {
    if (!hasSystemSyncToken) {
      toast.error('Please set the system sync token first');
      return;
    }

    try {
      setSyncing(true);
      toast.info('Starting FBR master data sync...');

      const result = await adminApi.triggerSync();

      toast.success('Sync completed successfully!');
      setSyncStatus(result.result);

      // Show summary
      if (result.result) {
        const summary = `
          Status: ${result.result.status}
          Total Records: ${result.result.total_records}
          Changes Detected: ${result.result.total_changes}
        `;
      }
    } catch (err) {
      if (err instanceof Error) {
        toast.error(err.message);
      } else {
        toast.error('Failed to trigger sync');
      }
      console.error('Error triggering sync:', err);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl pb-8">
      {/* Back to Dashboard Button */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>

      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Profile Settings</h1>
        <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Manage your account information and FBR integration credentials</p>
      </div>

      {/* User Information Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <User className="h-5 w-5" />
            Account Information
          </CardTitle>
          <CardDescription className="text-sm">
            Your account details and registration information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="flex items-center gap-2 text-[#6d7175] dark:text-[#8c9196] text-sm">
                  <Mail className="h-4 w-4" />
                  Email Address
                </Label>
                <p className="mt-1 text-[#202223] dark:text-[#e3e3e3] font-medium">{userProfile?.email || 'Not available'}</p>
              </div>
              <div>
                <Label className="flex items-center gap-2 text-[#6d7175] dark:text-[#8c9196] text-sm">
                  <User className="h-4 w-4" />
                  Name
                </Label>
                <p className="mt-1 text-[#202223] dark:text-[#e3e3e3] font-medium">{userProfile?.name || 'Not set'}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-[#6d7175] dark:text-[#8c9196] text-sm">Account Status</Label>
                <p className="mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    userProfile?.is_active ? 'bg-[#d1fae5] text-[#065f46] dark:bg-[#064e3b]/30 dark:text-[#34d399]' : 'bg-[#fee2e2] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:text-[#f87171]'
                  }`}>
                    {userProfile?.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
              </div>
              <div>
                <Label className="text-[#6d7175] dark:text-[#8c9196] text-sm">Production Access</Label>
                <p className="mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    userProfile?.has_production_access ? 'bg-[#dbeafe] text-[#1e40af] dark:bg-[#1e3a8a]/30 dark:text-[#60a5fa]' : 'bg-[#f6f6f7] text-[#6d7175] dark:bg-[#2e2e2e] dark:text-[#8c9196]'
                  }`}>
                    {userProfile?.has_production_access ? 'Enabled' : 'Disabled'}
                  </span>
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoice Numbering Settings */}
      <InvoiceSettingsSection />

      {/* FBR Credentials Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Key className="h-5 w-5" />
            FBR Integration Credentials
          </CardTitle>
          <CardDescription className="text-sm">
            Configure your Federal Board of Revenue (FBR) API credentials for invoice validation and posting.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveFbrCredentials} className="space-y-6">
            {/* Existing Tokens Display */}
            <div className="space-y-4">
              {/* Sandbox Token */}
              {hasSandboxToken && sandboxToken && (
                <div className="p-4 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 border border-[#bfdbfe] dark:border-[#1e3a8a] rounded-xl">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <Label className="flex items-center gap-2 text-[#1e40af] dark:text-[#60a5fa] font-semibold mb-2">
                        <Key className="h-4 w-4" />
                        Sandbox FBR Access Token
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          type={showSandboxToken ? "text" : "password"}
                          value={sandboxToken}
                          readOnly
                          className="font-mono text-sm bg-white dark:bg-[#1a1a1a]"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => setShowSandboxToken(!showSandboxToken)}
                          className="flex-shrink-0"
                        >
                          {showSandboxToken ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="icon"
                          onClick={() => handleDeleteFbrToken('SANDBOX')}
                          disabled={deleting}
                          className="flex-shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-[#1e40af] dark:text-[#60a5fa] mt-2">
                        Your Sandbox token for testing. Click the eye icon to view or the trash icon to delete.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Production Token */}
              {hasProductionToken && productionToken && (
                <div className="p-4 bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <Label className="flex items-center gap-2 text-[#065f46] dark:text-[#34d399] font-semibold mb-2">
                        <Key className="h-4 w-4" />
                        Production FBR Access Token
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          type={showProductionToken ? "text" : "password"}
                          value={productionToken}
                          readOnly
                          className="font-mono text-sm bg-white dark:bg-[#1a1a1a]"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => setShowProductionToken(!showProductionToken)}
                          className="flex-shrink-0"
                        >
                          {showProductionToken ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="icon"
                          onClick={() => handleDeleteFbrToken('PRODUCTION')}
                          disabled={deleting}
                          className="flex-shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-[#065f46] dark:text-[#34d399] mt-2">
                        Your Production token for live invoices. Click the eye icon to view or the trash icon to delete.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* System Sync Token (Admin Only) */}
              {userProfile?.role === 'admin' && hasSystemSyncToken && systemSyncToken && (
                <div className="p-4 bg-[#fef3c7] dark:bg-[#78350f]/30 border border-[#fde68a] dark:border-[#92400e] rounded-xl">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <Label className="flex items-center gap-2 text-[#92400e] dark:text-[#fbbf24] font-semibold mb-2">
                        <Key className="h-4 w-4" />
                        System Sync Token (Admin)
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          type={showSystemSyncToken ? "text" : "password"}
                          value={systemSyncToken}
                          readOnly
                          className="font-mono text-sm bg-white dark:bg-[#1a1a1a]"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => setShowSystemSyncToken(!showSystemSyncToken)}
                          className="flex-shrink-0"
                        >
                          {showSystemSyncToken ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="icon"
                          onClick={() => handleDeleteFbrToken('SYSTEM')}
                          disabled={deleting}
                          className="flex-shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-[#92400e] dark:text-[#fbbf24] mt-2">
                        System token for daily FBR master data sync at 6:00 AM PKT. This token is used by the system to fetch provinces, UOM, HS codes, and other master data.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Add/Update Token Form */}
            <div className="pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
              <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">
                {hasSandboxToken || hasProductionToken ? 'Add or Update Token' : 'Add FBR Token'}
              </h3>

              {/* Environment Selection */}
              <div>
                <Label htmlFor="fbrEnvironment">Environment *</Label>
                <Select value={fbrEnvironment} onValueChange={setFbrEnvironment}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SANDBOX">Sandbox (Testing)</SelectItem>
                    <SelectItem value="PRODUCTION">Production (Live)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                  Select which environment this token is for
                </p>
              </div>
            </div>

            {/* FBR Access Token Input */}
            <div>
              <Label htmlFor="fbrAccessToken" className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                FBR Access Token for {fbrEnvironment} *
              </Label>
              <Input
                id="fbrAccessToken"
                type="password"
                value={fbrAccessToken}
                onChange={(e) => setFbrAccessToken(e.target.value)}
                placeholder={`Enter your ${fbrEnvironment} FBR API access token`}
                className="mt-1"
              />
              <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                Your FBR API access token from the FBR Digital Invoicing Portal
              </p>
            </div>

            {/* Seller NTN */}
            <div>
              <Label htmlFor="fbrSellerNtn" className="flex items-center gap-2">
                <Hash className="h-4 w-4" />
                Seller NTN/CNIC
              </Label>
              <Input
                id="fbrSellerNtn"
                type="text"
                value={fbrSellerNtn}
                onChange={(e) => setFbrSellerNtn(e.target.value)}
                placeholder="Enter your 7-digit NTN or 13-digit CNIC"
                className="mt-1"
              />
              <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                Your National Tax Number (7 digits) or CNIC (13 digits)
              </p>
            </div>

            {/* Business Name */}
            <div>
              <Label htmlFor="fbrBusinessName" className="flex items-center gap-2">
                <Building className="h-4 w-4" />
                Business Name
              </Label>
              <Input
                id="fbrBusinessName"
                type="text"
                value={fbrBusinessName}
                onChange={(e) => setFbrBusinessName(e.target.value)}
                placeholder="Enter your registered business name"
                className="mt-1"
              />
              <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                Your business name as registered with FBR
              </p>
            </div>

            {/* Seller Province */}
            <div>
              <Label htmlFor="fbrSellerProvince" className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Province
              </Label>
              <Select value={fbrSellerProvince} onValueChange={setFbrSellerProvince}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select your province" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PUNJAB">Punjab</SelectItem>
                  <SelectItem value="SINDH">Sindh</SelectItem>
                  <SelectItem value="KPK">Khyber Pakhtunkhwa</SelectItem>
                  <SelectItem value="BALOCHISTAN">Balochistan</SelectItem>
                  <SelectItem value="GILGIT_BALTISTAN">Gilgit-Baltistan</SelectItem>
                  <SelectItem value="AJK">Azad Jammu & Kashmir</SelectItem>
                  <SelectItem value="ISLAMABAD">Islamabad Capital Territory</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                Your business province (will auto-fill in invoices)
              </p>
            </div>

            {/* Seller Address */}
            <div>
              <Label htmlFor="fbrSellerAddress" className="flex items-center gap-2">
                <Home className="h-4 w-4" />
                Business Address
              </Label>
              <Input
                id="fbrSellerAddress"
                type="text"
                value={fbrSellerAddress}
                onChange={(e) => setFbrSellerAddress(e.target.value)}
                placeholder="Enter your complete business address"
                className="mt-1"
              />
              <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                Your complete business address (will auto-fill in invoices)
              </p>
            </div>

            {/* Information Box */}
            <div className="p-4 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 border border-[#bfdbfe] dark:border-[#1e3a8a] rounded-xl">
              <h4 className="text-sm font-semibold text-[#1e40af] dark:text-[#60a5fa] mb-2">How to get FBR credentials:</h4>
              <ol className="text-sm text-[#1e40af] dark:text-[#60a5fa] space-y-1 list-decimal list-inside">
                <li>Register at FBR Digital Invoicing Portal: <a href="https://e.fbr.gov.pk" target="_blank" rel="noopener noreferrer" className="underline">https://e.fbr.gov.pk</a></li>
                <li>Complete the registration and verification process</li>
                <li>Navigate to API Settings to generate your access token</li>
                <li>Copy the token and paste it here</li>
              </ol>
            </div>

            {/* Save Button */}
            <div className="flex justify-end gap-3">
              <Button
                type="submit"
                disabled={saving}
                className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
              >
                {saving ? 'Saving...' : 'Save FBR Credentials'}
              </Button>
            </div>
          </form>

          {/* Admin Only: System Sync Token Section */}
          {userProfile?.role === 'admin' && (
            <div className="mt-8 pt-8 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3] flex items-center gap-2">
                  <Key className="h-5 w-5 text-[#92400e] dark:text-[#fbbf24]" />
                  System Sync Token (Admin Only)
                </h3>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mt-1">
                  Configure the FBR token used by the system for daily master data synchronization at 6:00 AM PKT.
                </p>
              </div>

              <form onSubmit={handleSaveSystemSyncToken} className="space-y-4">
                <div className="p-4 bg-[#fef3c7] dark:bg-[#78350f]/30 border border-[#fde68a] dark:border-[#92400e] rounded-xl">
                  <h4 className="text-sm font-semibold text-[#92400e] dark:text-[#fbbf24] mb-2">What is the System Sync Token?</h4>
                  <ul className="text-sm text-[#92400e] dark:text-[#fbbf24] space-y-1 list-disc list-inside">
                    <li>Used by the system to automatically fetch FBR master data (provinces, UOM, HS codes, etc.)</li>
                    <li>Runs daily at 6:00 AM Pakistan Time</li>
                    <li>Detects changes in FBR data and creates notifications</li>
                    <li>Only one admin token is used system-wide for all users</li>
                    <li>Can be manually triggered using the button below</li>
                  </ul>
                </div>

                <div>
                  <Label htmlFor="system_token" className="flex items-center gap-2">
                    <Key className="h-4 w-4" />
                    System FBR Access Token *
                  </Label>
                  <Input
                    id="system_token"
                    name="system_token"
                    type="password"
                    placeholder="Enter the system FBR API access token"
                    className="mt-1"
                  />
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-1">
                    This token will be used for automated system operations. Make sure it has the necessary permissions.
                  </p>
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    type="submit"
                    disabled={saving}
                    className="bg-[#92400e] hover:bg-[#78350f] dark:bg-[#fbbf24] dark:hover:bg-[#f59e0b] dark:text-[#1a1a1a]"
                  >
                    {saving ? 'Saving...' : 'Save System Token'}
                  </Button>
                </div>
              </form>

              {/* Manual Sync Section */}
              {hasSystemSyncToken && (
                <div className="mt-6 pt-6 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
                  <div className="mb-4">
                    <h4 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      Manual Data Sync
                    </h4>
                    <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mt-1">
                      Manually trigger FBR master data synchronization to fetch the latest data immediately.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      type="button"
                      onClick={handleManualSync}
                      disabled={syncing}
                      className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] flex items-center gap-2"
                    >
                      <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                      {syncing ? 'Syncing...' : 'Sync Now'}
                    </Button>

                    {syncStatus && (
                      <div className="flex items-center gap-2 text-sm">
                        {syncStatus.status === 'success' ? (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                            <span className="text-green-600 dark:text-green-400">
                              Last sync: {syncStatus.total_records} records, {syncStatus.total_changes} changes
                            </span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                            <span className="text-red-600 dark:text-red-400">
                              Sync failed
                            </span>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {syncStatus && syncStatus.status === 'success' && (
                    <div className="mt-4 p-3 bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-lg">
                      <p className="text-sm text-[#065f46] dark:text-[#34d399] font-medium mb-2">Sync Details:</p>
                      <div className="grid grid-cols-2 gap-2 text-xs text-[#065f46] dark:text-[#34d399]">
                        {syncStatus.data_types && Object.entries(syncStatus.data_types).map(([key, value]: [string, any]) => (
                          <div key={key}>
                            <span className="font-semibold">{key}:</span> {value.synced} records
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Saved HS Codes Section */}
      <SavedHSCodesSection />

      {/* Saved Product Descriptions Section */}
      <SavedProductDescriptionsSection />

      {/* Saved UOMs Section */}
      <SavedUOMsSection />

      {/* Saved Tax Rates Section */}
      <SavedTaxRatesSection />
    </div>
  );
}
