'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import UploadHistory from '@/components/automation/UploadHistory';
import { ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

export default function UploadHistoryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (!loading && user && !user.automation_enabled) {
      toast.error('Automation access not enabled. Please contact your administrator.');
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user?.automation_enabled) {
    return null;
  }
  return (
    <div className="h-full flex flex-col pt-1 pb-2 max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 overflow-hidden">
      <div className="flex gap-3 flex-1 min-h-0">
        {/* Sidebar Action Buttons */}
        <div className="flex flex-col items-center gap-1.5 flex-shrink-0 pt-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.push('/automation')}
            className="h-10 lg:h-12 w-10 lg:w-12 border-slate-500 text-slate-600"
            title="Back to Automation"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setRefreshKey(k => k + 1)}
            disabled={isRefreshing}
            className="h-10 lg:h-12 w-10 lg:w-12 border-blue-500 text-blue-600 disabled:opacity-50"
            title="Refresh"
          >
            {isRefreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex-shrink-0 mb-4">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Upload History
            </h1>
          </div>

          {/* Info Card */}
          <div className="flex-shrink-0 bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-600 dark:border-blue-800 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">
              About Upload Sessions
            </h3>
            <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
              <li>• Each Excel file upload creates a new session</li>
              <li>• You can delete sessions that have no submitted invoices</li>
              <li>• Deleting a session removes all pending, failed, and blocked invoices from that upload</li>
              <li>• Submitted invoices cannot be deleted for audit purposes</li>
            </ul>
          </div>

          {/* Upload History Component */}
          <div className="flex-1 min-h-0">
            <Suspense
              fallback={
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              }
            >
              <UploadHistory refreshKey={refreshKey} onLoading={setIsRefreshing} />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
