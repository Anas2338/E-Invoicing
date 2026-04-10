import * as React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, type, ...props }: InputProps) {
  return (
    <input
      type={type}
      className={`flex h-12 w-full rounded-xl border-2 border-[#c9cccf] bg-white px-4 py-3 text-base text-[#202223] placeholder:text-[#8c9196] shadow-sm transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[#008060] focus:border-[#008060] disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#2e2e2e] dark:bg-[#1a1a1a] dark:text-[#e3e3e3] dark:placeholder:text-[#6d7175] dark:focus:ring-[#00a876] dark:focus:border-[#00a876] ${className}`}
      {...props}
    />
  );
}
