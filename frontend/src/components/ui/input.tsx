import * as React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, type, ...props }: InputProps) {
  return (
    <input
      type={type}
      className={`flex rounded-xl border-2 border-[#c9cccf] bg-white px-4 py-3 text-[#202223] shadow-sm transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[#008060] focus:border-[#008060] disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
