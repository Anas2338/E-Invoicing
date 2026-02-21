'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EnvironmentSelector } from '@/components/common/environment-selector';
import { userService, authService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';

export default function SettingsPage() {
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
      <div className="flex items-center justify-center min-h-screen">
        <p>Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-sm sm:text-base text-gray-600">Manage your account settings and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Account Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 sm:space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-medium text-gray-500">Email Address</p>
              <p className="text-gray-900 sm:col-span-2 break-words">{userProfile?.email || 'Not available'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-medium text-gray-500">Name</p>
              <p className="text-gray-900 sm:col-span-2">{userProfile?.name || 'Not set'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-medium text-gray-500">Production Access</p>
              <p className="text-gray-900 sm:col-span-2">{canAccessProduction ? 'Enabled' : 'Disabled'}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <p className="text-sm font-medium text-gray-500">Current Environment</p>
              <p className="text-gray-900 capitalize sm:col-span-2">{currentEnv}</p>
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
            <p className="text-sm sm:text-base text-gray-600">
              Select the environment you want to work with. This affects which API endpoints your actions target.
            </p>

            <div className="pt-4">
              <EnvironmentSelector
                currentEnv={currentEnv}
                canAccessProduction={canAccessProduction}
                onEnvironmentChange={handleEnvironmentChange}
              />
            </div>

            <div className="mt-4 p-4 bg-blue-50 rounded-md">
              <h3 className="font-medium text-blue-800">Environment Information</h3>
              <ul className="mt-2 text-sm text-blue-700 list-disc pl-5 space-y-1">
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