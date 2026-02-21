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
    color: 'bg-blue-50 hover:bg-blue-100 border-blue-200',
  },
  {
    title: 'View All Invoices',
    description: 'Browse and manage all your invoices',
    icon: '📋',
    href: '/invoices/history',
    color: 'bg-green-50 hover:bg-green-100 border-green-200',
  },
  {
    title: 'Settings',
    description: 'Manage your account and preferences',
    icon: '⚙️',
    href: '/settings',
    color: 'bg-purple-50 hover:bg-purple-100 border-purple-200',
  },
  {
    title: 'Help & Support',
    description: 'Get help with FBR e-invoicing',
    icon: '❓',
    href: '/help',
    color: 'bg-orange-50 hover:bg-orange-100 border-orange-200',
  },
];

export function QuickActionsPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3">
          {quickActions.map((action) => (
            <a
              key={action.title}
              href={action.href}
              className={`flex items-center p-3 rounded-lg border-2 transition-colors ${action.color}`}
            >
              <span className="text-2xl mr-3">{action.icon}</span>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900">{action.title}</h3>
                <p className="text-xs text-gray-600">{action.description}</p>
              </div>
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
