'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import {
  getPostingStatus,
  emergencyPauseAutoPosting,
  PostingStatusResponse,
} from '@/services/autoPostingApi';

export default function AutoPostingStatus() {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<PostingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load status
  const loadStatus = async () => {
    if (!isAuthenticated) return;

    try {
      setError(null);
      const data = await getPostingStatus();
      setStatus(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load posting status');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadStatus();
    }
  }, [isAuthenticated]);

  // Poll every 30 seconds
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleEmergencyPause = async () => {
    if (!isAuthenticated) return;
    if (!confirm('Are you sure you want to pause auto-posting immediately?')) return;

    try {
      await emergencyPauseAutoPosting();
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to pause auto-posting');
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (!status) return null;

  const getStatusColor = () => {
    switch (status.status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-200';
      case 'outside_hours':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200';
      case 'limit_reached':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-200';
      case 'paused':
      case 'disabled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-200';
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case 'active':
        return '🟢 Active - Auto-posting enabled';
      case 'outside_hours':
        return '🟡 Outside posting hours';
      case 'limit_reached':
        return '🟠 Daily limit reached';
      case 'paused':
        return '⏸️ Paused';
      case 'disabled':
        return '⚫ Disabled';
      default:
        return 'Unknown status';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold">Auto-Posting Status</h3>
        {status.auto_posting_enabled && status.status === 'active' && (
          <button
            onClick={handleEmergencyPause}
            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
          >
            Emergency Pause
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
          <p className="text-red-800 dark:text-red-200 text-sm">{error}</p>
        </div>
      )}

      {/* Status Indicator */}
      <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-4 ${getStatusColor()}`}>
        {getStatusText()}
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Posted Today</p>
          <p className="text-2xl font-bold">{status.today_posted_count}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Failed Today</p>
          <p className="text-2xl font-bold text-red-600">{status.today_failed_count}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Remaining</p>
          <p className="text-2xl font-bold">{status.remaining_limit}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Daily Limit</p>
          <p className="text-2xl font-bold">{status.daily_limit}</p>
        </div>
      </div>

      {/* Additional Info */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-400">Environment:</span>
          <span className="font-medium">{status.environment}</span>
        </div>
        {status.next_check_time && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Next Check:</span>
            <span className="font-medium">
              {new Date(status.next_check_time).toLocaleTimeString()}
            </span>
          </div>
        )}
        {status.paused_until && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Paused Until:</span>
            <span className="font-medium">
              {new Date(status.paused_until).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* Quick Link to Settings */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <a
          href="/settings"
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Configure auto-posting settings →
        </a>
      </div>
    </div>
  );
}
