import * as React from 'react';

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, ...props }: LabelProps) {
  return (
    <label
      className={`block text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2 ${className}`}
      {...props}
    />
  );
}
