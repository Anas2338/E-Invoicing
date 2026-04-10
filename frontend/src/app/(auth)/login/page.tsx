'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { LoginForm } from '@/components/auth/login-form';
import FeatureHighlights from '@/components/auth/feature-highlights';
import { Lock, Frown } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { signIn, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (email: string, password: string) => {
    try {
      setError(null);
      await signIn(email, password);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f6f6f7] via-white to-[#f1f8f5] dark:from-[#0a0a0a] dark:via-[#1a1a1a] dark:to-[#0d3d2f]/20 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-7xl w-full">
        <div className="grid lg:grid-cols-[3fr_2fr] gap-8 items-start">
          {/* Feature Highlights - Hidden on mobile, shown on desktop */}
          <div className="hidden lg:block">
            <FeatureHighlights />
          </div>

          {/* Login Form */}
          <div className="w-full space-y-8">
            <div className="bg-white dark:bg-[#1a1a1a] py-8 px-6 shadow-lg rounded-2xl sm:px-10 border border-[#e1e3e5] dark:border-[#2e2e2e] transition-all duration-150 hover:shadow-xl">
              <div className="text-center mb-8">
                <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-xl bg-[#f1f8f5] dark:bg-[#0d3d2f]/30">
                  <Lock className="h-7 w-7 text-[#008060] dark:text-[#00a876]" />
                </div>
                <h2 className="mt-6 text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">
                  Welcome Back
                </h2>
                <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
                  Sign in to your account to continue
                </p>
              </div>

              <LoginForm onSubmit={handleSubmit} disabled={loading} error={error} />

              <div className="mt-6 text-center">
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                  Don't have an account?{' '}
                  <Link
                    href="/register"
                    className="font-semibold text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] transition-colors duration-150"
                  >
                    Sign up
                  </Link>
                </p>
              </div>

              {error && (
                <div className="mt-4 flex items-center p-3 bg-[#fef3f2] dark:bg-[#3d1e1e] rounded-xl border border-[#fecdca] dark:border-[#5c2b2b]">
                  <Frown className="h-4 w-4 text-[#d72c0d] dark:text-[#ff6f59] mr-2" />
                  <span className="text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</span>
                </div>
              )}
            </div>

            <div className="text-center text-xs text-[#6d7175] dark:text-[#8c9196]">
              <p>Secured with enterprise-grade encryption</p>
            </div>
          </div>

          {/* Feature Highlights - Shown on mobile below login form */}
          <div className="lg:hidden">
            <FeatureHighlights />
          </div>
        </div>
      </div>
    </div>
  );
}