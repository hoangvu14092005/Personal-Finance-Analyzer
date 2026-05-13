/**
 * Heading primitives (DESIGN.md typography scale).
 */
import { HTMLAttributes, ReactNode } from "react";

interface HeadingProps extends HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode;
}

export function DisplayXl({ className = "", children, ...props }: HeadingProps) {
  return (
    <h1 className={`text-display-xl text-ink ${className}`} {...props}>
      {children}
    </h1>
  );
}

export function DisplayLg({ className = "", children, ...props }: HeadingProps) {
  return (
    <h1 className={`text-display-lg text-ink ${className}`} {...props}>
      {children}
    </h1>
  );
}

export function HeadingLg({ className = "", children, ...props }: HeadingProps) {
  return (
    <h2 className={`text-heading-lg text-ink ${className}`} {...props}>
      {children}
    </h2>
  );
}

export function HeadingMd({ className = "", children, ...props }: HeadingProps) {
  return (
    <h3 className={`text-heading-md text-ink ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function HeadingSmMixed({ className = "", children, ...props }: HeadingProps) {
  return (
    <h3 className={`text-heading-sm-mixed text-ink ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function Eyebrow({ className = "", children, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={`text-utility-xs text-body ${className}`} {...props}>
      {children}
    </p>
  );
}
