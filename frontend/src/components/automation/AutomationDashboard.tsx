'use client';

import { useEffect, useState } from 'react';
import { automationApi, DashboardStats } from '@/services/automationApi';
import { SummaryCard } from '@/components/dashboard/summary-card';
import {
  FileText,
  Clock,
  FileCheck,
  PauseCircle,
  Send,
  AlertTriangle,
  XCircle,
  CalendarX
} from 'lucide-react';

interface AutomationDashboardProps {
  refreshTrigger?: number;
}

export default function AutomationDashboard({ refreshTrigger = 0 }: AutomationDashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [refreshTrigger]);

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

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-[#008060] border-t-transparent" />
          <span className="text-[#6d7175] dark:text-[#8c9196] text-sm font-medium">Loading statistics...</span>
        </div>
      </div>
    );
  }

  if (error && !stats) {
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
      title: 'Total Invoices',
      count: stats.total_invoices,
      icon: <FileText className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-blue-600 dark:bg-blue-500 shadow-xl shadow-blue-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-blue-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Pending',
      count: stats.pending_count,
      icon: <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-amber-500 dark:bg-amber-400 shadow-xl shadow-amber-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-amber-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Validated',
      count: stats.validated_count,
      icon: <FileCheck className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-emerald-600 dark:bg-emerald-500 shadow-xl shadow-emerald-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-emerald-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Paused',
      count: stats.paused_count,
      icon: <PauseCircle className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-amber-500 dark:bg-amber-400 shadow-xl shadow-amber-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-amber-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Transferred',
      count: stats.transferred_count,
      icon: <Send className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-purple-600 dark:bg-purple-500 shadow-xl shadow-purple-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-purple-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Transfer Failed',
      count: stats.transfer_failed_count,
      icon: <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-orange-600 dark:bg-orange-500 shadow-xl shadow-orange-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-orange-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Failed',
      count: stats.failed_count,
      icon: <XCircle className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-rose-600 dark:bg-rose-500 shadow-xl shadow-rose-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-rose-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
    {
      title: 'Expired',
      count: stats.expired_count,
      icon: <CalendarX className="h-4 w-4 sm:h-5 sm:w-5 text-white" />,
      color: 'bg-slate-500 dark:bg-slate-400 shadow-xl shadow-slate-500/30',
      bg: 'bg-white dark:bg-[#1a1a1a] border-2 border-slate-400 dark:border-neutral-800/80 rounded-3xl shadow-lg p-4 text-xl',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
      {statCards.map((card) => (
        <SummaryCard
          key={card.title}
          title={card.title}
          count={card.count}
          icon={card.icon}
          color={card.color}
          bg={card.bg}
        />
      ))}
    </div>
  );
}
