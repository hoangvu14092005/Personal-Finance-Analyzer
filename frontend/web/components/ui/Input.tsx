/**
 * Input primitive (DESIGN.md component.text-input).
 *
 * - 36px height, 12px horizontal padding
 * - 1px hairline border, surface-card bg
 * - Blue focus ring
 */
import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={`w-full h-9 px-3 rounded-md border border-hairline bg-surface-card text-ink text-body-md placeholder:text-ash focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 disabled:bg-surface-soft disabled:text-ash ${className}`}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`w-full min-h-[80px] px-3 py-2 rounded-md border border-hairline bg-surface-card text-ink text-body-md placeholder:text-ash focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 resize-y ${className}`}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
