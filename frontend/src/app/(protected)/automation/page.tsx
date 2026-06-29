'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Upload, LayoutDashboard, ClipboardList } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { toast } from 'react-toastify';
import AutomationDashboard from '@/components/automation/AutomationDashboard';

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
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="text-center space-y-6">
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 animate-pulse" />
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-emerald-600 dark:border-t-emerald-400 animate-spin" />
          </div>
          <p className="text-base sm:text-lg md:text-xl font-black text-neutral-600 dark:text-neutral-300 tracking-wide">Loading automation</p>
        </div>
      </div>
    );
  }

  if (!user?.automation_enabled) {
    return null;
  }

  return (
    <div className="h-full flex flex-col space-y-1 sm:space-y-2 pt-1 pb-2 px-3 sm:px-4 md:px-6 lg:px-8 w-full max-w-[1600px] mx-auto overflow-hidden">

      {/* SECTION 1: Action Cards */}
      <div className="flex-shrink-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">

          {/* Upload Excel */}
          <Link
            href="/automation/upload"
            className="relative group h-20 sm:h-24 lg:h-28 p-[1.5px] rounded-2xl sm:rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(37,99,235,0.5)]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400 via-blue-500 to-indigo-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <div className="relative h-full w-full flex flex-col items-center justify-center gap-1 rounded-[20px] bg-gradient-to-b from-blue-400 to-blue-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none">
              <div className="h-7 w-7 sm:h-8 sm:w-8 lg:h-10 lg:w-10 rounded-lg lg:rounded-xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <Upload className="h-4 w-4 sm:h-5 sm:w-5 text-white stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs lg:text-sm font-black tracking-wide text-white drop-shadow-md">
                Upload Excel
              </span>
            </div>
          </Link>

          {/* Dashboard */}
          <Link
            href="/automation/dashboard"
            className="relative group h-20 sm:h-24 lg:h-28 p-[1.5px] rounded-2xl sm:rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(22,163,74,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(22,163,74,0.5)]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 via-green-500 to-teal-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <div className="relative h-full w-full flex flex-col items-center justify-center gap-1 rounded-[20px] bg-gradient-to-b from-emerald-400 to-emerald-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none">
              <div className="h-7 w-7 sm:h-8 sm:w-8 lg:h-10 lg:w-10 rounded-lg lg:rounded-xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <LayoutDashboard className="h-4 w-4 sm:h-5 sm:w-5 text-white stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs lg:text-sm font-black tracking-wide text-white drop-shadow-md">
                Invoice Dashboard
              </span>
            </div>
          </Link>

          {/* Upload History */}
          <Link
            href="/automation/uploads"
            className="relative group h-20 sm:h-24 lg:h-28 p-[1.5px] rounded-2xl sm:rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(234,88,12,0.5)] focus-within:-translate-y-1 focus-within:shadow-[0_0_30px_rgba(234,88,12,0.5)]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-orange-400 via-orange-500 to-red-600 opacity-80 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-300" />
            <div className="relative h-full w-full flex flex-col items-center justify-center gap-1 rounded-[20px] bg-gradient-to-b from-orange-400 to-orange-500 text-white cursor-pointer px-4 border-2 border-white/90 shadow-lg focus:outline-none">
              <div className="h-7 w-7 sm:h-8 sm:w-8 lg:h-10 lg:w-10 rounded-lg lg:rounded-xl bg-white/20 flex items-center justify-center transform group-hover:scale-110 group-focus-within:scale-110 transition-transform duration-300 border-2 border-white/30 shadow-lg">
                <ClipboardList className="h-4 w-4 sm:h-5 sm:w-5 text-white stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs lg:text-sm font-black tracking-wide text-white drop-shadow-md">
                Upload History
              </span>
            </div>
          </Link>

        </div>
      </div>

      {/* SECTION 2: Stats Cards */}
      <div className="flex-shrink-0">
        <AutomationDashboard />
      </div>

      {/* SECTION 3: How It Works — compact */}
      <div className="bg-gradient-to-br from-blue-50/80 to-indigo-50/80 dark:from-[#0a1628]/80 dark:to-[#0f1a30]/80 rounded-2xl sm:rounded-3xl border-2 border-blue-700 dark:border-blue-900/40 shadow-xl p-3 sm:p-4">
        <h3 className="text-sm sm:text-base font-black text-blue-900 dark:text-blue-300 mb-2 sm:mb-3 tracking-tight">How It Works</h3>
        <ol className="space-y-1 sm:space-y-1.5">
          {[
            'Download the Excel template with predefined columns',
            'Fill in your invoice data including scheduled date and time',
            'Upload the completed Excel file for validation',
            'Our AI Agent validates invoices immediately and transfers them to the main system at their scheduled times',
            'Monitor progress and download updated Excel with submission results',
          ].map((step, index) => (
            <li key={index} className="flex items-start gap-2 sm:gap-3">
              <span className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 bg-blue-600 dark:bg-blue-500 text-white rounded-full flex items-center justify-center text-[10px] sm:text-xs font-black shadow-md shadow-blue-600/30">
                {index + 1}
              </span>
              <span className="text-[11px] sm:text-xs font-semibold text-neutral-700 dark:text-neutral-300 leading-relaxed pt-0.5">
                {step}
              </span>
            </li>
          ))}
        </ol>
      </div>

    </div>
  );
}
