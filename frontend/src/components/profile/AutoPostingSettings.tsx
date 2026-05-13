'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'react-toastify';
import { Zap, Clock, AlertTriangle, Loader2 } from 'lucide-react';
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
  const environment = 'PRODUCTION';
  const [dailyLimit, setDailyLimit] = useState(100);

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

      setEnabled(data.auto_posting_enabled);
      setStartTime(data.auto_posting_start_time.substring(0, 5));
      setEndTime(data.auto_posting_end_time.substring(0, 5));
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
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update auto-posting');
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

      if (dailyLimit < 1 || dailyLimit > 1000) {
        setError('Daily limit must be between 1 and 1000');
        return;
      }

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
    setEnabled(result.auto_posting_enabled);
    setStartTime(result.auto_posting_start_time.substring(0, 5));
    setEndTime(result.auto_posting_end_time.substring(0, 5));
    setDailyLimit(result.auto_posting_daily_limit);
    window.location.reload();
    setShowProductionConfirm(false);
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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Zap className="h-5 w-5" />
            Auto-Posting Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
              <Zap className="h-5 w-5" />
              Auto-Posting Settings
            </CardTitle>
            <CardDescription className="text-sm mt-1">
              Configure automatic posting of validated invoices to FBR
            </CardDescription>
          </div>
          {enabled && (
            <Button
              onClick={handleEmergencyPause}
              disabled={saving}
              variant="destructive"
              size="sm"
              className="flex-shrink-0"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Emergency Pause
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {success && (
          <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-sm text-green-800 dark:text-green-200">{success}</p>
          </div>
        )}

        <div className="space-y-6">
          {/* Enable/Disable Toggle */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <label className="text-sm font-medium text-[#202223] dark:text-[#e3e3e3]">Enable Auto-Posting</label>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                Automatically post validated invoices to FBR during configured hours
              </p>
            </div>
            <button
              onClick={handleToggle}
              disabled={saving}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ${
                enabled ? 'bg-[#008060] dark:bg-[#00a876]' : 'bg-gray-200 dark:bg-gray-700'
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#202223] dark:text-[#e3e3e3] mb-2">Start Time</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                disabled={!enabled}
                className="w-full px-3 py-2 border border-[#c9cccf] dark:border-[#5c5f62] rounded-lg bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#202223] dark:text-[#e3e3e3] mb-2">End Time</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                disabled={!enabled}
                className="w-full px-3 py-2 border border-[#c9cccf] dark:border-[#5c5f62] rounded-lg bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] text-sm"
              />
            </div>
          </div>
          <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
            <Clock className="h-3.5 w-3.5 inline mr-1" />
            Midnight-spanning windows are supported (e.g., 22:00 - 02:00)
          </p>

          {/* Daily Limit */}
          <div>
            <label className="block text-sm font-medium text-[#202223] dark:text-[#e3e3e3] mb-2">
              Daily Limit (1-1000)
            </label>
            <input
              type="number"
              min="1"
              max="1000"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(parseInt(e.target.value) || 1)}
              disabled={!enabled}
              className="w-full sm:w-48 px-3 py-2 border border-[#c9cccf] dark:border-[#5c5f62] rounded-lg bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] text-sm"
            />
            <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
              Maximum number of invoices to post per day
            </p>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button
              onClick={handleSave}
              disabled={saving}
              className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Configuration'
              )}
            </Button>
          </div>
        </div>

        {/* Production Confirmation Dialog */}
        {showProductionConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-[#1a1a1a] rounded-xl p-6 max-w-md w-full shadow-lg">
              <h3 className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3] mb-4">Switch to Production?</h3>
              <p className="text-[#6d7175] dark:text-[#8c9196] text-sm mb-6">
                You are about to switch auto-posting to Production environment. This will post invoices
                to the live FBR system using your Production credentials. Are you sure?
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  onClick={() => setShowProductionConfirm(false)}
                  variant="outline"
                >
                  Cancel
                </Button>
                <Button
                  onClick={saveConfig}
                  className="bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64]"
                >
                  Confirm
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
