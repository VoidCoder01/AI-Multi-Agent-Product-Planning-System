import { useEffect, useState } from "react";

export interface AgentProgressProps {
  /** Syncs the top pipeline (0–4) with the simulated phase. */
  onPhaseChange?: (index: number) => void;
  /** Pauses simulated phase rotation and tips (UI-only). */
  paused?: boolean;
}

const PHASES = [
  {
    id: "clarify",
    name: "Clarification Agent",
    icon: "🔍",
    message: "Asking the right questions...",
    emoji: "💭",
    tip: "Analyzing your product idea and identifying knowledge gaps",
  },
  {
    id: "requirement",
    name: "Requirement Agent",
    icon: "📋",
    message: "Structuring your vision...",
    emoji: "✍️",
    tip: "Converting Q&A into a structured project brief",
  },
  {
    id: "pm",
    name: "Product Manager",
    icon: "🎯",
    message: "Crafting the PRD...",
    emoji: "📄",
    tip: "Writing functional requirements and success metrics",
  },
  {
    id: "scrum",
    name: "Scrum Master",
    icon: "📊",
    message: "Breaking down into epics and stories...",
    emoji: "📑",
    tip: "Organizing work into epics and user stories with acceptance criteria",
  },
  {
    id: "task",
    name: "Tech Lead",
    icon: "⚙️",
    message: "Decomposing into tasks...",
    emoji: "🔨",
    tip: "Breaking user stories into actionable engineering tasks",
  },
] as const;

const ROTATING_TIPS = [
  "💡 This AI system uses 5 specialized agents working together like a real product team",
  "🚀 Powered by Claude Sonnet 4 — strong reasoning for structured documentation",
  "📊 We're generating epics, stories, and many engineering tasks from your idea",
  "⚡ Each agent has a unique system prompt optimized for its role",
  "🎯 The PRD includes functional and non-functional requirements",
  "🔄 LangGraph orchestrates the sequential workflow between agents",
  "✨ Your download will include brief, PRD, epics, stories, and tasks",
];

const PHASE_MS = 12_000;
const TIP_MS = 8_000;

export function AgentProgress({ onPhaseChange, paused = false }: AgentProgressProps) {
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    onPhaseChange?.(currentPhaseIndex);
  }, [currentPhaseIndex, onPhaseChange]);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setCurrentPhaseIndex((prev) =>
        prev < PHASES.length - 1 ? prev + 1 : prev
      );
    }, PHASE_MS);
    return () => clearInterval(interval);
  }, [paused]);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % ROTATING_TIPS.length);
    }, TIP_MS);
    return () => clearInterval(interval);
  }, [paused]);

  const currentPhase = PHASES[currentPhaseIndex];
  const progressPercentage = ((currentPhaseIndex + 1) / PHASES.length) * 100;
  const remainingPhases = Math.max(0, PHASES.length - currentPhaseIndex - 1);
  const estimatedSeconds = remainingPhases * (PHASE_MS / 1000);

  return (
    <div className="agent-progress">
      <div className="progress-bar-container">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <div className="progress-percentage">
          {Math.round(progressPercentage)}% complete
        </div>
      </div>

      <div className="progress-steps">
        {PHASES.map((p, i) => (
          <div
            key={p.id}
            className={`step ${i <= currentPhaseIndex ? "active" : ""} ${
              i === currentPhaseIndex ? "current" : ""
            }`}
          >
            <div className="step-icon-wrap">
              <div className="step-icon">{p.icon}</div>
              {i < currentPhaseIndex && (
                <div className="step-check" aria-hidden>
                  ✓
                </div>
              )}
            </div>
            <div className="step-name">{p.name}</div>
          </div>
        ))}
      </div>

      <div className="current-phase">
        <div className="phase-icon-large" aria-hidden>
          {currentPhase.emoji}
        </div>
        <h3>{currentPhase.name}</h3>
        <p className="phase-message">{currentPhase.message}</p>
        <p className="phase-tip">{currentPhase.tip}</p>

        <div className="pulse-loader" aria-hidden>
          <span />
          <span />
          <span />
        </div>
        {!paused && (
          <p className="mt-3 text-center text-[11px] text-muted-foreground/90">
            Agent is reasoning
            <span className="inline-flex gap-0.5 pl-1">
              {[0, 1, 2].map((d) => (
                <span
                  key={d}
                  className="inline-block h-1 w-1 animate-pulse rounded-full bg-primary/70"
                  style={{ animationDelay: `${d * 0.12}s` }}
                />
              ))}
            </span>
          </p>
        )}
        {paused && (
          <p className="mt-3 text-center text-[11px] font-medium text-amber-400/95">Paused — resume to continue</p>
        )}
      </div>

      <div className="fun-facts">
        <p className="tip" key={tipIndex}>
          {ROTATING_TIPS[tipIndex]}
        </p>
      </div>

      <div className="time-estimate">
        <span className="time-icon" aria-hidden>
          ⏱️
        </span>
        <span>
          Estimated time remaining (visual guide): ~{estimatedSeconds}s across{" "}
          {remainingPhases} phase{remainingPhases === 1 ? "" : "s"} — actual run
          may take longer
        </span>
      </div>
    </div>
  );
}
