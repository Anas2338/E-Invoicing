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
  className?: string;
}

interface SelectItemProps extends React.LiHTMLAttributes<HTMLLIElement> {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
  /** @internal - set by SelectContent */
  index?: number;
  /** @internal - set by SelectContent */
  isHighlighted?: boolean;
}

interface SelectValueProps {
  placeholder?: string;
}

interface SelectContextType {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  highlightedIndex: number;
  setHighlightedIndex: (index: number) => void;
  itemsRef: React.MutableRefObject<Array<{ value: string; disabled: boolean }>>;
}

const SelectContext = React.createContext<SelectContextType | null>(null);

/** Find the next non-disabled index (wraps around) */
function findNextIndex(
  current: number,
  direction: 'down' | 'up',
  items: Array<{ value: string; disabled: boolean }>
): number {
  const len = items.length;
  if (len === 0) return -1;

  if (direction === 'down') {
    for (let i = 1; i <= len; i++) {
      const idx = (current + i) % len;
      if (!items[idx]?.disabled) return idx;
    }
  } else {
    for (let i = 1; i <= len; i++) {
      const idx = (current - i + len) % len;
      if (!items[idx]?.disabled) return idx;
    }
  }
  return -1; // all items are disabled
}

export function Select({ children, value = '', onValueChange }: SelectProps) {
  const [open, setOpen] = React.useState(false);
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);
  const itemsRef = React.useRef<Array<{ value: string; disabled: boolean }>>([]);
  const selectRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setOpen(false);
        setHighlightedIndex(-1);
      }
    };

    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open]);

  // Close on Escape (global listener so it works even when focus is on the trigger button)
  React.useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const contextValue: SelectContextType = {
    value,
    onValueChange: onValueChange || (() => {}),
    open,
    setOpen,
    highlightedIndex,
    setHighlightedIndex,
    itemsRef,
  };

  return (
    <SelectContext.Provider value={contextValue}>
      <div ref={selectRef} className="relative">{children}</div>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({ className, children, onKeyDown, ...props }: SelectTriggerProps) {
  const context = React.useContext(SelectContext);

  const handleClick = () => {
    if (context) {
      if (context.open) {
        context.setOpen(false);
        context.setHighlightedIndex(-1);
      } else {
        context.setOpen(true);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (!context) return;

    const items = context.itemsRef.current;

    if (context.open) {
      // Dropdown is OPEN — navigate items
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = findNextIndex(
          context.highlightedIndex === -1 ? -1 : context.highlightedIndex,
          'down',
          items
        );
        if (next !== -1) context.setHighlightedIndex(next);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const next = findNextIndex(
          context.highlightedIndex === -1 ? items.length : context.highlightedIndex,
          'up',
          items
        );
        if (next !== -1) context.setHighlightedIndex(next);
      } else if (e.key === 'Home') {
        e.preventDefault();
        const first = findNextIndex(-1, 'down', items);
        if (first !== -1) context.setHighlightedIndex(first);
      } else if (e.key === 'End') {
        e.preventDefault();
        const last = findNextIndex(items.length, 'up', items);
        if (last !== -1) context.setHighlightedIndex(last);
      } else if (e.key === 'Enter') {
        if (context.highlightedIndex >= 0 && context.highlightedIndex < items.length) {
          e.preventDefault();
          const item = items[context.highlightedIndex];
          if (item && !item.disabled) {
            context.onValueChange(item.value);
            context.setOpen(false);
            context.setHighlightedIndex(-1);
          }
        } else {
          // No item highlighted — close the dropdown
          e.preventDefault();
          context.setOpen(false);
          context.setHighlightedIndex(-1);
        }
      } else if (e.key === ' ') {
        // Space: select highlighted item if any
        if (context.highlightedIndex >= 0 && context.highlightedIndex < items.length) {
          e.preventDefault();
          const item = items[context.highlightedIndex];
          if (item && !item.disabled) {
            context.onValueChange(item.value);
            context.setOpen(false);
            context.setHighlightedIndex(-1);
          }
        }
        // Otherwise let the button's native click behavior handle toggle
      }
    } else {
      // Dropdown is CLOSED — open on arrow keys
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        context.setOpen(true);
        const first = findNextIndex(-1, 'down', items);
        if (first !== -1) context.setHighlightedIndex(first);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        context.setOpen(true);
        const last = findNextIndex(items.length, 'up', items);
        if (last !== -1) context.setHighlightedIndex(last);
      }
    }

    // Call user-provided onKeyDown if any
    if (onKeyDown) {
      onKeyDown(e);
    }
  };

  return (
    <button
      type="button"
      className={`flex h-7 w-full items-center justify-between rounded-lg border border-[#c9cccf] bg-white px-3 py-2 text-[12px] text-[#202223] shadow-sm transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#008060] focus-visible:border-[#008060] disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#2e2e2e] dark:bg-[#1a1a1a] dark:text-[#e3e3e3] dark:focus-visible:ring-[#00a876] dark:focus-visible:border-[#00a876] ${className || ''}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-haspopup="listbox"
      aria-expanded={context?.open}
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

export function SelectContent({ children, className }: SelectContentProps) {
  const context = React.useContext(SelectContext);

  if (!context?.open) {
    return null;
  }

  // Map children to inject index + highlight state
  const childrenArray = React.Children.toArray(children);

  // Update itemsRef so trigger keyboard handler knows about current items
  context.itemsRef.current = childrenArray.map((child: any) => ({
    value: child?.props?.value || '',
    disabled: child?.props?.disabled || false,
  }));

  return (
    <div
      className={`absolute z-50 min-w-[8rem] overflow-hidden rounded-xl border-2 border-[#e1e3e5] bg-white text-[#202223] shadow-lg animate-in fade-in-0 zoom-in-95 mt-1 w-full max-h-60 overflow-y-auto dark:bg-[#1a1a1a] dark:border-[#2e2e2e] dark:text-[#e3e3e3] ${className || ''}`}
      role="listbox"
    >
      <ul className="p-1">
        {childrenArray.map((child: any, index: number) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child as React.ReactElement<any>, {
              index,
              isHighlighted: context.highlightedIndex === index,
            });
          }
          return child;
        })}
      </ul>
    </div>
  );
}

export function SelectItem({
  value,
  children,
  disabled,
  className,
  onClick,
  index,
  isHighlighted,
  ...props
}: SelectItemProps) {
  const context = React.useContext(SelectContext);
  const itemRef = React.useRef<HTMLLIElement>(null);

  // Scroll into view when keyboard-highlighted
  React.useEffect(() => {
    if (isHighlighted && itemRef.current) {
      itemRef.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isHighlighted]);

  const handleClick = (e: React.MouseEvent<HTMLLIElement>) => {
    if (disabled) return;

    if (context) {
      context.onValueChange(value);
      context.setOpen(false);
      context.setHighlightedIndex(-1);
    }

    if (onClick) {
      onClick(e);
    }
  };

  return (
    <li
      ref={itemRef}
      role="option"
      aria-selected={context?.value === value}
      aria-disabled={disabled}
      data-highlighted={isHighlighted ? '' : undefined}
      data-disabled={disabled ? '' : undefined}
      className={`relative flex w-full cursor-pointer select-none items-center rounded-lg py-2 pl-8 pr-2 text-sm outline-none hover:bg-[#f6f6f7] data-[highlighted]:bg-[#f6f6f7] data-[disabled]:pointer-events-none data-[disabled]:opacity-50 dark:hover:bg-[#2e2e2e] dark:data-[highlighted]:bg-[#2e2e2e] ${className || ''}`}
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
