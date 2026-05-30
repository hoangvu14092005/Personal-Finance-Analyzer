/**
 * CalloutBanner primitive (DESIGN.md component.banner-tip-*).
 *
 * 4 severities with pastel backgrounds + emoji icons.
 */
import { HTMLAttributes, ReactNode } from "react";

type Severity = "info" | "success" | "warning" | "note";

interface CalloutBannerProps extends HTMLAttributes<HTMLDivElement> {
  severity: Severity;
  title?: string;
  children: ReactNode;
}

const SEVERITY_STYLES: Record<Severity, { bg: string; icon: string }> = {
  info: { bg: "bg-accent-blue-soft", icon: "💡" },
  success: { bg: "bg-accent-green-soft", icon: "✅" },
  warning: { bg: "bg-accent-red-soft", icon: "⚠️" },
  note: { bg: "bg-accent-purple-soft", icon: "📘" },
};

export function CalloutBanner({
  severity,
  title,
  className = "",
  children,
  ...props
}: CalloutBannerProps) {
  const style = SEVERITY_STYLES[severity];
  return (
    <div
      className={`rounded-md p-4 ${style.bg} text-ink ${className}`}
      {...props}
    >
      <div className="flex gap-3">
        <span aria-hidden className="text-lg leading-none flex-shrink-0">
          {style.icon}
        </span>
        <div className="flex-1">
          {title ? (
            <div className="font-semibold mb-1 text-body-md">{title}</div>
          ) : null}
          <div className="text-body-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
