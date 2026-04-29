'use client';

import { Card } from '@/components/ui/card';
import { FileText, Clock, CheckCircle, XCircle, AlertCircle, Calendar, Ban } from 'lucide-react';

interface StatsProps {
  stats: {
    total_invoices: number;
    pending_count: number;
    expired_count: number;
    validated_count: number;
    transferred_count: number;
    transfer_failed_count: number;
    failed_count: number;
    blocked_count: number;
  };
}

export function AutomationStats({ stats }: StatsProps) {
  const statCards = [
    {
      label: 'Total Invoices',
      value: stats.total_invoices,
      icon: FileText,
      color: 'text-[#1e40af] dark:text-[#60a5fa]',
      bgColor: 'bg-[#dbeafe] dark:bg-[#1e3a8a]/30'
    },
    {
      label: 'Pending',
      value: stats.pending_count,
      icon: Clock,
      color: 'text-[#92400e] dark:text-[#fbbf24]',
      bgColor: 'bg-[#fef3c7] dark:bg-[#451a03]/30'
    },
    {
      label: 'Transferred',
      value: stats.transferred_count,
      icon: CheckCircle,
      color: 'text-[#065f46] dark:text-[#34d399]',
      bgColor: 'bg-[#d1fae5] dark:bg-[#064e3b]/30'
    },
    {
      label: 'Transfer Failed',
      value: stats.transfer_failed_count,
      icon: XCircle,
      color: 'text-[#7c2d12] dark:text-[#fb923c]',
      bgColor: 'bg-[#ffedd5] dark:bg-[#431407]/30'
    },
    {
      label: 'Failed',
      value: stats.failed_count,
      icon: XCircle,
      color: 'text-[#991b1b] dark:text-[#f87171]',
      bgColor: 'bg-[#fee2e2] dark:bg-[#7f1d1d]/30'
    },
    {
      label: 'Blocked',
      value: stats.blocked_count,
      icon: Ban,
      color: 'text-[#7c2d12] dark:text-[#fb923c]',
      bgColor: 'bg-[#ffedd5] dark:bg-[#431407]/30'
    },
    {
      label: 'Validated',
      value: stats.validated_count,
      icon: AlertCircle,
      color: 'text-[#3730a3] dark:text-[#a5b4fc]',
      bgColor: 'bg-[#e0e7ff] dark:bg-[#312e81]/30'
    },
    {
      label: 'Expired',
      value: stats.expired_count,
      icon: Calendar,
      color: 'text-[#6d7175] dark:text-[#8c9196]',
      bgColor: 'bg-[#f6f6f7] dark:bg-[#2e2e2e]'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-4">
      {statCards.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label} className="p-4 hover:shadow-lg transition-shadow duration-150">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">{stat.label}</p>
                <p className="text-2xl font-bold text-[#202223] dark:text-[#e3e3e3] mt-1">{stat.value}</p>
              </div>
              <div className={`${stat.bgColor} p-3 rounded-xl`}>
                <Icon className={`h-6 w-6 ${stat.color}`} />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
