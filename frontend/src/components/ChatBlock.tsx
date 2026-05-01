import { motion } from "framer-motion";
import { Bot, User } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const PLACEHOLDER_RULES: Array<{ keywords: string[]; placeholder: string }> = [
  {
    keywords: ["target", "audience", "user", "customer", "who", "persona"],
    placeholder: "e.g. Small business owners aged 30–50 who struggle with manual invoicing and want a simple mobile-first solution…",
  },
  {
    keywords: ["feature", "scope", "include", "functionality", "mvp", "launch", "day one"],
    placeholder: "e.g. Core features at launch: user auth, dashboard, real-time notifications, and CSV export. Analytics in v2…",
  },
  {
    keywords: ["monetiz", "revenue", "pricing", "freemium", "subscription", "paid", "business model"],
    placeholder: "e.g. Free tier for up to 3 projects; Pro plan at $12/month with unlimited projects and priority support…",
  },
  {
    keywords: ["differenti", "unique", "competitor", "compet", "stand out", "compared", "unlike", "advantage"],
    placeholder: "e.g. Unlike Notion or Linear, we focus exclusively on async remote teams with built-in timezone awareness…",
  },
  {
    keywords: ["tech", "stack", "platform", "mobile", "web", "framework", "backend", "database", "infrastructure"],
    placeholder: "e.g. React + TypeScript frontend, FastAPI backend, PostgreSQL, hosted on AWS. iOS and Android via React Native…",
  },
  {
    keywords: ["data", "storage", "privacy", "security", "compliance", "gdpr", "cloud", "local"],
    placeholder: "e.g. Cloud-based with end-to-end encryption, GDPR compliant, optional local-only mode for enterprise…",
  },
  {
    keywords: ["timeline", "launch", "deadline", "schedule", "roadmap", "milestone", "phase"],
    placeholder: "e.g. MVP in 10 weeks, beta in month 4, public launch in month 6 with a waitlist campaign…",
  },
  {
    keywords: ["team", "resource", "budget", "funding", "size", "headcount"],
    placeholder: "e.g. Two co-founders (engineering + design), bootstrapped, $50k budget for the first 6 months…",
  },
  {
    keywords: ["integrat", "third.party", "api", "connect", "plugin", "zapier", "slack", "social"],
    placeholder: "e.g. Slack and Google Calendar integrations at launch; Zapier and REST API in Q2…",
  },
  {
    keywords: ["metric", "success", "kpi", "goal", "measure", "track", "analytic"],
    placeholder: "e.g. 1,000 active users within 3 months, <2% monthly churn, NPS above 40…",
  },
];

function getPlaceholder(question: string): string {
  const lower = question.toLowerCase();
  for (const rule of PLACEHOLDER_RULES) {
    if (rule.keywords.some((kw) => lower.includes(kw))) {
      return rule.placeholder;
    }
  }
  return "e.g. Share as much context as you can — specifics help produce better output…";
}

interface ChatBlockProps {
  questions: string[];
  answers: Record<string, string>;
  onAnswerChange: (key: string, value: string) => void;
  /** Show typing row on the AI side */
  thinking?: boolean;
  thinkingLabel?: string;
  className?: string;
}

export function ChatBlock({
  questions,
  answers,
  onAnswerChange,
  thinking = false,
  thinkingLabel = "Clarifier is thinking…",
  className,
}: ChatBlockProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="grid gap-8 lg:grid-cols-2 lg:gap-10">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Agent
          </span>
        </div>
        <div className="mb-2 flex items-center justify-end gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Your answers
          </span>
        </div>
      </div>

      {thinking && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-4 lg:grid-cols-2 lg:gap-10"
        >
          <div className="flex gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-primary/30 bg-primary/10">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-white/[0.08] bg-white/[0.04] px-4 py-3 shadow-inner">
              <p className="text-[13px] text-[#E5E7EB]/90">{thinkingLabel}</p>
              <TypingDots />
            </div>
          </div>
          <div />
        </motion.div>
      )}

      {questions.map((q, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="grid items-stretch gap-4 lg:grid-cols-2 lg:gap-10"
        >
          <div className="flex gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.04]">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-white/[0.08] bg-white/[0.04] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <p className="text-[10px] font-medium uppercase tracking-wider text-primary/90">
                Clarifier · Step {i + 1} of {questions.length}
              </p>
              <p className="mt-1.5 text-[14px] leading-relaxed text-[#E5E7EB]/95">{q}</p>
            </div>
          </div>

          <div className="flex h-full flex-row-reverse gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.04]">
              <User className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex h-full flex-1 flex-col rounded-2xl rounded-tr-sm border border-white/[0.08] bg-white/[0.04] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <p className="text-[10px] font-medium uppercase tracking-wider text-primary/90">
                Answer · Step {i + 1} of {questions.length}
              </p>
              <Label htmlFor={`chat-a-${i}`} className="sr-only">
                Answer {i + 1}
              </Label>
              <Textarea
                id={`chat-a-${i}`}
                value={answers[`q${i + 1}`] || ""}
                onChange={(e) => onAnswerChange(`q${i + 1}`, e.target.value)}
                placeholder="Type your answer…"
                autoComplete="off"
                rows={3}
                className="mt-1.5 min-h-[92px] flex-1 resize-none border-0 bg-transparent px-0 py-0 text-[14px] leading-relaxed text-[#E5E7EB]/95 shadow-none placeholder:text-muted-foreground/45 focus-visible:ring-0"
              />
              {!answers[`q${i + 1}`]?.trim() && (
                <button
                  type="button"
                  onClick={() => onAnswerChange(`q${i + 1}`, getPlaceholder(q).replace(/^e\.g\.\s*/i, ""))}
                  className="mt-2 w-full rounded-lg border border-dashed border-white/[0.1] bg-white/[0.02] px-3 py-2 text-left text-[11px] text-muted-foreground/50 hover:border-primary/30 hover:bg-primary/5 hover:text-muted-foreground/80 transition-all duration-150"
                >
                  <span className="mr-1.5 text-primary/40">↵</span>
                  {getPlaceholder(q)}
                </button>
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function TypingDots() {
  return (
    <div className="mt-2 flex gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-primary/80"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}
