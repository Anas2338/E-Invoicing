'use client';

import { useState, useEffect } from 'react';
import { SummaryCard } from '@/components/dashboard/summary-card';
import { RecentInvoices } from '@/components/dashboard/recent-invoices';
import { UserProfileCard } from '@/components/dashboard/user-profile-card';
import { QuickActionsPanel } from '@/components/dashboard/quick-actions-panel';
import { api, ApiError } from '@/lib/api';
import { useAuth } from '@/providers/auth-provider';

export default function DashboardPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [invoiceStats, setInvoiceStats] = useState({
    draft: 0,
    validated: 0,
    posted: 0,
    failed: 0,
  });

  const [recentInvoices, setRecentInvoices] = useState<Array<{
    id: string;
    number: string;
    date: string;
    amount: number;
    status: 'draft' | 'validated' | 'posted' | 'failed';
  }>>([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        // PERFORMANCE: Single optimized API call instead of 6 separate calls
        // Old: 6 queries × 4-5s each = 24-30s total
        // New: 1 query = 4-5s total (6x faster)
        const response = await fetch('/api/v1/dashboard/stats', {
          method: 'GET',
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch dashboard data');
        }

        const data = await response.json();

        // Set stats from optimized response - manual invoices only
        setInvoiceStats({
          draft: data.manual_stats.draft || 0,
          validated: data.manual_stats.validated || 0,
          posted: data.manual_stats.posted || 0,
          failed: data.manual_stats.failed || 0,
        });

        setRecentInvoices(data.recent_invoices || []);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Failed to load dashboard data');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Dashboard</h1>
          <p className="mt-2 text-[#6d7175] dark:text-[#8c9196]">Welcome back, {user?.name || 'User'}!</p>
        </div>
        <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-[#d72c0d] dark:text-[#ff6f59]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-[#d72c0d] dark:text-[#ff6f59]">Error loading dashboard</h3>
              <p className="mt-1 text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Dashboard</h1>
          <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Welcome back, {user?.name || 'User'}! Here's what's happening with your invoices.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center h-10 px-4 py-2 border-2 border-[#c9cccf] dark:border-[#2e2e2e] rounded-xl shadow-sm text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] bg-white dark:bg-[#1a1a1a] hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] transition-all duration-150"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <a
            href="/invoices/create"
            className="inline-flex items-center justify-center h-10 px-4 py-2 border border-transparent rounded-xl shadow-sm text-sm font-semibold text-white bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] transition-all duration-150 hover:shadow-md"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Invoice
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Draft"
          count={invoiceStats.draft}
          icon="📝"
          color="bg-blue-500"
        />
        <SummaryCard
          title="Validated"
          count={invoiceStats.validated}
          icon="✅"
          color="bg-green-500"
        />
        <SummaryCard
          title="Posted"
          count={invoiceStats.posted}
          icon="📤"
          color="bg-purple-500"
        />
        <SummaryCard
          title="Failed"
          count={invoiceStats.failed}
          icon="❌"
          color="bg-red-500"
        />
      </div>

      {/* Total Summary */}
      <div className="bg-gradient-to-r from-[#008060] to-[#00a876] dark:from-[#006e52] dark:to-[#008f64] rounded-2xl shadow-lg p-4 sm:p-6 text-white">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <p className="text-sm font-semibold text-white/80">Total Manual Invoices</p>
            <p className="text-2xl sm:text-3xl font-bold mt-2">
              {invoiceStats.draft + invoiceStats.validated + invoiceStats.posted + invoiceStats.failed}
            </p>
          </div>
          <div className="text-center sm:text-right">
            <p className="text-sm font-semibold text-white/80">Success Rate</p>
            <p className="text-2xl sm:text-3xl font-bold mt-2">
              {(() => {
                const total = invoiceStats.draft + invoiceStats.validated + invoiceStats.posted + invoiceStats.failed;
                const successful = invoiceStats.validated + invoiceStats.posted;
                return total > 0 ? Math.round((successful / total) * 100) : 0;
              })()}%
            </p>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Recent Invoices (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">Recent Invoices</h2>
              <a
                href="/invoices/history"
                className="text-sm font-semibold text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] transition-colors duration-150"
              >
                View all →
              </a>
            </div>
            {recentInvoices.length > 0 ? (
              <RecentInvoices invoices={recentInvoices} />
            ) : (
              <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-[#e1e3e5] dark:border-[#2e2e2e] shadow-sm p-12 text-center">
                <svg className="mx-auto h-12 w-12 text-[#8c9196] dark:text-[#6d7175]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="mt-2 text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">No invoices</h3>
                <p className="mt-1 text-sm text-[#6d7175] dark:text-[#8c9196]">Get started by creating your first invoice.</p>
                <div className="mt-6">
                  <a
                    href="/invoices/create"
                    className="inline-flex items-center h-10 px-4 py-2 border border-transparent shadow-sm text-sm font-semibold rounded-xl text-white bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] transition-all duration-150 hover:shadow-md"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Create Invoice
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - User Profile & Quick Actions (1/3 width) */}
        <div className="space-y-6">
          <UserProfileCard user={user} />
          <QuickActionsPanel />
        </div>
      </div>
    </div>
  );
}