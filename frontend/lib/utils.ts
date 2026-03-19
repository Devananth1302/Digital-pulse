/**
 * Utility function for merging Tailwind CSS classes
 * Handles conflicting utility classes gracefully
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
