import { useState } from "react";
import { motion } from "framer-motion";
import { Copy, Download, Eye, FileText } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AgentBadge } from "@/components/AgentBadge";

interface ArtifactCardProps {
  title: string;
  description: string;
  agentKey: string;
  content: string;
  index: number;
}

export function ArtifactCard({ title, description, agentKey, content, index }: ArtifactCardProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const exportArtifact = () => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_").toLowerCase()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("File exported");
  };

  return (
    <>
      <motion.article
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
        className={cn(
          "group relative flex flex-col rounded-2xl border border-white/[0.09] bg-card/40 p-5 sm:p-6 shadow-sm backdrop-blur-xl transition-all duration-300 ease-out",
          "hover:-translate-y-1 hover:border-primary/22 hover:shadow-[0_10px_36px_-18px_rgba(0,0,0,0.55)]",
        )}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04]">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h3 className="text-[17px] font-semibold tracking-tight text-[#E5E7EB]">{title}</h3>
              <p className="mt-1.5 line-clamp-3 text-[14px] leading-relaxed text-muted-foreground/95">{description}</p>
            </div>
          </div>
        </div>
        <div className="mb-4">
          <AgentBadge agent={agentKey} pulse={false} className="rounded-md border border-white/[0.06] bg-white/[0.03] px-2 py-1" />
        </div>
        <div className="mt-auto flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="h-8 text-[13px] transition-transform duration-200 hover:scale-[1.02]"
            onClick={() => setOpen(true)}
          >
            <Eye className="h-3.5 w-3.5" />
            View
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 text-[13px] text-muted-foreground hover:text-foreground"
            onClick={exportArtifact}
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </Button>
        </div>
      </motion.article>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-hidden border-white/[0.1] bg-[hsl(222,28%,8%)] p-0 shadow-2xl">
          <DialogHeader className="border-b border-white/[0.08] px-6 py-4">
            <DialogTitle className="text-left text-[17px] font-semibold text-[#E5E7EB]">{title}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[65vh] overflow-auto px-6 py-4">
            <pre className="whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-muted-foreground">
              {content}
            </pre>
          </div>
          <div className="flex justify-end gap-2 border-t border-white/[0.08] px-6 py-3">
            <Button variant="secondary" size="sm" onClick={copy}>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </Button>
            <Button size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
