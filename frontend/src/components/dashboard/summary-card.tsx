import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SummaryCardProps {
  title: string;
  count: number;
  icon: string;
  color: string;
}

export function SummaryCard({ title, count, icon, color }: SummaryCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <span className={`text-2xl ${color} rounded-full w-8 h-8 flex items-center justify-center text-white`}>
          {icon}
        </span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{count}</div>
      </CardContent>
    </Card>
  );
}