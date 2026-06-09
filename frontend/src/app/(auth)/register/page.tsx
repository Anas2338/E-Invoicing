'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { RegisterForm } from '@/components/auth/register-form';
import { UserPlus, Frown, CheckCircle } from 'lucide-react';

export default function RegisterPage() {
  const router = useRouter();
  const { user, loading: authLoading, signUp, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState(false);
  const [authorized, setAuthorized] = useState(false);

  // Only allow authenticated admin users to access the register page
  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      router.push('/login');
      return;
    }

    if (user.role !== 'admin') {
      router.push('/dashboard');
      return;
    }

    setAuthorized(true);
  }, [user, authLoading, router]);

  // Show loading while checking auth
  if (authLoading || !authorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f6f6f7] via-white to-[#f1f8f5] dark:from-[#0a0a0a] dark:via-[#1a1a1a] dark:to-[#0d3d2f]/20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008060] dark:border-[#00a876] mx-auto"></div>
          <p className="mt-4 text-[#6d7175] dark:text-[#8c9196]">Loading...</p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (email: string, password: string, name: string) => {
    try {
      setError(null);
      setSuccess(null);
      const result = await signUp(email, password, name);

      // Check if registration requires approval
      if (result && result.status === 'pending_approval') {
        setPendingApproval(true);
        setSuccess(result.message || 'Registration successful! Your account is pending admin approval.');
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    }
  };

  if (pendingApproval) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f6f6f7] via-white to-[#f1f8f5] dark:from-[#0a0a0a] dark:via-[#1a1a1a] dark:to-[#0d3d2f]/20 px-4 py-12 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="bg-white dark:bg-[#1a1a1a] py-8 px-6 shadow-lg rounded-2xl sm:px-10 border border-[#e1e3e5] dark:border-[#2e2e2e]">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-xl bg-[#d1fae5] dark:bg-[#064e3b]/30">
                <CheckCircle className="h-7 w-7 text-[#065f46] dark:text-[#34d399]" />
              </div>
              <h2 className="mt-6 text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">
                Registration Successful!
              </h2>
              <p className="mt-4 text-sm text-[#6d7175] dark:text-[#8c9196]">
                {success}
              </p>
              <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
                You will receive an email notification once your account is approved by an administrator.
              </p>
              <div className="mt-8">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center w-full px-4 py-2 border border-transparent rounded-xl shadow-sm text-sm font-semibold text-white bg-[#008060] hover:bg-[#006e52] dark:bg-[#00a876] dark:hover:bg-[#008f64] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876] transition-all duration-150"
                >
                  Back to Login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f6f6f7] via-white to-[#f1f8f5] dark:from-[#0a0a0a] dark:via-[#1a1a1a] dark:to-[#0d3d2f]/20 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white dark:bg-[#1a1a1a] py-8 px-6 shadow-lg rounded-2xl sm:px-10 border border-[#e1e3e5] dark:border-[#2e2e2e] transition-all duration-150 hover:shadow-xl">
          <div className="text-center mb-8">
            <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-xl bg-[#f1f8f5] dark:bg-[#0d3d2f]/30">
              <UserPlus className="h-7 w-7 text-[#008060] dark:text-[#00a876]" />
            </div>
            <h2 className="mt-6 text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">
              Create Account
            </h2>
            <p className="mt-2 text-sm text-[#6d7175] dark:text-[#8c9196]">
              Join us today to get started
            </p>
          </div>

          <RegisterForm onSubmit={handleSubmit} disabled={loading} error={error} />

          {error && (
            <div className="mt-4 flex items-center p-3 bg-[#fef3f2] dark:bg-[#3d1e1e] rounded-xl border border-[#fecdca] dark:border-[#5c2b2b]">
              <Frown className="h-4 w-4 text-[#d72c0d] dark:text-[#ff6f59] mr-2" />
              <span className="text-sm text-[#d72c0d] dark:text-[#ff6f59]">{error}</span>
            </div>
          )}
        </div>

        <div className="text-center text-xs text-[#6d7175] dark:text-[#8c9196]">
          <p>Join thousands of satisfied customers</p>
        </div>
      </div>
    </div>
  );
}