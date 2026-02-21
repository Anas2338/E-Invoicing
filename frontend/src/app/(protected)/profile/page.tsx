'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { api, ApiError } from '@/lib/api';
import { authService } from '@/lib/api/api-client';
import { Key, Building, Hash, User, Mail, Eye, EyeOff, Trash2, MapPin, Home } from 'lucide-react';
import { toast } from 'react-toastify';

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // User profile state
  const [userProfile, setUserProfile] = useState<any>(null);

  // FBR Credentials state
  const [fbrAccessToken, setFbrAccessToken] = useState('');
  const [sandboxToken, setSandboxToken] = useState('');
  const [productionToken, setProductionToken] = useState('');
  const [showSandboxToken, setShowSandboxToken] = useState(false);
  const [showProductionToken, setShowProductionToken] = useState(false);
  const [fbrEnvironment, setFbrEnvironment] = useState('SANDBOX');
  const [fbrSellerNtn, setFbrSellerNtn] = useState('');
  const [fbrBusinessName, setFbrBusinessName] = useState('');
  const [fbrSellerProvince, setFbrSellerProvince] = useState('');
  const [fbrSellerAddress, setFbrSellerAddress] = useState('');
  const [hasSandboxToken, setHasSandboxToken] = useState(false);
  const [hasProductionToken, setHasProductionToken] = useState(false);

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

  const handleDeleteFbrToken = async (environment: 'SANDBOX' | 'PRODUCTION') => {
    const envName = environment === 'SANDBOX' ? 'Sandbox' : 'Production';
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
      } else {
        setProductionToken('');
        setHasProductionToken(false);
        setShowProductionToken(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl pb-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Profile Settings</h1>
        <p className="mt-2 text-sm sm:text-base text-gray-600">Manage your account information and FBR integration credentials</p>
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
                <Label className="flex items-center gap-2 text-gray-500 text-sm">
                  <Mail className="h-4 w-4" />
                  Email Address
                </Label>
                <p className="mt-1 text-gray-900 font-medium">{userProfile?.email || 'Not available'}</p>
              </div>
              <div>
                <Label className="flex items-center gap-2 text-gray-500 text-sm">
                  <User className="h-4 w-4" />
                  Name
                </Label>
                <p className="mt-1 text-gray-900 font-medium">{userProfile?.name || 'Not set'}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-gray-500 text-sm">Account Status</Label>
                <p className="mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    userProfile?.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {userProfile?.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
              </div>
              <div>
                <Label className="text-gray-500 text-sm">Production Access</Label>
                <p className="mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    userProfile?.has_production_access ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {userProfile?.has_production_access ? 'Enabled' : 'Disabled'}
                  </span>
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
            {(hasSandboxToken || hasProductionToken) && (
              <div className="space-y-4">
                {/* Sandbox Token */}
                {hasSandboxToken && sandboxToken && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <Label className="flex items-center gap-2 text-blue-900 font-medium mb-2">
                          <Key className="h-4 w-4" />
                          Sandbox FBR Access Token
                        </Label>
                        <div className="flex items-center gap-2">
                          <Input
                            type={showSandboxToken ? "text" : "password"}
                            value={sandboxToken}
                            readOnly
                            className="font-mono text-sm bg-white"
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
                        <p className="text-xs text-blue-700 mt-2">
                          Your Sandbox token for testing. Click the eye icon to view or the trash icon to delete.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Production Token */}
                {hasProductionToken && productionToken && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <Label className="flex items-center gap-2 text-green-900 font-medium mb-2">
                          <Key className="h-4 w-4" />
                          Production FBR Access Token
                        </Label>
                        <div className="flex items-center gap-2">
                          <Input
                            type={showProductionToken ? "text" : "password"}
                            value={productionToken}
                            readOnly
                            className="font-mono text-sm bg-white"
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
                        <p className="text-xs text-green-700 mt-2">
                          Your Production token for live invoices. Click the eye icon to view or the trash icon to delete.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Add/Update Token Form */}
            <div className="pt-4 border-t">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
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
                <p className="text-xs text-gray-500 mt-1">
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
              <p className="text-xs text-gray-500 mt-1">
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
              <p className="text-xs text-gray-500 mt-1">
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
              <p className="text-xs text-gray-500 mt-1">
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
              <p className="text-xs text-gray-500 mt-1">
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
              <p className="text-xs text-gray-500 mt-1">
                Your complete business address (will auto-fill in invoices)
              </p>
            </div>

            {/* Information Box */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="text-sm font-medium text-blue-900 mb-2">How to get FBR credentials:</h4>
              <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
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
                className="bg-indigo-600 hover:bg-indigo-700"
              >
                {saving ? 'Saving...' : 'Save FBR Credentials'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
