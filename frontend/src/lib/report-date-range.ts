/**
 * Date-range resolution for the report filters.
 *
 * The report API requires an explicit [date_from, date_to], but the page lets
 * the user search by customer alone — so a bound the user did not supply is
 * left open: the lower bound is the earliest year the account has invoices in,
 * the upper bound is today. That is the "all data from the start up to now"
 * case, and it behaves the same whether one bound or both were omitted.
 *
 * Kept out of the page component so the rules can be read (and tested) on
 * their own.
 */

/** Floor for an open "from" when the account has no invoice years at all. */
export const ALL_TIME_FROM_YEAR = 1970;

/**
 * Today as YYYY-MM-DD in the user's own timezone. `toISOString()` is UTC and
 * would report yesterday for timezones ahead of UTC (e.g. PKT, UTC+5) until
 * 05:00 local, silently excluding the current day from the report.
 */
export function todayISO(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

export type ReportRangeResult =
  | { ok: true; from: string; to: string }
  | { ok: false; error: string };

export interface ReportRangeInput {
  year: string;
  month: string;
  dateFrom: string;
  dateTo: string;
  /** True when a customer name or NTN/CNIC is filled in. */
  hasBuyerFilter: boolean;
  /** Years the account has invoices in (feeds the Year dropdown). */
  availableYears: number[];
  /** Injectable for tests. */
  today?: Date;
}

export function resolveReportRange({
  year,
  month,
  dateFrom,
  dateTo,
  hasBuyerFilter,
  availableYears,
  today,
}: ReportRangeInput): ReportRangeResult {
  if (year) {
    // Year/month mode takes precedence over the From/To fields
    if (month) {
      const m = Number(month);
      const lastDay = new Date(Number(year), m, 0).getDate();
      return {
        ok: true,
        from: `${year}-${month}-01`,
        to: `${year}-${month}-${String(lastDay).padStart(2, '0')}`,
      };
    }
    return { ok: true, from: `${year}-01-01`, to: `${year}-12-31` };
  }

  if (month) {
    return { ok: false, error: 'Please select a year along with the month' };
  }

  // Nothing to search on — the report covers every invoice in the company, so
  // require at least one filter rather than returning an unbounded dump.
  if (!dateFrom && !dateTo && !hasBuyerFilter) {
    return {
      ok: false,
      error: 'Select a customer, a date range, or a Year/Month to generate a report',
    };
  }

  const earliestYear = availableYears.length
    ? Math.min(...availableYears)
    : ALL_TIME_FROM_YEAR;
  const from = dateFrom || `${earliestYear}-01-01`;
  const to = dateTo || todayISO(today);

  if (from > to) {
    return { ok: false, error: 'From date must not be after To date' };
  }

  return { ok: true, from, to };
}
