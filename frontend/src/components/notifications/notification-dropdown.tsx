'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Bell, CheckCheck, X, ExternalLink } from 'lucide-react';
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

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  onCountChange?: (count: number) => void;
}

export function NotificationDropdown({ isOpen, onClose, onCountChange }: NotificationDropdownProps) {
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (dropdownRef.current && !dropdownRef.current.contains(target)) {
        onClose();
      }
    };

    if (isOpen) {
      // Delay adding the listener to avoid catching the click that opened the dropdown
      const timeoutId = setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
      }, 100);

      return () => {
        clearTimeout(timeoutId);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen, onClose]);

  // Fetch notifications when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
      setFilter('all'); // Reset filter when opening
    }
  }, [isOpen]);

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

      // Update parent count
      const unreadCount = recentNotifications.filter((n: Notification) => !n.read).length;
      onCountChange?.(unreadCount);
    } catch (error) {
      console.error('Error fetching notifications:', error);

      // Use mock data if API fails
      const mockData = [
        {
          id: '1',
          title: 'FBR Tax Rates Updated',
          message: 'FBR has updated tax rates for 15 transaction types. Please review the changes before creating new invoices.',
          type: 'warning' as const,
          read: false,
          created_at: new Date().toISOString(),
        },
        {
          id: '2',
          title: 'New HS Codes Added',
          message: 'FBR added 127 new HS codes to the reference database. The codes are now available in the invoice creation form.',
          type: 'info' as const,
          read: true,
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
      ];

      const twoDaysAgo = new Date();
      twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);

      const recentMockData = mockData.filter((notif) => {
        const notifDate = new Date(notif.created_at);
        return notifDate >= twoDaysAgo;
      });

      setNotifications(recentMockData);

      const unreadCount = recentMockData.filter((n) => !n.read).length;
      onCountChange?.(unreadCount);
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

      const unreadCount = notifications.filter(n => !n.read && n.id !== id).length;
      onCountChange?.(unreadCount);

      toast.success('Marked as read');
    } catch (error) {
      console.error('Error marking notification as read:', error);
      toast.error('Failed to mark as read');
    }
  };

  const markAllAsRead = async () => {
    try {
      await notificationService.markAllAsRead();

      setNotifications(prev =>
        prev.map(notif => ({ ...notif, read: true }))
      );

      onCountChange?.(0);
      toast.success('All marked as read');
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
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (!isOpen) return null;

  return (
    <div
      ref={dropdownRef}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      className="fixed sm:absolute inset-x-2 sm:inset-x-auto sm:right-0 mt-2 sm:w-96 bg-white dark:bg-[#1a1a1a] rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 z-50 max-h-[80vh] sm:max-h-[600px] flex flex-col"
    >
      {/* Header */}
      <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2 sm:mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-base sm:text-lg text-[#202223] dark:text-[#e3e3e3]">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <Badge className="bg-red-600 text-white text-xs">
                {unreadCount}
              </Badge>
            )}
          </div>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors touch-manipulation"
            aria-label="Close notifications"
          >
            <X className="h-4 w-4 sm:h-5 sm:w-5" />
          </button>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-1.5 sm:gap-2">
            <button
              className={`h-8 sm:h-7 px-3 sm:px-3 text-xs font-medium rounded-md transition-colors touch-manipulation ${
                filter === 'all'
                  ? 'bg-[#008060] text-white dark:bg-[#00a876]'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
                setFilter('all');
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
              }}
            >
              All
            </button>
            <button
              className={`h-8 sm:h-7 px-3 sm:px-3 text-xs font-medium rounded-md transition-colors touch-manipulation ${
                filter === 'unread'
                  ? 'bg-[#008060] text-white dark:bg-[#00a876]'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
                setFilter('unread');
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
              }}
            >
              Unread
            </button>
          </div>

          {unreadCount > 0 && (
            <button
              className="h-8 sm:h-7 px-2.5 sm:px-2 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 rounded-md transition-colors flex items-center gap-1 touch-manipulation"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
                markAllAsRead();
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
              }}
            >
              <CheckCheck className="h-3.5 w-3.5 sm:h-3 sm:w-3" />
              <span className="hidden sm:inline">Mark all</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications List */}
      <div className="overflow-y-auto flex-1">
        {loading ? (
          <div className="flex items-center justify-center py-8 sm:py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#008060] dark:border-[#00a876]"></div>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="text-center py-8 sm:py-12 px-4">
            <Bell className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
              No notifications
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {filter === 'unread'
                ? "You're all caught up!"
                : "You don't have any notifications yet."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-3 sm:p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                  !notification.read ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start sm:items-center gap-2 mb-1 flex-wrap">
                      <h4 className="font-medium text-sm text-[#202223] dark:text-[#e3e3e3] break-words">
                        {notification.title}
                      </h4>
                      <Badge className={`${getTypeColor(notification.type)} text-xs px-1.5 py-0 shrink-0`}>
                        {notification.type}
                      </Badge>
                    </div>
                    <p className="text-xs text-[#6d7175] dark:text-[#8c9196] line-clamp-2 mb-1 break-words">
                      {notification.message}
                    </p>
                    <p className="text-xs text-[#8c9196] dark:text-[#6d7175]">
                      {formatDate(notification.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {!notification.read && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          markAsRead(notification.id);
                        }}
                        onMouseDown={(e) => e.stopPropagation()}
                        className="p-1.5 sm:p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors touch-manipulation"
                        title="Mark as read"
                        aria-label="Mark as read"
                      >
                        <CheckCheck className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 sm:p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            router.push('/notifications');
            onClose();
          }}
          onMouseDown={(e) => e.stopPropagation()}
          className="w-full text-center text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-medium flex items-center justify-center gap-1.5 py-2 sm:py-1 touch-manipulation"
        >
          View all notifications
          <ExternalLink className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
        </button>
        <p className="text-xs text-center text-gray-500 dark:text-gray-400 mt-2">
          Auto-removed after 2 days
        </p>
      </div>
    </div>
  );
}
