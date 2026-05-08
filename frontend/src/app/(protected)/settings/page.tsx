'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { userService, authService } from '@/lib/api/api-client';
import { api } from '@/lib/api';
import { toast } from 'react-toastify';
import { ArrowLeft } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<any>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);

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
    } catch (error) {
      console.error('Error fetching settings:', error);
      toast.error('Failed to load settings. Please refresh the page.');
    } finally {
      setLoading(false);
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
          </div>
        </CardContent>
      </Card>

      {/* FBR Token Status (Read-Only) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">FBR Token Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
              FBR tokens are managed by administrators. Contact your admin to add or update tokens.
            </p>

            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-3">
                Token Configuration Status
              </h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 dark:text-gray-300">Sandbox Token:</span>
                  <span className={`text-sm font-semibold ${userProfile?.fbr_sandbox_token ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
                    {userProfile?.fbr_sandbox_token ? '✓ Configured' : '✗ Not Configured'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 dark:text-gray-300">Production Token:</span>
                  <span className={`text-sm font-semibold ${userProfile?.fbr_production_token ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
                    {userProfile?.fbr_production_token ? '✓ Configured' : '✗ Not Configured'}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-[#fff4e6] dark:bg-[#7c2d12]/30 border border-[#ffd8a8] dark:border-[#7c2d12] rounded-xl">
              <h3 className="font-semibold text-[#c2410c] dark:text-[#fb923c]">Security Notice</h3>
              <ul className="mt-2 text-sm text-[#c2410c] dark:text-[#fb923c] list-disc pl-5 space-y-1">
                <li>Tokens are encrypted before being stored in the database</li>
                <li>Never share your FBR tokens with anyone</li>
                <li>Contact your administrator to update or rotate tokens</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}