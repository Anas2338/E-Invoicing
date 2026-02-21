'use client';

import { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'react-toastify';

interface EnvironmentSelectorProps {
  currentEnv: 'sandbox' | 'production';
  canAccessProduction: boolean;
  onEnvironmentChange: (env: 'sandbox' | 'production') => void;
}

export function EnvironmentSelector({ currentEnv, canAccessProduction, onEnvironmentChange }: EnvironmentSelectorProps) {
  const [selectedEnv, setSelectedEnv] = useState<'sandbox' | 'production'>(currentEnv);

  useEffect(() => {
    setSelectedEnv(currentEnv);
  }, [currentEnv]);

  const handleEnvChange = (value: string) => {
    if (value === 'production' && !canAccessProduction) {
      toast.warning('You do not have access to the production environment. Please contact your administrator.');
      return;
    }

    const env = value as 'sandbox' | 'production';
    setSelectedEnv(env);
    onEnvironmentChange(env);
  };

  return (
    <div className="flex items-center space-x-2">
      <span className="text-sm font-medium">Environment:</span>
      <Select value={selectedEnv} onValueChange={handleEnvChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Select environment" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="sandbox">Sandbox</SelectItem>
          {canAccessProduction && <SelectItem value="production">Production</SelectItem>}
          {!canAccessProduction && (
            <SelectItem value="production" disabled={!canAccessProduction}>
              Production (restricted)
            </SelectItem>
          )}
        </SelectContent>
      </Select>
      <span className={`text-xs px-2 py-1 rounded ${
        selectedEnv === 'sandbox' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'
      }`}>
        {selectedEnv.toUpperCase()}
      </span>
    </div>
  );
}