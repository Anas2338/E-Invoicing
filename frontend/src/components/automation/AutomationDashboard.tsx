'use client';

import { useEffect, useState } from 'react';
import { automationApi, DashboardStats } from '@/services/automationApi';

export default function AutomationDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await automationApi.getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-[#6d7175] dark:text-[#8c9196]">Loading statistics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl p-4">
        <p className="text-[#d72c0d] dark:text-[#ff6f59]">{error}</p>
        <button
          onClick={loadStats}
          className="mt-2 text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] underline font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const statCards = [
    {
      label: 'Total Invoices',
      value: stats.total_invoices,
      color: 'bg-[#dbeafe] border-[#bfdbfe] text-[#1e40af] dark:bg-[#1e3a8a]/30 dark:border-[#1e3a8a] dark:text-[#60a5fa]',
    },
    {
      label: 'Pending',
      value: stats.pending_count,
      color: 'bg-[#fef3c7] border-[#fde68a] text-[#92400e] dark:bg-[#451a03]/30 dark:border-[#451a03] dark:text-[#fbbf24]',
    },
    {
      label: 'Validated',
      value: stats.validated_count,
      color: 'bg-[#e0e7ff] border-[#c7d2fe] text-[#3730a3] dark:bg-[#312e81]/30 dark:border-[#312e81] dark:text-[#a5b4fc]',
    },
    {
      label: 'Paused',
      value: stats.paused_count,
      color: 'bg-[#fef3c7] border-[#fde68a] text-[#92400e] dark:bg-[#451a03]/30 dark:border-[#451a03] dark:text-[#fbbf24]',
    },
    {
      label: 'Transferred',
      value: stats.transferred_count,
      color: 'bg-[#d1fae5] border-[#a7f3d0] text-[#065f46] dark:bg-[#064e3b]/30 dark:border-[#065f46] dark:text-[#34d399]',
    },
    {
      label: 'Transfer Failed',
      value: stats.transfer_failed_count,
      color: 'bg-[#ffedd5] border-[#fed7aa] text-[#7c2d12] dark:bg-[#431407]/30 dark:border-[#7c2d12] dark:text-[#fb923c]',
    },
    {
      label: 'Failed',
      value: stats.failed_count,
      color: 'bg-[#fee2e2] border-[#fecaca] text-[#991b1b] dark:bg-[#7f1d1d]/30 dark:border-[#7f1d1d] dark:text-[#f87171]',
    },
    {
      label: 'Expired',
      value: stats.expired_count,
      color: 'bg-[#f6f6f7] border-[#e1e3e5] text-[#6d7175] dark:bg-[#2e2e2e] dark:border-[#404040] dark:text-[#8c9196]',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">Dashboard Statistics</h2>
        <button
          onClick={loadStats}
          className="text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold transition-colors duration-150"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((card) => (
          <div
            key={card.label}
            className={`border-2 rounded-xl p-6 ${card.color} transition-all duration-150 hover:shadow-md`}
          >
            <div className="text-sm font-semibold mb-2">{card.label}</div>
            <div className="text-3xl font-bold">{card.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
