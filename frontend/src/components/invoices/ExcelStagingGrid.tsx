'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useExcelStaging } from '@/contexts/ExcelStagingContext';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExcelStagingGridProps {
  /** Called when user wants to go back to upload screen */
  onBackToUpload?: () => void;
  /** Called on successful commit */
  onCommitComplete?: (result: any) => void;
}

// Columns that should show a dropdown (constrained fields)
const DROPDOWN_COLUMNS = new Set([
  'invoice_type',
  'buyer_province',
  'buyer_registration_type',
  'income_tax',
]);

// Dropdown options for constrained fields
const DROPDOWN_OPTIONS: Record<string, string[]> = {
  invoice_type: ['Sale Invoice', 'Debit Note', 'Credit Note'],
  buyer_province: [
    'PUNJAB', 'SINDH', 'KPK', 'BALOCHISTAN',
    'ISLAMABAD', 'GILGIT BALTISTAN', 'AZAD JAMMU KASHMIR',
  ],
  buyer_registration_type: ['Registered', 'Unregistered', 'Final Consumer'],
  income_tax: ['236G', '236H'],
};

// Numeric columns
const NUMERIC_COLUMNS = new Set([
  'quantity', 'value_sales_excluding_st', 'fixed_notified_value_or_retail_price',
  'further_tax', 'discount', 'withholding_tax_amount',
]);

// Column display configuration
interface ColumnDef {
  key: string;
  label: string;
  width?: string;
}

const GRID_COLUMNS: ColumnDef[] = [
  { key: 'excel_row_number', label: '#', width: 'w-8 sm:w-10 lg:w-12' },
  { key: 'invoice_number', label: 'Invoice No', width: 'w-20 sm:w-24 lg:w-28 xl:w-32' },
  { key: 'invoice_type', label: 'Type', width: 'w-20 lg:w-24 xl:w-28' },
  { key: 'invoice_date', label: 'Date', width: 'w-20 sm:w-24 xl:w-28' },
  { key: 'buyer_ntn_cnic', label: 'Buyer NTN/ CNIC', width: 'w-24 lg:w-28 xl:w-32' },
  { key: 'buyer_business_name', label: 'Buyer Name', width: 'min-w-[100px] lg:min-w-0' },
  { key: 'buyer_province', label: 'Province', width: 'w-24 lg:w-36 xl:w-44' },
  { key: 'buyer_address', label: 'Address', width: 'min-w-[100px] lg:min-w-0' },
  { key: 'buyer_registration_type', label: 'Reg Type', width: 'w-20 lg:w-28 xl:w-34' },
  { key: 'saved_item_code', label: 'Item Code', width: 'w-20 lg:w-24 xl:w-28' },
  { key: 'quantity', label: 'Qty', width: 'w-16 lg:w-20 xl:w-24' },
  { key: 'value_sales_excluding_st', label: 'Value Excl ST', width: 'w-24 lg:w-28 xl:w-36' },
  { key: 'fixed_notified_value_or_retail_price', label: 'Retail Price', width: 'w-24 lg:w-28 xl:w-36' },
  { key: 'further_tax', label: 'Further Tax', width: 'w-24 lg:w-28 xl:w-36' },
  { key: 'discount', label: 'Discount', width: 'w-20 lg:w-28 xl:w-34' },
  { key: 'income_tax', label: 'Income Tax', width: 'w-16 lg:w-20 xl:w-24' },
  { key: 'withholding_tax_amount', label: 'WHT', width: 'w-16 lg:w-20 xl:w-24' },
];

// ---------------------------------------------------------------------------
// Editable Cell Component
// ---------------------------------------------------------------------------

function EditableCell({
  value,
  field,
  rowId,
  isError,
  errorMessages,
  onSave,
  isReadOnly,
  width,
}: {
  value: any;
  field: string;
  rowId: string;
  isError: boolean;
  errorMessages: string[];
  onSave: (rowId: string, field: string, value: any) => Promise<void>;
  isReadOnly: boolean;
  width?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const originalValueRef = useRef<string>('');

  const numeric = NUMERIC_COLUMNS.has(field);
  const dropdown = DROPDOWN_COLUMNS.has(field);
  const options = dropdown ? DROPDOWN_OPTIONS[field] || [] : [];

  const displayValue = value ?? '';

  // -----------------------------------------------------------------------
  // Navigation helper — uses DOM traversal to find the next/prev/adjacent cell
  // -----------------------------------------------------------------------
  const navigateToCell = useCallback(
    (fromElement: HTMLElement, key: string, shiftKey: boolean) => {
      const currentTd = fromElement.closest('td');
      const currentTr = currentTd?.closest('tr');
      const tbody = currentTr?.closest('tbody');
      if (!currentTd || !currentTr || !tbody) return null;

      const allTrs = Array.from(tbody.children) as HTMLTableRowElement[];
      const currentRowIdx = allTrs.indexOf(currentTr as HTMLTableRowElement);
      const currentColIdx = Array.from(currentTr.children).indexOf(currentTd);
      const numCols = GRID_COLUMNS.length;

      let dRow = 0, dCol = 0;
      if (key === 'Tab') dCol = shiftKey ? -1 : 1;
      else if (key === 'ArrowRight') dCol = 1;
      else if (key === 'ArrowLeft') dCol = -1;
      else if (key === 'ArrowDown') dRow = 1;
      else if (key === 'ArrowUp') dRow = -1;
      else return null;

      let targetRow = currentRowIdx + dRow;
      let targetCol = currentColIdx + dCol;

      // Wrap between rows
      if (targetCol < 0) {
        if (targetRow > 0) { targetRow--; targetCol = numCols - 1; }
        else return null;
      } else if (targetCol >= numCols) {
        if (targetRow < allTrs.length - 1) { targetRow++; targetCol = 0; }
        else return null;
      }

      if (targetRow < 0 || targetRow >= allTrs.length) return null;

      const targetTd = allTrs[targetRow].children[targetCol] as HTMLElement;
      if (!targetTd) return null;

      // Skip non-editable column (excel_row_number), shift one further
      if (targetTd.dataset.colKey === 'excel_row_number') {
        return navigateToCell(targetTd, dCol >= 0 ? 'ArrowRight' : 'ArrowLeft', false);
      }

      return targetTd;
    },
    [],
  );

  const handleStartEdit = useCallback(() => {
    if (isReadOnly || savingRef.current) return;
    const strVal = String(displayValue);
    setEditValue(strVal);
    originalValueRef.current = strVal;
    setEditing(true);
  }, [displayValue, isReadOnly]);

  const handleSave = useCallback(async () => {
    // Guard: prevent double-save (Enter + onBlur race)
    if (savingRef.current) return;

    // Guard: skip save if the value hasn't actually changed —
    // otherwise the backend clears field_errors without re-validating,
    // making errors disappear on cells the user clicked but didn't modify.
    const rawValue = editValue;
    if (rawValue === originalValueRef.current) {
      setEditing(false);
      return;
    }

    savingRef.current = true;
    setSaving(true);
    setEditing(false);

    let finalValue: any = rawValue;
    if (numeric) {
      const parsed = parseFloat(rawValue);
      finalValue = Number.isNaN(parsed) ? 0 : parsed;
    }

    try {
      await onSave(rowId, field, finalValue);
    } catch {
      // Error handled by context
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }, [editValue, field, rowId, onSave, numeric]);

  // -----------------------------------------------------------------------
  // Unified key-down handler for input/select cells
  // -----------------------------------------------------------------------
  const handleCellKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSave();
        return;
      }
      if (e.key === 'Escape') {
        setEditing(false);
        return;
      }
      // For select cells, arrow keys change the selected option — don't intercept
      if (dropdown && e.key.startsWith('Arrow')) return;

      if (e.key === 'Tab' || e.key.startsWith('Arrow')) {
        e.preventDefault();
        const targetTd = navigateToCell(e.currentTarget as HTMLElement, e.key, e.shiftKey);
        if (!targetTd) return;

        handleSave().then(() => {
          requestAnimationFrame(() => {
            targetTd.focus();
          });
        });
      }
    },
    [handleSave, navigateToCell, dropdown],
  );

  const isEditing = editing && !isReadOnly;

  const cellClasses = [
    'px-1.5 sm:px-2 py-1 sm:py-1.5 text-[10px] sm:text-xs border-r border-b border-gray-200 dark:border-gray-700 truncate text-gray-900 dark:text-gray-100',
    width || '',
    isError ? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200' : '',
    saving ? 'opacity-50' : '',
    !isReadOnly && !isEditing ? 'cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <td
      className={cellClasses}
      data-col-key={field}
      tabIndex={!isReadOnly && !isEditing ? 0 : undefined}
      onClick={isEditing ? undefined : handleStartEdit}
      onFocus={isEditing ? undefined : handleStartEdit}
      title={errorMessages.length > 0 ? errorMessages.join('; ') : displayValue?.toString()}
    >
      {isEditing ? (
        dropdown ? (
          <select
            className="w-full px-1 py-1 text-xs border border-blue-500 rounded bg-white text-gray-900"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleCellKeyDown}
            autoFocus
          >
            <option value="">Select...</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : (
          <input
            type={numeric ? 'number' : 'text'}
            className="w-full px-1 py-1 text-xs border border-blue-500 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none [appearance:textfield]"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleCellKeyDown}
            autoFocus
            step={numeric ? 'any' : undefined}
          />
        )
      ) : (
        <div className="flex items-center gap-1">
          <span className="truncate flex-1">{displayValue}</span>
          {isError && (
            <svg className="w-3 h-3 shrink-0 text-red-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          )}
        </div>
      )}
    </td>
  );
}

// ---------------------------------------------------------------------------
// Main Grid Component
// ---------------------------------------------------------------------------

export default function ExcelStagingGrid({
  onBackToUpload,
  onCommitComplete,
}: ExcelStagingGridProps) {
  const {
    rows,
    currentSession,
    isProcessing,
    processingText,
    error,
    updateCell,
    recheckSession,
    commitSession,
    cancelSession,
  } = useExcelStaging();

  const erroredRows = rows.filter((r) => !r.is_valid).length;
  const validRows = rows.filter((r) => r.is_valid).length;
  const totalRows = rows.length;
  const allValid = totalRows > 0 && erroredRows === 0;

  const handleUpdateCell = useCallback(
    async (rowId: string, field: string, value: any) => {
      await updateCell(rowId, field, value);
    },
    [updateCell]
  );

  const handleCommit = useCallback(async () => {
    try {
      // The commitSession in the context clears state after success
      await commitSession();
      if (onCommitComplete) {
        onCommitComplete({ total_committed: validRows });
      }
    } catch {
      // Error handled by context
    }
  }, [commitSession, onCommitComplete, validRows]);

  const handleCancel = useCallback(async () => {
    await cancelSession();
    if (onBackToUpload) {
      onBackToUpload();
    }
  }, [cancelSession, onBackToUpload]);

  // If no rows, show empty state
  if (totalRows === 0 && !isProcessing) {
    return (
      <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-gray-200 dark:border-gray-700 p-4 sm:p-8 text-center">
        <p className="text-gray-500 dark:text-gray-400">No rows to display.</p>
        {onBackToUpload && (
          <button
            onClick={onBackToUpload}
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            Upload another file
          </button>
        )}
      </div>
    );
  }

  return (
    <div className='flex flex-col flex-1 min-h-0 gap-2'>
      {/* Processing Overlay */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black/30 dark:bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl p-4 sm:p-8 mx-4 shadow-xl flex flex-col items-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 dark:border-blue-400 mb-4"></div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{processingText || 'Processing...'}</p>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mx-2 sm:mx-4 mt-2 sm:mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-2 sm:p-3">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Summary Bar */}
      <div className="px-3 sm:px-4 py-2 sm:py-3 rounded-2xl sm:rounded-3xl lg:rounded-4xl bg-white border-2 border-blue-600 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-2">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {totalRows} rows
          </span>
          <span className="text-sm text-green-600 dark:text-green-400">
            {validRows} valid
          </span>
          {erroredRows > 0 && (
            <span className="text-sm text-red-600 dark:text-red-400">
              {erroredRows} with errors
            </span>
          )}
        </div>
        {currentSession && (
          <span className="text-xs text-black dark:text-gray-500">
            {currentSession.original_filename}
          </span>
        )}
      </div>

      {/* Progress Bar */}
      {totalRows > 0 && (
        <div className="px-3 sm:px-4 py-1">
          <div className="w-full bg-gray-200 border border-blue-600 rounded-full h-1.5">
            <div
              className="bg-green-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${(validRows / totalRows) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Scrollable Grid */}
      <div className="overflow-auto flex-1 min-h-0 border-2 border-blue-600 rounded-2xl sm:rounded-3xl lg:rounded-4xl">
        <table className="w-full border-collapse table-fixed">
          <thead>
            <tr className="bg-gray-50">
              {GRID_COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`px-1.5 sm:px-2 py-1.5 sm:py-2 text-[10px] sm:text-xs font-semibold text-black text-left border-r border-b border-white dark:border-gray-700 sticky top-0 bg-[#7c97f0] z-10 ${col.width || ''}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const prevGroup = idx > 0 ? rows[idx - 1].group_key : null;
              const isGroupStart = prevGroup !== row.group_key;

              return (
                <tr
                  key={row.id}
                  className={`${
                    isGroupStart ? 'border-t-2 border-blue-300 bg-blue-50' : ''
                  } ${
                    row.is_valid
                      ? 'border-l-4 border-l-green-400'
                      : 'border-l-4 border-l-red-400'
                  } transition-colors hover:bg-gray-50`}
                >
                  {GRID_COLUMNS.map((col) => {
                    const isError = !!(
                      row.field_errors && row.field_errors[col.key]
                    );
                    const errorMessages = row.field_errors?.[col.key] || [];
                    return (
                      <EditableCell
                        key={col.key}
                        rowId={row.id}
                        field={col.key}
                        value={row[col.key]}
                        isError={isError}
                        errorMessages={errorMessages}
                        onSave={handleUpdateCell}
                        isReadOnly={isProcessing}
                        width={col.width}
                      />
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Button Bar */}
      <div className="px-3 sm:px-4 py-2 sm:py-3 bg-white border-2 border-blue-600 rounded-2xl sm:rounded-3xl lg:rounded-4xl flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3">
        <button
          onClick={handleCancel}
          disabled={isProcessing}
          className="w-full sm:w-auto px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-center"
        >
          Cancel
        </button>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
          {erroredRows > 0 && (
            <button
              onClick={recheckSession}
              disabled={isProcessing}
              className="w-full sm:w-auto px-4 py-2 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm text-center"
            >
              Recheck
            </button>
          )}

          {allValid && (
            <button
              onClick={handleCommit}
              disabled={isProcessing}
              className="w-full sm:w-auto px-6 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm text-center"
            >
              Upload All ({validRows} invoices)
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
