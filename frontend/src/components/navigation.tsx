'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';
import { Button } from '@/components/ui/button';
import { NotificationDropdown } from '@/components/notifications/notification-dropdown';
import { Home, FileText, LogOut, Menu, X, Zap, Bell, HelpCircle } from 'lucide-react';
import { notificationService } from '@/lib/api/api-client';


export function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const { signOut, user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [notificationDropdownOpen, setNotificationDropdownOpen] = useState(false);
  const fetchingRef = useRef(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch notification count on mount and periodically
  useEffect(() => {
    const fetchNotificationCount = async () => {
      if (fetchingRef.current) return;

      fetchingRef.current = true;
      try {
        const response = await notificationService.getUnreadCount();
        setNotificationCount(response.count);
      } catch (error) {
        // Silently fail
      } finally {
        fetchingRef.current = false;
      }
    };

    fetchNotificationCount();

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = setInterval(fetchNotificationCount, 60000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const handleLogout = async () => {
    await signOut();
  };

  const allNavItems = [
    { name: 'Dashboard', path: '/dashboard', icon: Home },
    { name: 'Automation', path: '/automation', icon: Zap, requiresAutomation: true },
    { name: 'Invoices', path: '/invoices/history', icon: FileText },
  ];

  const navItems = allNavItems.filter(item => {
    if (item.requiresAutomation) {
      return user?.automation_enabled === true;
    }
    return true;
  });

  return (
    <nav className="sticky top-0 z-50 bg-white dark:bg-[#1a1a1a] shadow-sm border-b border-[#e1e3e5] dark:border-[#2e2e2e] mb-2">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <button
                onClick={() => router.push('/dashboard')}
                className="text-2xl font-bold text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] transition-colors cursor-pointer tracking-tight"
              >
                Taxntec
              </button>
            </div>
            {/* Desktop Navigation */}
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.path || pathname.startsWith(item.path);
                return (
                  <button
                    key={item.path}
                    onClick={() => router.push(item.path as any)}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-semibold transition-colors ${
                      isActive
                        ? 'border-[#008060] text-[#202223] dark:text-[#e3e3e3] dark:border-[#00a876]'
                        : 'border-transparent text-[#6d7175] dark:text-[#8c9196] hover:border-[#c9cccf] dark:hover:border-[#404040] hover:text-[#202223] dark:hover:text-[#e3e3e3]'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Desktop Actions */}
          <div className="hidden sm:flex items-center gap-1">
            {/* Notifications */}
            <button
              onClick={() => setNotificationDropdownOpen(true)}
              className="relative p-2 text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {notificationCount > 0 && (
                <span className="absolute top-0.5 right-0.5 inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold leading-none text-white bg-red-600 rounded-full">
                  {notificationCount > 9 ? '9+' : notificationCount}
                </span>
              )}
            </button>

            {/* Help */}
            <button
              onClick={() => router.push('/help')}
              className="p-2 text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              aria-label="Help"
            >
              <HelpCircle className="h-5 w-5" />
            </button>

            {/* Notification Dropdown */}
            <NotificationDropdown
              isOpen={notificationDropdownOpen}
              onClose={() => setNotificationDropdownOpen(false)}
              onCountChange={setNotificationCount}
            />

            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>

          {/* Mobile Actions */}
          <div className="flex items-center gap-1 sm:hidden">
            {/* Notifications */}
            <button
              onClick={() => setNotificationDropdownOpen(true)}
              className="relative p-2 text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {notificationCount > 0 && (
                <span className="absolute top-0.5 right-0.5 inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold leading-none text-white bg-red-600 rounded-full">
                  {notificationCount > 9 ? '9+' : notificationCount}
                </span>
              )}
            </button>

            {/* Help */}
            <button
              onClick={() => router.push('/help')}
              className="p-2 text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              aria-label="Help"
            >
              <HelpCircle className="h-5 w-5" />
            </button>

            <NotificationDropdown
              isOpen={notificationDropdownOpen}
              onClose={() => setNotificationDropdownOpen(false)}
              onCountChange={setNotificationCount}
            />

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            >
              <span className="sr-only">Open main menu</span>
              {mobileMenuOpen ? (
                <X className="block h-6 w-6" />
              ) : (
                <Menu className="block h-6 w-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-gray-200 dark:border-gray-800">
          <div className="pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.path || pathname.startsWith(item.path);
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    router.push(item.path as any);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center px-4 py-2 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 border-l-4 border-indigo-500 text-indigo-700 dark:text-indigo-400'
                      : 'border-l-4 border-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:text-gray-800 dark:hover:text-gray-300'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {item.name}
                </button>
              );
            })}
            <button
              onClick={() => {
                handleLogout();
                setMobileMenuOpen(false);
              }}
              className="w-full flex items-center px-4 py-2 text-base font-medium border-l-4 border-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:text-gray-800 dark:hover:text-gray-300"
            >
              <LogOut className="h-5 w-5 mr-3" />
              Logout
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
