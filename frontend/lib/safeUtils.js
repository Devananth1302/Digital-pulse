/**
 * Safe utility functions to prevent NaN/undefined/null issues
 */

/**
 * Safely convert a value to a number with fallback
 */
export function safeNumber(value, fallback = 0) {
  if (value === null || value === undefined) return fallback;
  const num = Number(value);
  if (isNaN(num) || !isFinite(num)) return fallback;
  return num;
}

/**
 * Safely format a number to fixed decimal places
 */
export function safeFixed(value, decimals = 1, fallback = '0.0') {
  const num = safeNumber(value, null);
  if (num === null) return fallback;
  return num.toFixed(decimals);
}

/**
 * Safely format a number with locale formatting
 */
export function safeLocaleString(value, fallback = '0') {
  const num = safeNumber(value, null);
  if (num === null) return fallback;
  return Math.round(num).toLocaleString();
}

/**
 * Safely calculate percentage
 */
export function safePercent(value, total, decimals = 0) {
  const numValue = safeNumber(value, 0);
  const numTotal = safeNumber(total, 0);
  if (numTotal === 0) return 0;
  const pct = (numValue / numTotal) * 100;
  return decimals > 0 ? pct.toFixed(decimals) : Math.round(pct);
}

/**
 * Safely get a nested property with fallback
 */
export function safeGet(obj, path, fallback = null) {
  if (!obj) return fallback;
  const keys = path.split('.');
  let result = obj;
  for (const key of keys) {
    if (result === null || result === undefined) return fallback;
    result = result[key];
  }
  return result ?? fallback;
}

/**
 * Safely parse a date
 */
export function safeDate(value) {
  if (!value) return null;
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

/**
 * Format relative time safely
 */
export function formatRelativeTime(timestamp) {
  const d = safeDate(timestamp);
  if (!d) return '';

  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.round(diffMs / 60000);
  const diffHours = Math.round(diffMs / 3600000);
  const diffDays = Math.round(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString();
}

/**
 * Safely truncate text
 */
export function truncate(text, maxLength = 100, suffix = '...') {
  if (!text || typeof text !== 'string') return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Ensure value is an array
 */
export function ensureArray(value) {
  if (Array.isArray(value)) return value;
  if (value === null || value === undefined) return [];
  return [value];
}

/**
 * Safely divide with zero protection
 */
export function safeDivide(numerator, denominator, fallback = 0) {
  const num = safeNumber(numerator, 0);
  const den = safeNumber(denominator, 0);
  if (den === 0) return fallback;
  return num / den;
}
