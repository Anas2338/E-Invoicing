import * as React from 'react';

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

export function Checkbox({ checked, onCheckedChange, className, ...props }: CheckboxProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onCheckedChange) {
      onCheckedChange(e.target.checked);
    }
    if (props.onChange) {
      props.onChange(e);
    }
  };

  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={handleChange}
      className={`h-5 w-5 rounded-md border-2 border-[#c9cccf] text-[#008060] transition-colors focus:ring-2 focus:ring-[#008060] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#2e2e2e] dark:bg-[#1a1a1a] dark:text-[#00a876] dark:focus:ring-[#00a876] ${className}`}
      {...props}
    />
  );
}
