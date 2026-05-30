/**
 * Badge primitives (DESIGN.md component.badge-*).
 */
import { HTMLAttributes } from "react";

type BadgeTone = "blue" | "green" | "red" | "purple" | "neutral";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const TONES: Record<BadgeTone, string> = {
  blue: "bg-accent-blue-soft text-link-blue",
  green: "bg-accent-green-soft text-accent-green",
  red: "bg-accent-red-soft text-accent-red",
  purple: "bg-accent-purple-soft text-accent-purple",
  neutral: "bg-surface-soft text-body",
};

export function Badge({ tone = "blue", className = "", children, ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption-xs ${TONES[tone]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}

export function BadgeUppercase({ className = "", children, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={`inline-block text-utility-xs text-body ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
