import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface QuickAction {
  title: string;
  description: string;
  icon: string;
  href: string;
  color: string;
}

const quickActions: QuickAction[] = [
  {
    title: 'Create Invoice',
    description: 'Create a new invoice for FBR submission',
    icon: '📝',
    href: '/invoices/create',
    color: 'bg-[#f1f8f5] hover:bg-[#e3f1eb] border-[#b4e3d0] dark:bg-[#0d3d2f]/20 dark:hover:bg-[#0d3d2f]/30 dark:border-[#1a5c45]',
  },
  {
    title: 'View All Invoices',
    description: 'Browse and manage all your invoices',
    icon: '📋',
    href: '/invoices/history',
    color: 'bg-[#f6f6f7] hover:bg-[#e8e9ea] border-[#c9cccf] dark:bg-[#2e2e2e]/20 dark:hover:bg-[#2e2e2e]/30 dark:border-[#404040]',
  },
  {
    title: 'Settings',
    description: 'Manage your account and preferences',
    icon: '⚙️',
    href: '/settings',
    color: 'bg-[#f6f6f7] hover:bg-[#e8e9ea] border-[#c9cccf] dark:bg-[#2e2e2e]/20 dark:hover:bg-[#2e2e2e]/30 dark:border-[#404040]',
  },
  {
    title: 'Help & Support',
    description: 'Get help with FBR e-invoicing',
    icon: '❓',
    href: '/help',
    color: 'bg-[#f6f6f7] hover:bg-[#e8e9ea] border-[#c9cccf] dark:bg-[#2e2e2e]/20 dark:hover:bg-[#2e2e2e]/30 dark:border-[#404040]',
  },
];

export function QuickActionsPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3">
          {quickActions.map((action) => (
            <a
              key={action.title}
              href={action.href}
              className={`flex items-center p-3 rounded-xl border-2 transition-all duration-150 ${action.color}`}
            >
              <span className="text-2xl mr-3">{action.icon}</span>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">{action.title}</h3>
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">{action.description}</p>
              </div>
              <svg className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
