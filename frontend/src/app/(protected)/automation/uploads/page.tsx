'use client';

import { Suspense, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import UploadHistory from '@/components/automation/UploadHistory';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

export default function UploadHistoryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/automation"
            className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Automation
          </Link>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Upload History
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            View and manage your Excel upload sessions
          </p>
        </div>

        {/* Info Card */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <Suspense
            fallback={
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            }
          >
            <UploadHistory />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
