'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'react-toastify';
import { Eye, EyeOff } from 'lucide-react';

const API_BASE_URL = '/api/v1';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [pin, setPin] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step, setStep] = useState<'verify' | 'reset'>('verify');
  const router = useRouter();

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Validate PIN format
    if (!/^\d{4,6}$/.test(pin)) {
      toast.error('PIN must be 4-6 digits');
      setIsSubmitting(false);
      return;
    }

    try {
      // Call backend to verify email and PIN
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/verify-pin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          pin,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Verification successful - move to password reset step
        toast.success('Credentials verified! Please enter your new password.');
        setStep('reset');
      } else {
        // Verification failed - show error
        toast.error(data.detail || 'Invalid email or PIN');
      }
    } catch (error) {
      console.error('Error verifying credentials:', error);
      toast.error('Failed to verify credentials. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      setIsSubmitting(false);
      return;
    }

    // Validate password strength
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      setIsSubmitting(false);
      return;
    }

    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(newPassword)) {
      toast.error('Password must contain uppercase, lowercase, number, and special character');
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/with-pin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          pin,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success('Password reset successful! You can now login with your new password.');
        router.push('/login');
      } else {
        toast.error(data.detail || 'Failed to reset password');
      }
    } catch (error) {
      console.error('Error resetting password:', error);
      toast.error('Failed to reset password. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f6f6f7] via-white to-[#f1f8f5] dark:from-[#0a0a0a] dark:via-[#1a1a1a] dark:to-[#0d3d2f]/20 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Reset Password</CardTitle>
          <CardDescription>
            {step === 'verify'
              ? 'Enter your email address and recovery PIN to verify your identity.'
              : 'Enter your new password.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {step === 'verify' ? (
            <form onSubmit={handleVerify} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="pin">Recovery PIN</Label>
                <Input
                  id="pin"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="Enter your 4-6 digit PIN"
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
                  required
                  disabled={isSubmitting}
                />
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                  Enter the PIN you set during registration
                </p>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Verifying...' : 'Continue'}
              </Button>

              <div className="text-center">
                <Link
                  href="/login"
                  className="text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold"
                >
                  Back to Login
                </Link>
              </div>
            </form>
          ) : (
            <form onSubmit={handleReset} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-password">New Password</Label>
                <div className="relative">
                  <Input
                    id="new-password"
                    type={showNewPassword ? "text" : "password"}
                    placeholder="Enter new password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    disabled={isSubmitting}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    disabled={isSubmitting}
                  >
                    {showNewPassword ? (
                      <EyeOff className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196]" />
                    ) : (
                      <Eye className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196]" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                  Must be at least 8 characters with uppercase, lowercase, number, and special character
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm New Password</Label>
                <div className="relative">
                  <Input
                    id="confirm-password"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={isSubmitting}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    disabled={isSubmitting}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196]" />
                    ) : (
                      <Eye className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196]" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={() => setStep('verify')}
                  disabled={isSubmitting}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Resetting...' : 'Reset Password'}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
