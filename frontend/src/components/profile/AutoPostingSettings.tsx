'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import {
  getAutoPostingConfig,
  updateAutoPostingConfig,
  emergencyPauseAutoPosting,
  AutoPostingConfig,
  AutoPostingConfigUpdate,
} from '@/services/autoPostingApi';

export default function AutoPostingSettings() {
  const { isAuthenticated } = useAuth();
  const [config, setConfig] = useState<AutoPostingConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showProductionConfirm, setShowProductionConfirm] = useState(false);

  // Form state
  const [enabled, setEnabled] = useState(false);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('18:00');
  const [environment, setEnvironment] = useState<'SANDBOX' | 'PRODUCTION'>('SANDBOX');
  const [dailyLimit, setDailyLimit] = useState(100);

  // Load configuration
  useEffect(() => {
    if (isAuthenticated) {
      loadConfig();
    }
  }, [isAuthenticated]);

  const loadConfig = async () => {
    if (!isAuthenticated) return;

    try {
      setLoading(true);
      setError(null);
      const data = await getAutoPostingConfig();
      setConfig(data);

      // Update form state
      setEnabled(data.auto_posting_enabled);
      setStartTime(data.auto_posting_start_time.substring(0, 5)); // HH:MM format
      setEndTime(data.auto_posting_end_time.substring(0, 5));
      setEnvironment(data.auto_posting_environment);
      setDailyLimit(data.auto_posting_daily_limit);
    } catch (err: any) {
      setError(err.message || 'Failed to load auto-posting configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    const newEnabled = !enabled;
    setEnabled(newEnabled);

    // Auto-save when toggling
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const update: AutoPostingConfigUpdate = {
        auto_posting_enabled: newEnabled,
        auto_posting_start_time: `${startTime}:00`,
        auto_posting_end_time: `${endTime}:00`,
        auto_posting_environment: environment,
        auto_posting_daily_limit: dailyLimit,
      };

      const result = await updateAutoPostingConfig(update);
      setConfig(result);
      setSuccess(`Auto-posting ${newEnabled ? 'enabled' : 'disabled'} successfully`);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update auto-posting');
      // Revert the toggle on error
      setEnabled(!newEnabled);
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Validate daily limit
      if (dailyLimit < 1 || dailyLimit > 1000) {
        setError('Daily limit must be between 1 and 1000');
        return;
      }

      // Check if switching to Production
      if (environment === 'PRODUCTION' && config?.auto_posting_environment === 'SANDBOX') {
        setShowProductionConfirm(true);
        return;
      }

      await saveConfig();
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const saveConfig = async () => {
    if (!isAuthenticated) return;

    const update: AutoPostingConfigUpdate = {
      auto_posting_enabled: enabled,
      auto_posting_start_time: `${startTime}:00`,
      auto_posting_end_time: `${endTime}:00`,
      auto_posting_environment: environment,
      auto_posting_daily_limit: dailyLimit,
    };

    const result = await updateAutoPostingConfig(update);
    setConfig(result);
    setSuccess('Auto-posting configuration saved successfully');
    setShowProductionConfirm(false);

    // Clear success message after 3 seconds
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleEmergencyPause = async () => {
    if (!isAuthenticated) return;
    if (!confirm('Are you sure you want to pause auto-posting immediately?')) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await emergencyPauseAutoPosting();
      setEnabled(false);
      setSuccess('Auto-posting paused successfully');
      await loadConfig();
    } catch (err: any) {
      setError(err.message || 'Failed to pause auto-posting');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Auto-Posting Settings</h2>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Auto-Posting Settings</h2>
        {enabled && (
          <button
            onClick={handleEmergencyPause}
            disabled={saving}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
          >
            Emergency Pause
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded">
          <p className="text-green-800 dark:text-green-200">{success}</p>
        </div>
      )}

      <div className="space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <label className="text-sm font-medium">Enable Auto-Posting</label>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Automatically post validated invoices to FBR during configured hours
            </p>
          </div>
          <button
            onClick={handleToggle}
            disabled={saving}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
            } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Time Window */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Start Time</label>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              disabled={!enabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">End Time</label>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              disabled={!enabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 disabled:opacity-50"
            />
          </div>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Midnight-spanning windows are supported (e.g., 22:00 - 02:00)
        </p>

        {/* Environment */}
        <div>
          <label className="block text-sm font-medium mb-2">Environment</label>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value as 'SANDBOX' | 'PRODUCTION')}
            disabled={!enabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 disabled:opacity-50"
          >
            <option value="SANDBOX">Sandbox (Testing)</option>
            <option value="PRODUCTION">Production (Live)</option>
          </select>
          {environment === 'PRODUCTION' && (
            <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
              ⚠️ Production posting will use real FBR credentials and create actual invoices
            </p>
          )}
        </div>

        {/* Daily Limit */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Daily Limit (1-1000)
          </label>
          <input
            type="number"
            min="1"
            max="1000"
            value={dailyLimit}
            onChange={(e) => setDailyLimit(parseInt(e.target.value) || 1)}
            disabled={!enabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 disabled:opacity-50"
          />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Maximum number of invoices to post per day
          </p>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      {/* Production Confirmation Dialog */}
      {showProductionConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md">
            <h3 className="text-lg font-semibold mb-4">Switch to Production?</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              You are about to switch auto-posting to Production environment. This will post invoices
              to the live FBR system using your Production credentials. Are you sure?
            </p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setShowProductionConfirm(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={saveConfig}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
