'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useExcelStaging } from '@/contexts/ExcelStagingContext';
import ExcelStagingGrid from '@/components/invoices/ExcelStagingGrid';

export default function ExcelStagingSessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.sessionId as string;

  const { loadSession, currentSession, clearSession } = useExcelStaging();

  useEffect(() => {
    if (!sessionId) return;

    const load = async () => {
      try {
        await loadSession(sessionId);
      } catch {
        // Session not found or expired — redirect to upload
        router.push('/invoices/history');
      }
    };

    load();
  }, [sessionId, loadSession, router]);

  const handleBackToUpload = () => {
    clearSession();
    router.push('/invoices/history');
  };

  if (!currentSession) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#202223] dark:text-[#e3e3e3]">
            Staging: {currentSession.original_filename}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {currentSession.total_rows} rows · {currentSession.valid_rows} valid · {currentSession.errored_rows} with errors
          </p>
        </div>
      </div>
      <ExcelStagingGrid onBackToUpload={handleBackToUpload} />
    </div>
  );
}
