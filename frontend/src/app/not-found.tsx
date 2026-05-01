'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Home, ArrowLeft, FileQuestion } from 'lucide-react';

export default function NotFound() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full text-center">
        <div className="bg-white dark:bg-[#1a1a1a] py-12 px-6 shadow-xl rounded-2xl sm:px-12 border border-gray-200 dark:border-[#2e2e2e]">
          {/* Icon */}
          <div className="mx-auto flex items-center justify-center h-24 w-24 rounded-full bg-indigo-100 dark:bg-indigo-900/30 mb-8">
            <FileQuestion className="h-12 w-12 text-indigo-600 dark:text-indigo-400" />
          </div>

          {/* 404 Text */}
          <h1 className="text-9xl font-extrabold text-indigo-600 dark:text-indigo-400 mb-4">404</h1>

          {/* Error Message */}
          <h2 className="text-3xl font-bold text-gray-900 dark:text-[#e3e3e3] mb-4">
            Page Not Found
          </h2>
          <p className="text-lg text-gray-600 dark:text-[#8c9196] mb-8 max-w-md mx-auto">
            Sorry, we couldn't find the page you're looking for. The page might have been moved, deleted, or never existed.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button
              onClick={() => router.back()}
              variant="outline"
              className="w-full sm:w-auto px-6 py-3 text-base font-medium border-gray-300 dark:border-[#2e2e2e] text-gray-700 dark:text-[#e3e3e3] hover:bg-gray-50 dark:hover:bg-[#2e2e2e]"
            >
              <ArrowLeft className="h-5 w-5 mr-2" />
              Go Back
            </Button>
            <Link href="/dashboard" className="w-full sm:w-auto">
              <Button className="w-full px-6 py-3 text-base font-medium bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white">
                <Home className="h-5 w-5 mr-2" />
                Go to Dashboard
              </Button>
            </Link>
          </div>

          {/* Additional Help */}
          <div className="mt-8 pt-8 border-t border-gray-200 dark:border-[#2e2e2e]">
            <p className="text-sm text-gray-500 dark:text-[#8c9196]">
              Need help? Contact support or visit our{' '}
              <Link href="/dashboard" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-medium">
                help center
              </Link>
            </p>
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-400 dark:text-gray-600">
            Error Code: 404 | Page Not Found
          </p>
        </div>
      </div>
    </div>
  );
}
