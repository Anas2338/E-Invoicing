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

        // Fetch invoices for each status to get counts
        const [draftData, validatedData, postedData, failedData, recentData] = await Promise.all([
          api.invoices.list({ status: 'DRAFT', size: 1 }),
          api.invoices.list({ status: 'VALIDATED', size: 1 }),
          api.invoices.list({ status: 'POSTED', size: 1 }),
          api.invoices.list({ status: 'FAILED', size: 1 }),
          api.invoices.list({ size: 10 }), // Get recent 10 invoices
        ]);

        // Set stats from totals
        setInvoiceStats({
          draft: draftData.total || 0,
          validated: validatedData.total || 0,
          posted: postedData.total || 0,
          failed: failedData.total || 0,
        });

        // Transform recent invoices to match component format
        const transformedInvoices = recentData.data.map((invoice: any) => {
          // Calculate total amount from items
          const totalAmount = invoice.items?.reduce((sum: number, item: any) =>
            sum + (item.total_values || 0), 0
          ) || 0;

          return {
            id: invoice.id,
            number: invoice.external_id,
            date: invoice.invoice_date || new Date(invoice.created_at).toISOString().split('T')[0],
            amount: totalAmount,
            status: invoice.status.toLowerCase() as 'draft' | 'validated' | 'posted' | 'failed',
          };
        });

        setRecentInvoices(transformedInvoices);
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">Welcome back, {user?.name || 'User'}!</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading dashboard</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
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
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-sm sm:text-base text-gray-600">Welcome back, {user?.name || 'User'}! Here's what's happening with your invoices.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <a
            href="/invoices/create"
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
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
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg shadow-lg p-4 sm:p-6 text-white">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <p className="text-sm font-medium text-indigo-100">Total Invoices</p>
            <p className="text-2xl sm:text-3xl font-bold mt-2">
              {invoiceStats.draft + invoiceStats.validated + invoiceStats.posted + invoiceStats.failed}
            </p>
          </div>
          <div className="text-center sm:text-right">
            <p className="text-sm font-medium text-indigo-100">Success Rate</p>
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
              <h2 className="text-xl font-semibold text-gray-900">Recent Invoices</h2>
              <a
                href="/invoices/history"
                className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
              >
                View all →
              </a>
            </div>
            {recentInvoices.length > 0 ? (
              <RecentInvoices invoices={recentInvoices} />
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No invoices</h3>
                <p className="mt-1 text-sm text-gray-500">Get started by creating your first invoice.</p>
                <div className="mt-6">
                  <a
                    href="/invoices/create"
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
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