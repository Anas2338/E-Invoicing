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
    <div className="container mx-auto px-4 py-3">
      <div className="max-w-3xl lg:max-w-6xl mx-auto flex gap-3">
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
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0 flex flex-col">
          <ExcelUploadForm />

          <div className="mt-3 bg-[#fef3c7] dark:bg-[#451a03]/30 border-2 border-blue-600 dark:border-[#451a03] rounded-2xl p-6 lg:p-8 flex flex-col justify-center flex-1">
            <h3 className="text-lg lg:text-xl font-bold mb-4 text-[#92400e] dark:text-[#fbbf24]">Important Notes</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-2">
              <ul className="text-sm lg:text-base text-[#6d7175] dark:text-[#8c9196] space-y-2.5">
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Only one upload processed at a time per user</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Invoice numbers must be unique within the Excel file</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Invoices with past scheduled times marked as expired</span>
                </li>
              </ul>
              <ul className="text-sm lg:text-base text-[#6d7175] dark:text-[#8c9196] space-y-2.5">
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Max file size: 10 MB, Max rows: 20,000</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Invoices validated immediately after upload via FBR integration</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#92400e] dark:text-[#fbbf24] flex-shrink-0 text-xl leading-none mt-0.5">•</span>
                  <span>Validated invoices auto-transfer to main system every 5 min</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
