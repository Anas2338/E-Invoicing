import * as React from 'react';

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, ...props }: LabelProps) {
  return (
    <label
      className={`block text-sm font-medium text-gray-700 mb-2 ${className}`}
      {...props}
    />
  );
}