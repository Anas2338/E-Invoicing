import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SummaryCardProps {
  title: string;
  count: number;
  icon: string;
  color: string;
}

export function SummaryCard({ title, count, icon, color }: SummaryCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow duration-150">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">{title}</CardTitle>
        <span className={`text-2xl ${color} rounded-xl w-10 h-10 flex items-center justify-center text-white shadow-sm`}>
          {icon}
        </span>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">{count}</div>
      </CardContent>
    </Card>
  );
}