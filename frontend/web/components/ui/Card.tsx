/**
 * Card primitive (DESIGN.md component.product-card / feature-tile / doc-card).
 *
 * Flat cards with hairline borders, NO drop shadows (per design spec).
 */
import { HTMLAttributes } from "react";

type CardVariant = "product" | "feature" | "doc" | "pricing";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

const VARIANTS: Record<CardVariant, string> = {
  product: "bg-surface-card p-6",
  feature: "bg-surface-card p-5",
  doc: "bg-surface-doc p-6",
  pricing: "bg-surface-card p-8",
};

export function Card({ variant = "product", className = "", children, ...props }: CardProps) {
  return (
    <div
      className={`rounded-md border border-hairline ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
