'use client';

import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Navigation } from '@/components/navigation';
import { UploadSessionProvider } from '@/contexts/UploadSessionContext';
import { ValidationProgressWidget } from '@/components/automation/ValidationProgressWidget';

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f5f5f4] dark:bg-[#0a0a0a]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 dark:border-indigo-400 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <UploadSessionProvider>
      <div className="h-screen overflow-y-auto bg-[#f5f5f4] dark:bg-[#0a0a0a] flex flex-col">
        <Navigation />
        <div className="flex-1 min-h-0 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-1">
          {children}
        </div>
        <ValidationProgressWidget />
      </div>
    </UploadSessionProvider>
  );
}