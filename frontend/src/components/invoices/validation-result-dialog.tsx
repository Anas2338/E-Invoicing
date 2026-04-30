'use client';

import { Button } from '@/components/ui/button';
import { X, CheckCircle, AlertCircle } from 'lucide-react';

interface ValidationError {
  itemSNo: string;
  statusCode: string;
  status: string;
  errorCode: string;
  error: string;
}

interface ValidationResultDialogProps {
  isOpen: boolean;
  onClose: () => void;
  success: boolean;
  title: string;
  message: string;
  invoiceNumber?: string;
  fbrNumber?: string;
  errors?: ValidationError[];
  onRetry?: () => void;
  invoiceId?: string;
}

export function ValidationResultDialog({
  isOpen,
  onClose,
  success,
  title,
  message,
  invoiceNumber,
  fbrNumber,
  errors = [],
  onRetry,
  invoiceId
}: ValidationResultDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col border border-[#e1e3e5] dark:border-[#2e2e2e]">
        {/* Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          success ? 'bg-[#d1fae5] dark:bg-[#064e3b]/30 border-[#a7f3d0] dark:border-[#065f46]' : 'bg-[#fef3f2] dark:bg-[#3d1e1e] border-[#fecdca] dark:border-[#5c2b2b]'
        }`}>
          <div className="flex items-center gap-3">
            {success ? (
              <CheckCircle className="h-6 w-6 text-[#065f46] dark:text-[#34d399]" />
            ) : (
              <AlertCircle className="h-6 w-6 text-[#d72c0d] dark:text-[#ff6f59]" />
            )}
            <h2 className={`text-xl font-bold ${
              success ? 'text-[#065f46] dark:text-[#34d399]' : 'text-[#d72c0d] dark:text-[#ff6f59]'
            }`}>
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-[#8c9196] dark:text-[#6d7175] hover:text-[#6d7175] dark:hover:text-[#8c9196] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* Invoice Details */}
          {invoiceNumber && (
            <div className="mb-4">
              <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">Invoice Number</div>
              <div className="text-lg font-semibold text-[#202223] dark:text-[#e3e3e3]">{invoiceNumber}</div>
            </div>
          )}

          {/* FBR Number (for successful posting) */}
          {fbrNumber && (
            <div className="mb-4 p-3 bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl">
              <div className="text-sm text-[#065f46] dark:text-[#34d399] font-semibold">FBR Invoice Number</div>
              <div className="text-lg font-bold text-[#065f46] dark:text-[#34d399] font-mono">{fbrNumber}</div>
            </div>
          )}

          {/* Message */}
          <div className="mb-4">
            <p className={`text-sm ${success ? 'text-[#065f46] dark:text-[#34d399]' : 'text-[#d72c0d] dark:text-[#ff6f59]'}`}>
              {message}
            </p>
          </div>

          {/* Validation Errors */}
          {!success && errors.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
                Validation Errors ({errors.length})
              </h3>
              <div className="space-y-2">
                {errors.map((error, index) => (
                  <div
                    key={index}
                    className="p-3 bg-[#fef3f2] dark:bg-[#3d1e1e] border border-[#fecdca] dark:border-[#5c2b2b] rounded-xl"
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 mt-0.5">
                        <AlertCircle className="h-4 w-4 text-[#d72c0d] dark:text-[#ff6f59]" />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-semibold text-[#d72c0d] dark:text-[#ff6f59]">
                          Item {error.itemSNo || index + 1}
                        </div>
                        <div className="text-sm text-[#d72c0d] dark:text-[#ff6f59] mt-1">
                          {error.error || 'Unknown error'}
                        </div>
                        {error.errorCode && (
                          <div className="text-xs text-[#d72c0d] dark:text-[#ff6f59] mt-1">
                            Error Code: {error.errorCode}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Success Message */}
          {success && !title.includes('Delete') && (
            <div className="mt-4 p-4 bg-[#d1fae5] dark:bg-[#064e3b]/30 border border-[#a7f3d0] dark:border-[#065f46] rounded-xl">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-[#065f46] dark:text-[#34d399] flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-[#065f46] dark:text-[#34d399]">
                    {title === 'Validation Successful'
                      ? 'Your invoice has been validated successfully and is ready to be posted to FBR.'
                      : 'Your invoice has been successfully submitted to the Federal Board of Revenue.'}
                  </div>
                  {fbrNumber && (
                    <div className="text-xs text-[#065f46] dark:text-[#34d399] mt-2">
                      Please save the FBR invoice number for your records.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e] bg-[#f6f6f7] dark:bg-[#2e2e2e] flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
          {!success && title === 'Validation Failed' && onRetry && invoiceId && (
            <Button
              onClick={() => {
                onClose();
                onRetry();
              }}
              className="bg-[#008060] hover:bg-[#006e52] text-white"
            >
              Retry Validation
            </Button>
          )}
          {success && title === 'Validation Successful' && (
            <Button
              onClick={onClose}
            >
              Continue to Post
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
