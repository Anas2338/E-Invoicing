'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EnvironmentSelector } from '@/components/common/environment-selector';
import { userService, authService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';
import { ArrowLeft } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [currentEnv, setCurrentEnv] = useState<'sandbox' | 'production'>('sandbox');
  const [canAccessProduction, setCanAccessProduction] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<any>(null);

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
    </div>
  );
}