import * as React from 'react';

interface SelectProps {
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
}

interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

interface SelectContentProps {
  children: React.ReactNode;
}

interface SelectItemProps extends React.LiHTMLAttributes<HTMLLIElement> {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
}

interface SelectValueProps {
  placeholder?: string;
}

const SelectContext = React.createContext<{
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
} | null>(null);

export function Select({ children, value = '', onValueChange }: SelectProps) {
  const [open, setOpen] = React.useState(false);
  const selectRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open]);

  const contextValue = {
    value,
    onValueChange: onValueChange || (() => {}),
    open,
    setOpen,
  };

  return (
    <SelectContext.Provider value={contextValue}>
      <div ref={selectRef} className="relative">{children}</div>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({ className, children, ...props }: SelectTriggerProps) {
  const context = React.useContext(SelectContext);

  const handleClick = () => {
    if (context) {
      context.setOpen(!context.open);
    }
  };

  return (
    <button
      type="button"
      className={`flex h-12 w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-4 py-2 text-base text-gray-900 shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 ${className || ''}`}
      onClick={handleClick}
      {...props}
    >
      {children}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`h-4 w-4 opacity-50 transition-transform ${context?.open ? 'rotate-180' : ''}`}
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </button>
  );
}

export function SelectContent({ children }: SelectContentProps) {
  const context = React.useContext(SelectContext);

  if (!context?.open) {
    return null;
  }

  return (
    <div className="absolute z-50 min-w-[8rem] overflow-hidden rounded-md border bg-white text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95 mt-1 w-full max-h-60 overflow-y-auto">
      <ul className="p-1">
        {children}
      </ul>
    </div>
  );
}

export function SelectItem({ value, children, disabled, className, onClick, ...props }: SelectItemProps) {
  const context = React.useContext(SelectContext);

  const handleClick = (e: React.MouseEvent<HTMLLIElement>) => {
    if (disabled) return;

    if (context) {
      context.onValueChange(value);
      context.setOpen(false); // Close dropdown after selection
    }

    if (onClick) {
      onClick(e);
    }
  };

  return (
    <li
      className={`relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-gray-100 focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50 ${className || ''}`}
      onClick={handleClick}
      {...props}
    >
      <span className={`absolute left-2 flex h-3.5 w-3.5 items-center justify-center ${disabled ? 'opacity-50' : ''}`}>
        {context?.value === value && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        )}
      </span>
      {children}
    </li>
  );
}

export function SelectValue({ placeholder }: SelectValueProps) {
  const context = React.useContext(SelectContext);

  if (!context) {
    return null;
  }

  return <>{context.value || placeholder}</>;
}