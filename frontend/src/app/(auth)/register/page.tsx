'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { RegisterForm } from '@/components/auth/register-form';
import { UserPlus, Frown } from 'lucide-react';

export default function RegisterPage() {
  const router = useRouter();
  const { signUp, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (email: string, password: string, name: string) => {
    try {
      setError(null);
      await signUp(email, password, name);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white py-8 px-6 shadow-xl rounded-2xl sm:rounded-2xl sm:px-10 transition-all duration-300 hover:shadow-2xl">
          <div className="text-center mb-8">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
              <UserPlus className="h-6 w-6 text-green-600" />
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Create Account
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Join us today to get started
            </p>
          </div>

          <RegisterForm onSubmit={handleSubmit} disabled={loading} error={error} />

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                href="/login"
                className="font-medium text-indigo-600 hover:text-indigo-500 transition-colors duration-200"
              >
                Sign in
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
          <p>Join thousands of satisfied customers</p>
        </div>
      </div>
    </div>
  );
}