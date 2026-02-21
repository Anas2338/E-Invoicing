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
}

export function ValidationResultDialog({
  isOpen,
  onClose,
  success,
  title,
  message,
  invoiceNumber,
  fbrNumber,
  errors = []
}: ValidationResultDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          success ? 'bg-green-50' : 'bg-red-50'
        }`}>
          <div className="flex items-center gap-3">
            {success ? (
              <CheckCircle className="h-6 w-6 text-green-600" />
            ) : (
              <AlertCircle className="h-6 w-6 text-red-600" />
            )}
            <h2 className={`text-xl font-semibold ${
              success ? 'text-green-900' : 'text-red-900'
            }`}>
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* Invoice Details */}
          {invoiceNumber && (
            <div className="mb-4">
              <div className="text-sm text-gray-600">Invoice Number</div>
              <div className="text-lg font-medium text-gray-900">{invoiceNumber}</div>
            </div>
          )}

          {/* FBR Number (for successful posting) */}
          {fbrNumber && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="text-sm text-green-700 font-medium">FBR Invoice Number</div>
              <div className="text-lg font-bold text-green-900 font-mono">{fbrNumber}</div>
            </div>
          )}

          {/* Message */}
          <div className="mb-4">
            <p className={`text-sm ${success ? 'text-green-700' : 'text-red-700'}`}>
              {message}
            </p>
          </div>

          {/* Validation Errors */}
          {!success && errors.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Validation Errors ({errors.length})
              </h3>
              <div className="space-y-2">
                {errors.map((error, index) => (
                  <div
                    key={index}
                    className="p-3 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 mt-0.5">
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-red-900">
                          Item {error.itemSNo || index + 1}
                        </div>
                        <div className="text-sm text-red-700 mt-1">
                          {error.error || 'Unknown error'}
                        </div>
                        {error.errorCode && (
                          <div className="text-xs text-red-600 mt-1">
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
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-green-900">
                    {title === 'Validation Successful'
                      ? 'Your invoice has been validated successfully and is ready to be posted to FBR.'
                      : 'Your invoice has been successfully submitted to the Federal Board of Revenue.'}
                  </div>
                  {fbrNumber && (
                    <div className="text-xs text-green-700 mt-2">
                      Please save the FBR invoice number for your records.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
          {success && title === 'Validation Successful' && (
            <Button
              onClick={onClose}
              className="bg-green-600 hover:bg-green-700"
            >
              Continue to Post
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
