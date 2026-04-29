'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import ExcelUploadForm from '@/components/automation/ExcelUploadForm';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

export default function UploadPage() {
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
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/automation')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Automation
          </Button>
        </div>

        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2 text-[#202223] dark:text-[#e3e3e3]">Upload Excel File</h1>
          <p className="text-[#6d7175] dark:text-[#8c9196]">
            Download the template, fill with invoice data, and upload for bulk scheduling
          </p>
        </div>

        <ExcelUploadForm />

        <div className="mt-8 bg-[#fef3c7] dark:bg-[#451a03]/30 border border-[#fde68a] dark:border-[#451a03] rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 text-[#92400e] dark:text-[#fbbf24]">Important Notes</h3>
          <ul className="space-y-2 text-[#6d7175] dark:text-[#8c9196] text-sm">
            <li className="flex items-start">
              <svg className="w-5 h-5 text-[#92400e] dark:text-[#fbbf24] mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>Only one upload can be processed at a time per user</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-[#92400e] dark:text-[#fbbf24] mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>Invoice numbers must be unique within the Excel file</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-[#92400e] dark:text-[#fbbf24] mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>Invoices with past scheduled times will be marked as expired</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-[#92400e] dark:text-[#fbbf24] mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>Maximum file size: 10 MB, Maximum rows: 1,000</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-[#92400e] dark:text-[#fbbf24] mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>AI Agent processes invoices every 5 minutes with intelligent error handling and adaptive retry</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
