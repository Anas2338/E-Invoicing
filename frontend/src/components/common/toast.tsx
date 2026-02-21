import { useState, useEffect } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

// Define toast variants
const toastVariants = cva(
  'fixed top-4 right-4 z-50 w-full max-w-sm overflow-hidden rounded-md border p-4 shadow-lg transition-all data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full',
  {
    variants: {
      variant: {
        default: 'border bg-background text-foreground',
        destructive:
          'destructive group border-destructive bg-destructive text-destructive-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface ToastProps extends VariantProps<typeof toastVariants> {
  title?: string;
  description?: string;
  duration?: number;
  onClose?: () => void;
}

// Toast component
export function Toast({ title, description, variant, duration = 5000, onClose }: ToastProps) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setOpen(false);
        if (onClose) onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  if (!open) return null;

  return (
    <div className={cn(toastVariants({ variant }))}>
      <div className="grid gap-1">
        {title && <div className="text-sm font-semibold">{title}</div>}
        {description && <div className="text-sm opacity-90">{description}</div>}
      </div>
      <button
        onClick={() => {
          setOpen(false);
          if (onClose) onClose();
        }}
        className="absolute top-2 right-2 rounded-md p-1 opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label="Close"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
        >
          <path d="M18 6L6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

// Toast Provider to manage multiple toasts
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Array<{ id: string; props: ToastProps }>>([]);

  const addToast = (props: ToastProps) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, props }]);

    // Auto-remove toast after duration
    if (props.duration !== Infinity) {
      setTimeout(() => {
        removeToast(id);
      }, props.duration || 5000);
    }
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  // Expose addToast function via context or return it
  return (
    <div>
      {children}
      <div className="fixed top-4 right-4 z-[100] space-y-2">
        {toasts.map(({ id, props }) => (
          <Toast
            key={id}
            {...props}
            onClose={() => removeToast(id)}
          />
        ))}
      </div>
    </div>
  );
}

// Hook to use toast functionality
export function useToast() {
  // In a real implementation, this would use context
  // For now, we'll return a simple function to add toasts
  const addToast = (props: ToastProps) => {
    // This would interact with the ToastProvider context in a real app
  };

  return { addToast };
}