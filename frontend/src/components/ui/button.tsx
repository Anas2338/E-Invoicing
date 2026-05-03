import * as React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export function Button({ className, variant = 'default', size = 'default', ...props }: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] whitespace-nowrap';

  const variantClasses = {
    default: 'bg-[#008060] text-white hover:bg-[#006e52] focus:ring-[#008060] shadow-sm hover:shadow-md dark:bg-[#00a876] dark:hover:bg-[#008f64]',
    destructive: 'bg-[#d72c0d] text-white hover:bg-[#bf2711] focus:ring-[#d72c0d] shadow-sm hover:shadow-md dark:bg-[#e0301e] dark:hover:bg-[#c72912]',
    outline: 'border-2 border-[#c9cccf] bg-white text-[#202223] hover:bg-[#f6f6f7] hover:border-[#8c9196] focus:ring-[#008060] dark:border-[#2e2e2e] dark:bg-transparent dark:text-[#e3e3e3] dark:hover:bg-[#1a1a1a] dark:hover:border-[#404040]',
    secondary: 'bg-[#f6f6f7] text-[#202223] hover:bg-[#e4e5e7] focus:ring-[#8c9196] dark:bg-[#2e2e2e] dark:text-[#e3e3e3] dark:hover:bg-[#404040]',
    ghost: 'text-[#202223] hover:bg-[#f6f6f7] hover:text-[#202223] focus:ring-[#8c9196] dark:text-[#e3e3e3] dark:hover:bg-[#2e2e2e] dark:hover:text-[#e3e3e3]',
    link: 'text-[#008060] underline-offset-4 hover:underline dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64]',
  };

  const sizeClasses = {
    default: 'h-12 px-6 py-3 text-base',
    sm: 'h-10 px-4 py-2 text-sm',
    lg: 'h-14 px-8 py-4 text-lg',
    icon: 'h-12 w-12',
  };

  return (
    <button
      type="button"
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    />
  );
}
