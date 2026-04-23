import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, ArrowLeft, Command, Paperclip, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { TerminalHeader } from "@/components/TerminalHeader";
import { PipelineFlow } from "@/components/PipelineFlow";
import type { AgentNodeState } from "@/components/AgentNode";
import { AgentProgress } from "@/components/AgentProgress";
import { ResultsViewer } from "@/components/ResultsViewer";
import { StatusBar, type AppStage } from "@/components/StatusBar";
import { LogPanel, type ExecutionLogEntry, type TraceRunningState } from "@/components/LogPanel";
import { ChatBlock } from "@/components/ChatBlock";
import { CursorGlow } from "@/components/CursorGlow";
import { FloatingActions } from "@/components/FloatingActions";
import { ClarificationThinkingFeed } from "@/components/ClarificationThinkingFeed";
import { UserContextPanel } from "@/components/UserContextPanel";
import { WhatsNext } from "@/components/WhatsNext";

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (data.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (typeof data.detail === "object" && data.detail !== null) {
        const detail = data.detail as Record<string, unknown>;
        const stage = typeof detail.stage === "string" ? `${detail.stage}: ` : "";
        const message =
          (typeof detail.message === "string" && detail.message) ||
          (typeof detail.detail === "string" && detail.detail) ||
          (typeof detail.error === "string" && detail.error);
        if (message) return `${stage}${message}`;
      }
      return "Request failed. Please try again.";
    }
  } catch {
    /* ignore */
  }
  return res.statusText || `HTTP ${res.status}`;
}

const SUGGESTIONS = ["Marketplace for indie makers", "AI SaaS for support teams", "Mobile app for habit tracking"];

/** Trace copy aligned with the simulated generation phases in `AgentProgress`. */
const PIPELINE_TRACE = [
  {
    agent: "Clarification Agent",
    done: "Structured input validated",
    detail: "Merged Q&A into a single narrative for downstream agents.",
    run: "Asking the right questions…",
  },
  {
    agent: "Requirement Agent",
    done: "Project brief synthesized",
    detail: "Brief section passed to PM agent.",
    run: "Structuring your vision…",
  },
  {
    agent: "Product Manager",
    done: "PRD drafted",
    detail: "Requirements, metrics, and scope captured.",
    run: "Crafting the PRD…",
  },
  {
    agent: "Architect Agent",
    done: "Technical architecture designed",
    detail: "Services, stack, data flow, and scalability documented.",
    run: "Designing technical architecture…",
  },
  {
    agent: "Scrum Master",
    done: "Epics and user stories created",
    detail: "Backlog items with acceptance criteria.",
    run: "Breaking down into epics and stories…",
  },
  {
    agent: "Tech Lead",
    done: "Engineering tasks decomposed",
    detail: "Tasks ready for estimation and sprint planning.",
    run: "Decomposing into tasks…",
  },
  {
    agent: "Orchestrator",
    done: "Cross-document validation passed",
    detail: "Consistency checks across all artifacts complete.",
    run: "Running final validation…",
  },
] as const;

const PIPELINE_MINI_LABELS = ["Clarifier", "Analyst", "PM", "Architect", "Scrum", "Tasks", "Validate"] as const;

function truncate(s: string, max: number) {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

const pageTransition = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] as const },
};

export default function Index() {
  const [backendOnline, setBackendOnline] = useState(true);
  const [step, setStep] = useState(1);
  const [productIdea, setProductIdea] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<{doc_id: string, filename: string}[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [generatePhase, setGeneratePhase] = useState(0);
  const [traceLogs, setTraceLogs] = useState<ExecutionLogEntry[]>([]);
  const [traceRunning, setTraceRunning] = useState<TraceRunningState | null>(null);
  const [pipelinePaused, setPipelinePaused] = useState(false);
  const clarifyStartRef = useRef(0);
  const genFinalized = useRef(false);
  const prevGeneratePhase = useRef(0);

  const pipelineStates: AgentNodeState[] = useMemo(() => {
    const n = 7;
    const out: AgentNodeState[] = Array(n).fill("idle") as AgentNodeState[];
    if (step === 3) return Array(n).fill("completed") as AgentNodeState[];
    if (step === 2 && !loading) {
      out[0] = "completed";
      return out;
    }
    if (step === 2 && loading) {
      for (let i = 0; i < n; i++) {
        if (i < generatePhase) out[i] = "completed";
        else if (i === generatePhase) out[i] = "active";
        else out[i] = "idle";
      }
      return out;
    }
    if (step === 1 && loading) {
      out[0] = "active";
      return out;
    }
    return out;
  }, [step, loading, generatePhase]);

  const stage: AppStage = useMemo(() => {
    if (step === 3) return "output";
    if (step === 2 && loading) return "planning";
    if (step === 2) return "clarification";
    return "input";
  }, [step, loading]);

  const progressPct = useMemo(() => {
    if (step === 3) return 100;
    if (step === 2 && loading) return Math.min(95, 38 + generatePhase * 11);
    if (step === 2) return 42;
    if (step === 1 && loading) return 22;
    return 0;
  }, [step, loading, generatePhase]);

  const completedAgents = useMemo(
    () => pipelineStates.filter((s) => s === "completed").length,
    [pipelineStates],
  );

  const phaseName = useMemo(() => {
    if (step === 1 && loading) return "Clarification phase — live reasoning on your idea";
    if (step === 1) return "Input phase — describe what you want to build";
    if (step === 2 && loading) {
      const p = PIPELINE_TRACE[generatePhase];
      return p ? `${p.agent} — documentation pipeline` : "Planning phase";
    }
    if (step === 2) return "Clarification phase — answer follow-up questions";
    return "Output phase — review generated artifacts";
  }, [step, loading, generatePhase]);

  const miniSteps = useMemo(
    () =>
      PIPELINE_MINI_LABELS.map((label, i) => ({
        key: `p-${i}`,
        label,
        state:
          pipelineStates[i] === "completed"
            ? ("done" as const)
            : pipelineStates[i] === "active"
              ? ("active" as const)
              : ("pending" as const),
      })),
    [pipelineStates],
  );

  const appendLog = useCallback((entry: Omit<ExecutionLogEntry, "id" | "at">) => {
    setTraceLogs((prev) => [
      ...prev,
      { ...entry, id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, at: Date.now() },
    ]);
  }, []);

  useEffect(() => {
    if (!loading || step !== 2) {
      if (!loading) prevGeneratePhase.current = 0;
      return;
    }
    const p = PIPELINE_TRACE[generatePhase];
    if (p) {
      setTraceRunning({
        agent: p.agent,
        message: p.run,
        inputSummary: truncate(
          `${productIdea.slice(0, 72)}${Object.keys(answers).length ? ` · ${Object.keys(answers).length} answers` : ""}`,
          140,
        ),
      });
    }

    if (generatePhase > prevGeneratePhase.current) {
      const ctx = truncate(
        `${productIdea.slice(0, 72)}${Object.keys(answers).length ? ` · ${Object.keys(answers).length} answers` : ""}`,
        160,
      );
      for (let i = prevGeneratePhase.current; i < generatePhase; i++) {
        const done = PIPELINE_TRACE[i];
        appendLog({
          agent: done.agent,
          message: done.done,
          status: "completed",
          durationMs: 700 + i * 160,
          detail: done.detail,
          inputSummary: ctx,
          outputSummary: `Handoff: ${done.done}`,
        });
      }
      prevGeneratePhase.current = generatePhase;
    }
  }, [generatePhase, loading, step, appendLog, productIdea, answers]);

  useEffect(() => {
    if (step !== 3 || loading || genFinalized.current) return;
    const ctx = truncate(
      `${productIdea.slice(0, 80)} · ${Object.keys(answers).filter((k) => answers[k]?.trim()).length} answers`,
      160,
    );
    for (let i = prevGeneratePhase.current; i < PIPELINE_TRACE.length; i++) {
      const done = PIPELINE_TRACE[i];
      appendLog({
        agent: done.agent,
        message: done.done,
        status: "completed",
        durationMs: 500 + i * 120,
        detail: done.detail,
        inputSummary: ctx,
        outputSummary: `Completed: ${done.done}`,
      });
    }
    appendLog({
      agent: "Orchestrator",
      message: "All agents finished — artifacts ready",
      status: "completed",
      durationMs: 80,
      detail: "Sequential workflow complete.",
      inputSummary: truncate(productIdea, 140),
      outputSummary: "Documentation bundle ready for review",
    });
    setTraceRunning(null);
    prevGeneratePhase.current = 0;
    genFinalized.current = true;
  }, [step, loading, appendLog, productIdea, answers]);

  useEffect(() => {
    if (step !== 3) genFinalized.current = false;
  }, [step]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (e.target) e.target.value = '';
    
    setIsUploading(true);
    setError("");
    
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const base64Data = (event.target?.result as string).split(',')[1];
          const res = await fetch("/api/upload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: file.name,
              content_base64: base64Data,
              session_id: sessionId
            })
          });
          
          if (!res.ok) throw new Error(await parseError(res));
          
          const data = await res.json();
          setSessionId(data.session_id);
          setUploadedFiles(prev => [...prev, data.document]);
          appendLog({
            agent: "System",
            message: "Document uploaded",
            status: "completed",
            durationMs: 300,
            detail: `Indexed ${data.document.chunk_count} chunks from ${data.document.filename}`,
            inputSummary: truncate(data.document.filename, 100),
            outputSummary: "RAG index updated",
          });
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsDataURL(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsUploading(false);
    }
  };

  const handleGetQuestions = useCallback(async () => {
    setError("");
    const idea = productIdea.trim();
    if (!idea) {
      setError("Please enter a product idea.");
      return;
    }
    setLoading(true);
    clarifyStartRef.current = Date.now();
    setTraceRunning({
      agent: "Clarifier",
      message: "Analyzing your product idea and drafting questions…",
      inputSummary: truncate(productIdea, 120),
    });
    try {
      const res = await fetch("/api/questions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_idea: idea }),
      });
      if (!res.ok) throw new Error(await parseError(res));
      const data = await res.json();
      const qs = data.questions || [];
      setQuestions(qs);
      setAnswers({});
      setStep(2);
      const ms = Date.now() - clarifyStartRef.current;
      setTraceRunning(null);
      appendLog({
        agent: "Clarifier",
        message: "Clarification questions ready",
        status: "completed",
        durationMs: ms,
        detail: `${qs.length} question(s) generated.`,
        inputSummary: truncate(productIdea, 160),
        outputSummary: `Generated ${qs.length} clarification questions`,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setTraceRunning(null);
    } finally {
      setLoading(false);
    }
  }, [productIdea, appendLog]);

  const handleGenerate = useCallback(async () => {
    setError("");
    setLoading(true);
    setPipelinePaused(false);
    prevGeneratePhase.current = 0;
    setGeneratePhase(0);
    const ctx = truncate(
      `${productIdea.slice(0, 80)} · ${Object.keys(answers).filter((k) => answers[k]?.trim()).length} answers`,
      140,
    );
    setTraceRunning({
      agent: "Orchestrator",
      message: "Starting sequential agent pipeline…",
      inputSummary: ctx,
    });
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_idea: productIdea.trim(), answers, questions, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(await parseError(res));
      const data = await res.json();
      if (data.error) {
        const base = String(data.error).trim();
        const details = Array.isArray(data.validation_errors)
          ? Array.from(
              new Set(
                data.validation_errors
                  .map((item: unknown) => String(item ?? "").trim())
                  .filter(Boolean)
                  .filter((msg: string) => msg !== base),
              ),
            )
          : [];
        const message = details.length ? `${base} ${details.join("; ")}` : base;
        setError(message);
        setTraceRunning(null);
        return;
      }
      setResults(data);
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setTraceRunning(null);
    } finally {
      setLoading(false);
      setGeneratePhase(0);
    }
  }, [productIdea, answers, questions]);

  const downloadJson = useCallback(() => {
    if (!results) return;
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "project_documentation.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [results]);

  const downloadMarkdown = useCallback(() => {
    if (!results) return;
    let md = "# Project documentation\n\n_Generated by TaskWeave AI_\n\n";
    for (const [key, value] of Object.entries(results)) {
      const title = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      const body =
        typeof value === "string" ? value : JSON.stringify(value as object, null, 2);
      md += `## ${title}\n\n\`\`\`\n${body}\n\`\`\`\n\n`;
    }
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "project_documentation.md";
    a.click();
    URL.revokeObjectURL(url);
  }, [results]);

  const restart = useCallback(() => {
    setStep(1);
    setProductIdea("");
    setQuestions([]);
    setAnswers({});
    setResults(null);
    setSessionId(null);
    setUploadedFiles([]);
    setError("");
    setTraceLogs([]);
    setTraceRunning(null);
    setPipelinePaused(false);
    prevGeneratePhase.current = 0;
    setGeneratePhase(0);
  }, []);

  const applySuggestion = useCallback((text: string) => {
    setProductIdea((prev) => (prev.trim() ? `${prev.trim()}\n\n${text}` : text));
  }, []);

  useEffect(() => {
    let mounted = true;

    const checkBackendHealth = async () => {
      try {
        const res = await fetch("/api/health");
        if (!mounted) return;
        setBackendOnline(res.ok);
      } catch {
        if (!mounted) return;
        setBackendOnline(false);
      }
    };

    void checkBackendHealth();
    const interval = window.setInterval(() => {
      void checkBackendHealth();
    }, 5000);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.key !== "Enter") return;
      e.preventDefault();
      if (loading) return;
      if (step === 1) void handleGetQuestions();
      if (step === 2) void handleGenerate();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, loading, handleGetQuestions, handleGenerate]);

  const modKey = typeof navigator !== "undefined" && /Mac|iPhone/.test(navigator.platform) ? "⌘" : "Ctrl";

  return (
    <div className="relative flex min-h-screen flex-col">
      <div className="pointer-events-none fixed inset-0 grid-bg-animated opacity-40" aria-hidden />
      <CursorGlow />

      <TerminalHeader backendOnline={backendOnline} />

      <div className="relative z-10 w-full flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
        <div className="flex min-w-0 flex-1 flex-col gap-8">
          <PipelineFlow states={pipelineStates} />

          {(productIdea.trim().length > 0 || step >= 2) && (
            <UserContextPanel
              productIdea={productIdea}
              questions={questions}
              answers={answers}
            />
          )}

          <div className="w-full flex-1 space-y-8">
            {loading && step === 1 && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              >
                <ClarificationThinkingFeed active />
              </motion.div>
            )}

            {loading && step === 2 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden rounded-2xl border border-white/[0.09] bg-card/38 shadow-[0_12px_40px_-20px_rgba(0,0,0,0.5)] backdrop-blur-xl"
              >
                <AgentProgress
                  onPhaseChange={setGeneratePhase}
                  paused={pipelinePaused}
                />
              </motion.div>
            )}

            <AnimatePresence mode="wait">
              {step === 1 && !loading && (
                <motion.div key="step1" {...pageTransition} className="space-y-6">
                  <div className="overflow-hidden rounded-2xl border border-white/[0.1] bg-card/42 shadow-[0_8px_40px_-18px_rgba(0,0,0,0.45)] backdrop-blur-xl">
                    <div className="border-b border-white/[0.06] px-5 py-3.5 sm:px-8">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/40 opacity-50" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                          </span>
                          <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                            Product input
                          </span>
                        </div>
                        <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
                          <Command className="h-3 w-3 opacity-70" />
                          <span>
                            {modKey} + Enter to run
                          </span>
                        </span>
                      </div>
                    </div>
                    <div className="space-y-4 p-5 sm:p-8">
                      <label htmlFor="idea" className="block text-sm font-semibold text-[#E5E7EB]">
                        Describe your product
                      </label>
                      <div
                        className="rounded-2xl border border-white/[0.1] bg-black/18 p-1 shadow-[inset_0_1px_8px_rgba(0,0,0,0.28)] transition-[box-shadow,border-color] duration-300 focus-within:border-primary/40 focus-within:shadow-[inset_0_1px_8px_rgba(0,0,0,0.28),0_0_0_1px_hsla(160,72%,45%,0.2)]"
                      >
                        <Textarea
                          id="idea"
                          rows={12}
                          value={productIdea}
                          onChange={(e) => setProductIdea(e.target.value)}
                          placeholder="Example: A B2B marketplace connecting verified freelancers with teams, with escrow, real-time chat, and milestone-based payouts…"
                          className="min-h-[260px] resize-y border-0 bg-transparent px-4 py-3 text-[15px] leading-relaxed text-[#E5E7EB]/95 placeholder:text-muted-foreground/50 focus-visible:ring-0"
                        />
                        <div className="flex items-center gap-2 px-3 pb-2 pt-1 border-t border-white/[0.05]">
                          <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt" />
                          <Button type="button" variant="ghost" size="sm" onClick={() => fileInputRef.current?.click()} disabled={isUploading || loading} className="h-8 gap-1.5 px-2 text-muted-foreground hover:text-foreground">
                            {isUploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Paperclip className="h-3.5 w-3.5" />}
                            <span className="text-xs">{isUploading ? 'Uploading...' : 'Attach PDF/TXT Context'}</span>
                          </Button>
                          <div className="flex flex-wrap gap-1.5 overflow-hidden flex-1">
                            {uploadedFiles.map(f => (
                              <div key={f.doc_id} className="flex items-center gap-1 max-w-[150px] rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-muted-foreground border border-white/[0.04]">
                                <span className="truncate">{f.filename}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="mr-1 w-full text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground sm:w-auto sm:mr-2">
                          Suggestions
                        </span>
                        {SUGGESTIONS.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => applySuggestion(s)}
                            className="rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-[12px] text-[#E5E7EB]/85 transition-all duration-300 hover:border-primary/35 hover:bg-primary/[0.08] hover:text-primary"
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                      <div className="flex flex-wrap items-center gap-3 pt-1">
                        <Button
                          onClick={() => void handleGetQuestions()}
                          size="lg"
                          className="rounded-xl px-6 font-semibold shadow-md shadow-primary/10 transition-transform duration-200 hover:scale-[1.02]"
                        >
                          <Send className="h-4 w-4" />
                          Run clarifier
                        </Button>
                        {error && (
                          <p className="text-sm text-destructive">{error}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {step === 2 && !loading && (
                <motion.div key="step2" {...pageTransition} className="space-y-6">
                  <div className="overflow-hidden rounded-2xl border border-white/[0.1] bg-card/40 backdrop-blur-xl">
                    <div className="border-b border-white/[0.06] px-5 py-3.5 sm:px-8">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                          Clarification · {questions.length} questions
                        </span>
                        <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
                          <Command className="h-3 w-3 opacity-70" />
                          {modKey} + Enter to generate
                        </span>
                      </div>
                    </div>
                    <div className="p-5 sm:p-8">
                      <ChatBlock
                        questions={questions}
                        answers={answers}
                        onAnswerChange={(key, v) =>
                          setAnswers((prev) => ({ ...prev, [key]: v }))
                        }
                      />
                      <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/[0.06] pt-6">
                        <Button
                          onClick={() => void handleGenerate()}
                          size="lg"
                          className="rounded-xl px-6 font-semibold shadow-md shadow-primary/10 transition-transform duration-200 hover:scale-[1.02]"
                        >
                          <Sparkles className="h-4 w-4" />
                          Generate documentation
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => setStep(1)}
                          className="gap-2 text-muted-foreground hover:text-foreground"
                        >
                          <ArrowLeft className="h-4 w-4" />
                          Back
                        </Button>
                        {error && <p className="w-full text-sm text-destructive">{error}</p>}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {step === 3 && !loading && results && (
                <motion.div key="step3" {...pageTransition} className="space-y-6">
                  <div className="overflow-hidden rounded-2xl border border-white/[0.1] bg-card/40 p-5 shadow-md backdrop-blur-xl sm:p-8">
                    <div className="mb-6">
                      <h2 className="text-lg font-semibold tracking-tight text-[#E5E7EB]">
                        Artifacts
                      </h2>
                      <p className="mt-1 text-sm text-muted-foreground/95">
                        Every section was produced by a specialized agent. Open a card to review or export.
                      </p>
                    </div>
                    <ResultsViewer results={results} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <WhatsNext step={step} loading={loading} generatePhase={generatePhase} />
          </div>
        </div>

        <div className="w-full shrink-0 lg:sticky lg:top-24 lg:flex lg:h-[calc(100vh-7rem)] lg:w-[min(100%,360px)] lg:flex-col lg:self-start lg:overflow-hidden">
          <StatusBar
            stage={stage}
            progress={progressPct}
            agentsOnline={backendOnline ? 7 : 0}
            phaseName={phaseName}
            completedAgents={completedAgents}
            totalAgents={7}
            miniSteps={miniSteps}
            className="sm:flex-col sm:items-stretch sm:justify-start"
          />
          <LogPanel
            entries={traceLogs}
            running={traceRunning}
            className="mt-4 w-full min-h-0 lg:flex-1"
          />
        </div>
        </div>
      </div>

      <FloatingActions
        showExportJson={step === 3 && !!results}
        showExportMarkdown={step === 3 && !!results}
        onExportJson={downloadJson}
        onExportMarkdown={downloadMarkdown}
        onReset={step > 1 ? restart : undefined}
        showPause={loading && step === 2}
        pauseActive={pipelinePaused}
        onPauseToggle={() => setPipelinePaused((p) => !p)}
      />

      <footer className="relative z-10 border-t border-white/[0.06] py-5">
        <p className="text-center text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground/55">
          Multi-agent orchestration · {modKey} + Enter to run
        </p>
      </footer>
    </div>
  );
}
