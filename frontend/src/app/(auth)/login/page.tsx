'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { LoginForm } from '@/components/auth/login-form';
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white py-8 px-6 shadow-xl rounded-2xl sm:rounded-2xl sm:px-10 transition-all duration-300 hover:shadow-2xl">
          <div className="text-center mb-8">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-indigo-100">
              <Lock className="h-6 w-6 text-indigo-600" />
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Welcome Back
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Sign in to your account to continue
            </p>
          </div>

          <LoginForm onSubmit={handleSubmit} disabled={loading} error={error} />

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link
                href="/register"
                className="font-medium text-indigo-600 hover:text-indigo-500 transition-colors duration-200"
              >
                Sign up
              </Link>
            </p>
          </div>

          {error && (
            <div className="mt-4 flex items-center p-3 bg-red-50 rounded-lg border border-red-100">
              <Frown className="h-4 w-4 text-red-500 mr-2" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}
        </div>

        <div className="text-center text-xs text-gray-500">
          <p>Secured with enterprise-grade encryption</p>
        </div>
      </div>
    </div>
  );
}