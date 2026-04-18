'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { EnvironmentSelector } from '@/components/common/environment-selector';
import { userService, authService } from '@/lib/api/api-client';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { ArrowLeft, Eye, EyeOff, Trash2, Edit2, Save, X } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [currentEnv, setCurrentEnv] = useState<'sandbox' | 'production'>('sandbox');
  const [canAccessProduction, setCanAccessProduction] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<any>(null);

  // FBR Token Management State
  const [showSandboxToken, setShowSandboxToken] = useState(false);
  const [showProductionToken, setShowProductionToken] = useState(false);
  const [editingSandbox, setEditingSandbox] = useState(false);
  const [editingProduction, setEditingProduction] = useState(false);
  const [sandboxTokenInput, setSandboxTokenInput] = useState('');
  const [productionTokenInput, setProductionTokenInput] = useState('');
  const [updatingToken, setUpdatingToken] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);

      // Fetch environment settings
      const envResponse = await userService.getEnvironmentPreference();
      setCurrentEnv(envResponse.environment as 'sandbox' | 'production');
      setCanAccessProduction(envResponse.canAccessProduction);

      // Fetch user profile
      const profileResponse = await authService.getCurrentUser();
      setUserProfile(profileResponse);

      // Fetch FBR credentials (includes tokens)
      const fbrResponse = await api.auth.getFbrCredentials();

      // Merge FBR credentials into user profile
      setUserProfile((prev: any) => ({
        ...prev,
        fbr_sandbox_token: fbrResponse.fbr_sandbox_token,
        fbr_production_token: fbrResponse.fbr_production_token,
        fbr_environment: fbrResponse.fbr_environment,
      }));

      // Initialize token input fields
      setSandboxTokenInput(fbrResponse.fbr_sandbox_token || '');
      setProductionTokenInput(fbrResponse.fbr_production_token || '');
    } catch (error) {
      console.error('Error fetching settings:', error);
      toast.error('Failed to load settings. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  const handleEnvironmentChange = async (env: 'sandbox' | 'production') => {
    if (env === 'production' && !canAccessProduction) {
      toast.warning('You do not have access to the production environment. Please contact your administrator.');
      return;
    }

    try {
      await userService.updateEnvironmentPreference(env);
      setCurrentEnv(env);
      toast.success(`Environment switched to ${env.toUpperCase()}`);
    } catch (error) {
      console.error('Error updating environment:', error);
      toast.error('Failed to update environment. Please try again.');
    }
  };

  // FBR Token Management Handlers
  const handleEditToken = (environment: 'sandbox' | 'production') => {
    if (environment === 'sandbox') {
      setEditingSandbox(true);
    } else {
      setEditingProduction(true);
    }
  };

  const handleCancelEdit = (environment: 'sandbox' | 'production') => {
    if (environment === 'sandbox') {
      setEditingSandbox(false);
      setSandboxTokenInput(userProfile?.fbr_sandbox_token || '');
    } else {
      setEditingProduction(false);
      setProductionTokenInput(userProfile?.fbr_production_token || '');
    }
  };

  const handleSaveToken = async (environment: 'sandbox' | 'production') => {
    const token = environment === 'sandbox' ? sandboxTokenInput : productionTokenInput;

    if (!token || token.trim() === '') {
      toast.error('Token cannot be empty');
      return;
    }

    try {
      setUpdatingToken(true);

      const updateData = environment === 'sandbox'
        ? { fbr_sandbox_token: token }
        : { fbr_production_token: token };

      await userService.updateFbrCredentials(updateData);

      // Refresh all settings including FBR credentials
      await fetchSettings();

      if (environment === 'sandbox') {
        setEditingSandbox(false);
      } else {
        setEditingProduction(false);
      }

      toast.success(`${environment.toUpperCase()} token updated successfully`);
    } catch (error) {
      console.error('Error updating token:', error);
      toast.error('Failed to update token. Please try again.');
    } finally {
      setUpdatingToken(false);
    }
  };

  const handleDeleteToken = async (environment: 'sandbox' | 'production') => {
    if (!confirm(`Are you sure you want to delete your ${environment.toUpperCase()} token? This action cannot be undone.`)) {
      return;
    }

    try {
      setUpdatingToken(true);

      const updateData = environment === 'sandbox'
        ? { fbr_sandbox_token: '' }
        : { fbr_production_token: '' };

      await userService.updateFbrCredentials(updateData);

      // Refresh all settings including FBR credentials
      await fetchSettings();

      if (environment === 'sandbox') {
        setSandboxTokenInput('');
      } else {
        setProductionTokenInput('');
      }

      toast.success(`${environment.toUpperCase()} token deleted successfully`);
    } catch (error) {
      console.error('Error deleting token:', error);
      toast.error('Failed to delete token. Please try again.');
    } finally {
      setUpdatingToken(false);
    }
  };

  const maskToken = (token: string) => {
    if (!token || token.length < 10) return '••••••••';
    return `${token.substring(0, 10)}...${token.substring(token.length - 10)}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading settings...</p>
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
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Settings</h1>
        <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Manage your account settings and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Account Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 sm:space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Email Address</p>
              <p className="text-[#202223] dark:text-[#e3e3e3] sm:col-span-2 break-words">{userProfile?.email || 'Not available'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Name</p>
              <p className="text-[#202223] dark:text-[#e3e3e3] sm:col-span-2">{userProfile?.name || 'Not set'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Production Access</p>
              <p className="text-[#202223] dark:text-[#e3e3e3] sm:col-span-2">{canAccessProduction ? 'Enabled' : 'Disabled'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Current Environment</p>
              <p className="text-[#202223] dark:text-[#e3e3e3] capitalize sm:col-span-2">{currentEnv}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Environment Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
              Select the environment you want to work with. This affects which API endpoints your actions target.
            </p>

            <div className="pt-4">
              <EnvironmentSelector
                currentEnv={currentEnv}
                canAccessProduction={canAccessProduction}
                onEnvironmentChange={handleEnvironmentChange}
              />
            </div>

            <div className="mt-4 p-4 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 border border-[#bfdbfe] dark:border-[#1e3a8a] rounded-xl">
              <h3 className="font-semibold text-[#1e40af] dark:text-[#60a5fa]">Environment Information</h3>
              <ul className="mt-2 text-sm text-[#1e40af] dark:text-[#60a5fa] list-disc pl-5 space-y-1">
                <li><strong>Sandbox:</strong> Safe testing environment that doesn't affect real data</li>
                <li><strong>Production:</strong> Live environment that affects real business data</li>
                <li>Switching environments may require re-validation of pending operations</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FBR Token Management */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">FBR Token Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
              Manage your FBR API access tokens for sandbox and production environments.
            </p>

            {/* Sandbox Token */}
            <div className="border border-[#e1e3e5] dark:border-[#33363a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">Sandbox Token</h3>
                {userProfile?.fbr_sandbox_token && !editingSandbox && (
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowSandboxToken(!showSandboxToken)}
                      className="h-8"
                    >
                      {showSandboxToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditToken('sandbox')}
                      className="h-8"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteToken('sandbox')}
                      className="h-8 text-red-600 hover:text-red-700"
                      disabled={updatingToken}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>

              {editingSandbox ? (
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="sandboxToken">Token</Label>
                    <Input
                      id="sandboxToken"
                      type="text"
                      value={sandboxTokenInput}
                      onChange={(e) => setSandboxTokenInput(e.target.value)}
                      placeholder="Enter your FBR sandbox token"
                      className="font-mono text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleSaveToken('sandbox')}
                      disabled={updatingToken}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCancelEdit('sandbox')}
                      disabled={updatingToken}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : userProfile?.fbr_sandbox_token ? (
                <div className="bg-[#f6f6f7] dark:bg-[#2c2e33] p-3 rounded font-mono text-sm break-all">
                  {showSandboxToken ? userProfile.fbr_sandbox_token : maskToken(userProfile.fbr_sandbox_token)}
                </div>
              ) : (
                <div className="text-[#6d7175] dark:text-[#8c9196] text-sm">
                  No sandbox token configured.{' '}
                  <button
                    onClick={() => handleEditToken('sandbox')}
                    className="text-[#008060] dark:text-[#00a876] hover:underline"
                  >
                    Add token
                  </button>
                </div>
              )}
            </div>

            {/* Production Token */}
            <div className="border border-[#e1e3e5] dark:border-[#33363a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">Production Token</h3>
                {userProfile?.fbr_production_token && !editingProduction && (
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowProductionToken(!showProductionToken)}
                      className="h-8"
                    >
                      {showProductionToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditToken('production')}
                      className="h-8"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteToken('production')}
                      className="h-8 text-red-600 hover:text-red-700"
                      disabled={updatingToken}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>

              {editingProduction ? (
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="productionToken">Token</Label>
                    <Input
                      id="productionToken"
                      type="text"
                      value={productionTokenInput}
                      onChange={(e) => setProductionTokenInput(e.target.value)}
                      placeholder="Enter your FBR production token"
                      className="font-mono text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleSaveToken('production')}
                      disabled={updatingToken}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCancelEdit('production')}
                      disabled={updatingToken}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : userProfile?.fbr_production_token ? (
                <div className="bg-[#f6f6f7] dark:bg-[#2c2e33] p-3 rounded font-mono text-sm break-all">
                  {showProductionToken ? userProfile.fbr_production_token : maskToken(userProfile.fbr_production_token)}
                </div>
              ) : (
                <div className="text-[#6d7175] dark:text-[#8c9196] text-sm">
                  No production token configured.{' '}
                  <button
                    onClick={() => handleEditToken('production')}
                    className="text-[#008060] dark:text-[#00a876] hover:underline"
                  >
                    Add token
                  </button>
                </div>
              )}
            </div>

            <div className="mt-4 p-4 bg-[#fff4e6] dark:bg-[#7c2d12]/30 border border-[#ffd8a8] dark:border-[#7c2d12] rounded-xl">
              <h3 className="font-semibold text-[#c2410c] dark:text-[#fb923c]">Security Notice</h3>
              <ul className="mt-2 text-sm text-[#c2410c] dark:text-[#fb923c] list-disc pl-5 space-y-1">
                <li>Tokens are encrypted before being stored in the database</li>
                <li>Never share your FBR tokens with anyone</li>
                <li>Regularly rotate your tokens for security</li>
                <li>Delete tokens immediately if compromised</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}