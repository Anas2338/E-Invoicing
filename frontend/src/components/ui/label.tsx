import * as React from 'react';

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, ...props }: LabelProps) {
  return (
    <label
      className={`block pl-3 text-[14px] font-bold text-[#202223] ${className}`}
      {...props}
    />
  );
}
