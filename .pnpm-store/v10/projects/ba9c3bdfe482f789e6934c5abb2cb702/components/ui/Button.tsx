/**
 * Button primitive (DESIGN.md component.button-*).
 *
 * Variants:
 * - primary: yellow-orange CTA (brand signature)
 * - secondary: soft gray alternative
 * - tertiary: ghost text button
 * - danger: red accent for destructive actions
 */
import { ButtonHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "tertiary" | "danger";
type ButtonSize = "md" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-on hover:bg-primary-pressed active:bg-primary-active",
  secondary: "bg-surface-soft text-ink hover:bg-hairline-soft",
  tertiary: "bg-transparent text-ink hover:bg-surface-soft",
  danger: "bg-accent-red text-on-dark hover:opacity-90",
};

const SIZES: Record<ButtonSize, string> = {
  md: "h-10 px-4 text-button-md",
  sm: "h-8 px-3 text-button-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", className = "", disabled, children, ...props },
    ref,
  ) => {
    const disabledClass = disabled
      ? "bg-surface-soft text-ash cursor-not-allowed hover:bg-surface-soft"
      : VARIANTS[variant];
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={`inline-flex items-center justify-center gap-2 rounded-md font-bold transition-colors whitespace-nowrap ${SIZES[size]} ${disabledClass} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
