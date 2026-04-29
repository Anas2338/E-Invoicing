'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Bell, CheckCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { notificationService } from '@/lib/api/api-client';
import { toast } from 'react-toastify';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  created_at: string;
}

export default function NotificationsPage() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await notificationService.getAll();

      // Filter out notifications older than 2 days
      const twoDaysAgo = new Date();
      twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);

      const recentNotifications = response.filter((notif: Notification) => {
        const notifDate = new Date(notif.created_at);
        return notifDate >= twoDaysAgo;
      });

      setNotifications(recentNotifications);
    } catch (error) {
      console.error('Error fetching notifications:', error);

      // Use mock data if API fails (for development)
      const mockData: Notification[] = [
        {
          id: '1',
          title: 'FBR Tax Rates Updated',
          message: 'FBR has updated tax rates for 15 transaction types. The changes affect standard rate calculations. Please review before creating new invoices.',
          type: 'warning' as const,
          read: false,
          created_at: new Date().toISOString(),
        },
        {
          id: '2',
          title: 'New HS Codes Added',
          message: 'FBR added 127 new HS codes to the reference database. The codes are now available in the invoice creation form dropdown.',
          type: 'info' as const,
          read: true,
          created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
        },
        {
          id: '3',
          title: 'Province Codes Updated',
          message: 'FBR updated province codes for Balochistan and KPK. Existing invoices are not affected, but new invoices will use updated codes.',
          type: 'info' as const,
          read: false,
          created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago (will be filtered out)
        },
      ];

      // Filter mock data as well
      const twoDaysAgo = new Date();
      twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);

      const recentMockData = mockData.filter((notif) => {
        const notifDate = new Date(notif.created_at);
        return notifDate >= twoDaysAgo;
      });

      setNotifications(recentMockData);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (id: string) => {
    try {
      await notificationService.markAsRead(id);

      setNotifications(prev =>
        prev.map(notif =>
          notif.id === id ? { ...notif, read: true } : notif
        )
      );
      toast.success('Notification marked as read');
    } catch (error) {
      console.error('Error marking notification as read:', error);
      toast.error('Failed to mark notification as read');
    }
  };

  const markAllAsRead = async () => {
    try {
      await notificationService.markAllAsRead();

      setNotifications(prev =>
        prev.map(notif => ({ ...notif, read: true }))
      );
      toast.success('All notifications marked as read');
    } catch (error) {
      console.error('Error marking all as read:', error);
      toast.error('Failed to mark all as read');
    }
  };

  const filteredNotifications = notifications.filter(notif =>
    filter === 'all' ? true : !notif.read
  );

  const unreadCount = notifications.filter(n => !n.read).length;

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      default:
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading notifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/dashboard')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] flex items-center gap-3">
            <Bell className="h-8 w-8" />
            Notifications
            {unreadCount > 0 && (
              <Badge className="bg-red-600 text-white">
                {unreadCount} new
              </Badge>
            )}
          </h1>
          <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
            Get notified when FBR updates reference data (tax rates, HS codes, provinces, etc.)
          </p>
          <p className="mt-1 text-xs text-[#8c9196] dark:text-[#6d7175]">
            ℹ️ Notifications older than 2 days are automatically removed
          </p>
        </div>

        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={markAllAsRead}
            className="flex items-center gap-2"
          >
            <CheckCheck className="h-4 w-4" />
            Mark all as read
          </Button>
        )}
      </div>

      <div className="flex gap-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({notifications.length})
        </Button>
        <Button
          variant={filter === 'unread' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('unread')}
        >
          Unread ({unreadCount})
        </Button>
      </div>

      {filteredNotifications.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Bell className="h-12 w-12 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
              <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
                No notifications
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                {filter === 'unread'
                  ? "You're all caught up! No unread notifications."
                  : "You don't have any notifications yet."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredNotifications.map((notification) => (
            <Card
              key={notification.id}
              className={`transition-all ${
                !notification.read
                  ? 'border-l-4 border-l-[#008060] dark:border-l-[#00a876] bg-blue-50/50 dark:bg-blue-950/20'
                  : ''
              }`}
            >
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {notification.title}
                      </h3>
                      <Badge className={getTypeColor(notification.type)}>
                        {notification.type}
                      </Badge>
                      {!notification.read && (
                        <Badge className="bg-[#008060] text-white dark:bg-[#00a876]">
                          New
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-2">
                      {notification.message}
                    </p>
                    <p className="text-xs text-[#8c9196] dark:text-[#6d7175]">
                      {formatDate(notification.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {!notification.read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => markAsRead(notification.id)}
                        className="h-8"
                        title="Mark as read"
                      >
                        <CheckCheck className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
