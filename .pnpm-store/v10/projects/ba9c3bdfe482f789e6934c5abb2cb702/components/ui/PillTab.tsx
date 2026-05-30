/**
 * PillTab primitive (DESIGN.md component.pill-tab).
 *
 * Active state flips to ink bg + white text (full inversion).
 */
import { ButtonHTMLAttributes } from "react";

interface PillTabProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

export function PillTab({ active = false, className = "", children, ...props }: PillTabProps) {
  const state = active
    ? "bg-ink text-on-dark"
    : "bg-transparent text-body hover:bg-surface-soft hover:text-ink";
  return (
    <button
      type="button"
      className={`rounded-full px-4 py-1.5 text-button-sm transition-colors whitespace-nowrap ${state} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
