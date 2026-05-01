'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';

export default function AutomationPage() {
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
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
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

        <h1 className="text-3xl font-bold mb-6 text-[#202223] dark:text-[#e3e3e3]">Invoice Automation</h1>

        <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-[#202223] dark:text-[#e3e3e3]">Welcome to AI-Powered Invoice Automation</h2>
          <p className="text-[#6d7175] dark:text-[#8c9196] mb-4">
            Automate your invoice submissions with our intelligent AI Agent and Excel-based bulk upload system.
            Schedule invoices to be automatically validated and submitted to FBR with 5-minute precision and smart error handling.
          </p>

          <div className="grid md:grid-cols-2 gap-6 mt-8">
            <Link
              href="/automation/upload"
              className="block p-6 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 rounded-xl border-2 border-[#bfdbfe] dark:border-[#1e3a8a] hover:border-[#60a5fa] dark:hover:border-[#60a5fa] transition-all duration-150 hover:shadow-md"
            >
              <div className="flex items-center mb-3">
                <svg className="w-8 h-8 text-[#1e40af] dark:text-[#60a5fa] mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Upload Excel</h3>
              </div>
              <p className="text-[#6d7175] dark:text-[#8c9196]">
                Download template, fill with invoice data, and upload for bulk scheduling
              </p>
            </Link>

            <Link
              href="/automation/dashboard"
              className="block p-6 bg-[#d1fae5] dark:bg-[#064e3b]/30 rounded-xl border-2 border-[#a7f3d0] dark:border-[#065f46] hover:border-[#34d399] dark:hover:border-[#34d399] transition-all duration-150 hover:shadow-md"
            >
              <div className="flex items-center mb-3">
                <svg className="w-8 h-8 text-[#065f46] dark:text-[#34d399] mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Dashboard</h3>
              </div>
              <p className="text-[#6d7175] dark:text-[#8c9196]">
                Monitor automation progress, view statistics, and manage scheduled invoices
              </p>
            </Link>

            <Link
              href="/automation/uploads"
              className="block p-6 bg-[#ffedd5] dark:bg-[#431407]/30 rounded-xl border-2 border-[#fed7aa] dark:border-[#7c2d12] hover:border-[#fb923c] dark:hover:border-[#fb923c] transition-all duration-150 hover:shadow-md"
            >
              <div className="flex items-center mb-3">
                <svg className="w-8 h-8 text-[#7c2d12] dark:text-[#fb923c] mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">Upload History</h3>
              </div>
              <p className="text-[#6d7175] dark:text-[#8c9196]">
                View and manage your Excel upload sessions
              </p>
            </Link>
          </div>
        </div>

        <div className="bg-[#dbeafe] dark:bg-[#1e3a8a]/30 border border-[#bfdbfe] dark:border-[#1e3a8a] rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 text-[#1e40af] dark:text-[#60a5fa]">How It Works</h3>
          <ol className="space-y-3 text-[#6d7175] dark:text-[#8c9196]">
            <li className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-[#1e40af] dark:bg-[#60a5fa] text-white dark:text-[#1e3a8a] rounded-full flex items-center justify-center text-sm font-semibold mr-3">1</span>
              <span>Download the Excel template with predefined columns</span>
            </li>
            <li className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-[#1e40af] dark:bg-[#60a5fa] text-white dark:text-[#1e3a8a] rounded-full flex items-center justify-center text-sm font-semibold mr-3">2</span>
              <span>Fill in your invoice data including scheduled date and time</span>
            </li>
            <li className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-[#1e40af] dark:bg-[#60a5fa] text-white dark:text-[#1e3a8a] rounded-full flex items-center justify-center text-sm font-semibold mr-3">3</span>
              <span>Upload the completed Excel file for validation</span>
            </li>
            <li className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-[#1e40af] dark:bg-[#60a5fa] text-white dark:text-[#1e3a8a] rounded-full flex items-center justify-center text-sm font-semibold mr-3">4</span>
              <span>Our AI Agent automatically processes invoices at scheduled times with 5-minute precision</span>
            </li>
            <li className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-[#1e40af] dark:bg-[#60a5fa] text-white dark:text-[#1e3a8a] rounded-full flex items-center justify-center text-sm font-semibold mr-3">5</span>
              <span>Monitor progress and download updated Excel with submission results</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
}
