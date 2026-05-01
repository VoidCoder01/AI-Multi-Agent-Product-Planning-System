import { useState } from "react";

export interface AIErrorDetail {
  code: string;
  title: string;
  message: string;
  action: string;
  retryable: boolean;
}

interface AIErrorBannerProps {
  error: string | AIErrorDetail | null;
  onDismiss?: () => void;
  onRetry?: () => void;
}

const CODE_ICONS: Record<string, string> = {
  insufficient_credits: "💳",
  invalid_api_key: "🔑",
  model_not_found: "🤖",
  rate_limit: "⏱️",
  provider_overloaded: "🔥",
  context_too_long: "📄",
  connection_error: "🌐",
  unknown_error: "⚠️",
};

const CODE_COLORS: Record<string, string> = {
  insufficient_credits: "border-amber-500/40 bg-amber-500/8",
  invalid_api_key:      "border-red-500/40 bg-red-500/8",
  model_not_found:      "border-orange-500/40 bg-orange-500/8",
  rate_limit:           "border-yellow-500/40 bg-yellow-500/8",
  provider_overloaded:  "border-orange-400/40 bg-orange-400/8",
  context_too_long:     "border-blue-500/40 bg-blue-500/8",
  connection_error:     "border-red-400/40 bg-red-400/8",
  unknown_error:        "border-red-500/40 bg-red-500/8",
};

function parseError(raw: string | AIErrorDetail): AIErrorDetail {
  if (typeof raw === "object" && raw !== null && "code" in raw) return raw;
  // Try to extract a structured error from a plain string (e.g. from parseError() HTTP path)
  const str = String(raw);
  return {
    code: "unknown_error",
    title: "Request failed",
    message: str.length > 280 ? str.slice(0, 277) + "…" : str,
    action: "Check the backend logs or switch to a different AI provider.",
    retryable: false,
  };
}

export function AIErrorBanner({ error, onDismiss, onRetry }: AIErrorBannerProps) {
  const [expanded, setExpanded] = useState(false);
  if (!error) return null;

  const detail = parseError(error);
  const icon = CODE_ICONS[detail.code] ?? "⚠️";
  const colorCls = CODE_COLORS[detail.code] ?? "border-red-500/40 bg-red-500/8";

  return (
    <div className={`rounded-xl border px-4 py-3.5 ${colorCls} text-sm`}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0 text-lg leading-none">{icon}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold text-foreground leading-snug">{detail.title}</p>
            <button
              onClick={onDismiss}
              className="shrink-0 text-muted-foreground/60 hover:text-muted-foreground transition-colors text-xs"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>

          <p className="mt-1 text-muted-foreground leading-relaxed">{detail.message}</p>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-md bg-white/[0.06] px-2 py-0.5 text-[11px] text-muted-foreground/80">
              💡 {detail.action}
            </span>
          </div>

          <div className="mt-2.5 flex items-center gap-2">
            {detail.retryable && onRetry && (
              <button
                onClick={onRetry}
                className="rounded-md bg-primary/20 px-3 py-1 text-[11px] font-medium text-primary hover:bg-primary/30 transition-colors"
              >
                Retry
              </button>
            )}
            {detail.code === "insufficient_credits" && (
              <a
                href="https://console.anthropic.com/settings/billing"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md bg-amber-500/20 px-3 py-1 text-[11px] font-medium text-amber-400 hover:bg-amber-500/30 transition-colors"
              >
                Top up credits ↗
              </a>
            )}
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-[11px] text-muted-foreground/50 hover:text-muted-foreground/80 transition-colors"
            >
              {expanded ? "Hide details" : "Show details"}
            </button>
          </div>

          {expanded && (
            <pre className="mt-2 rounded-md bg-black/30 px-3 py-2 text-[10px] text-muted-foreground/70 whitespace-pre-wrap break-all leading-relaxed font-mono max-h-36 overflow-y-auto">
              code: {detail.code}{"\n"}retryable: {String(detail.retryable)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
