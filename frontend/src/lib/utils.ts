import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format currency for display
export function formatCurrency(amount: number, currency: string = 'PKR'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

// Format date for display
export function formatDate(dateString: string, locale: string = 'en-US'): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Debounce function for search and other input optimizations
export function debounce<T extends (...args: any[]) => any>(func: T, wait: number) {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>): void => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Check if the environment is client-side (browser)
export function isClientSide(): boolean {
  return typeof window !== 'undefined';
}

// Safely access localStorage
export function safeLocalStorage(): Storage | null {
  if (isClientSide()) {
    try {
      return window.localStorage;
    } catch (e) {
      return null;
    }
  }
  return null;
}

// Encrypt data for storage (simple obfuscation - not for sensitive data)
export function encryptForStorage(data: any): string {
  return btoa(unescape(encodeURIComponent(JSON.stringify(data))));
}

// Decrypt data from storage
export function decryptFromStorage(encryptedData: string): any {
  try {
    return JSON.parse(decodeURIComponent(escape(atob(encryptedData))));
  } catch (e) {
    console.error('Error decrypting data:', e);
    return null;
  }
}