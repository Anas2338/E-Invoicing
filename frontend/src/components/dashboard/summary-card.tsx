import { type ReactNode } from 'react';
import { Card } from '@/components/ui/card';

interface SummaryCardProps {
  title: string;
  count: number | string;
  icon: ReactNode;
  color: string;
  bg?: string;
  subtitle?: string;
  className?: string;
  countClassName?: string;
}

export function SummaryCard({ title, count, icon, color, bg, subtitle, className = '', countClassName = '' }: SummaryCardProps) {
  return (
    <Card className={`hover:shadow-lg transition-shadow duration-150 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-2 shadow-md ${bg || ''} ${className}`}>
      <div className={`${color} rounded-lg w-8 h-8 sm:w-9 sm:h-9 lg:w-10 lg:h-10 flex items-center justify-center text-white text-sm sm:text-base shadow-sm flex-shrink-0`}>
        {icon}
      </div>
      <div className="flex-1 text-center">
        <div className={`text-lg sm:text-xl font-extrabold text-[#202223] dark:text-white ${countClassName}`}>{count}</div>
        <div className="text-xs sm:text-sm lg:text-base font-extrabold text-[#202223] dark:text-white/90">{title}</div>
        {subtitle && (
          <p className="text-xs text-[#6d7175] dark:text-[#8c9196] mt-0.5">{subtitle}</p>
        )}
      </div>
    </Card>
  );
}