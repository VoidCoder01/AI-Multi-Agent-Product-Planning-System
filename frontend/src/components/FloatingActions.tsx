import { motion } from "framer-motion";
import { Download, FileCode2, Pause, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface FloatingActionsProps {
  onExportJson?: () => void;
  onExportMarkdown?: () => void;
  onReset?: () => void;
  showExportJson?: boolean;
  showExportMarkdown?: boolean;
  onPauseToggle?: () => void;
  pauseActive?: boolean;
  showPause?: boolean;
  className?: string;
}

export function FloatingActions({
  onExportJson,
  onExportMarkdown,
  onReset,
  showExportJson = true,
  showExportMarkdown = true,
  onPauseToggle,
  pauseActive = false,
  showPause = false,
  className,
}: FloatingActionsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn("fixed bottom-6 right-6 z-40 flex flex-col items-end gap-2", className)}
    >
      {showExportJson && onExportJson && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="lg"
              className="h-12 rounded-full px-5 shadow-md shadow-primary/12 transition-transform duration-200 hover:scale-[1.02]"
              onClick={onExportJson}
            >
              <Download className="h-4 w-4" />
              JSON
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" className="text-xs">
            Download project_documentation.json
          </TooltipContent>
        </Tooltip>
      )}
      {showExportMarkdown && onExportMarkdown && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="secondary"
              size="lg"
              className="h-11 rounded-full border border-white/[0.1] bg-card/85 px-4 shadow-md backdrop-blur-md transition-transform duration-200 hover:scale-[1.02]"
              onClick={onExportMarkdown}
            >
              <FileCode2 className="h-4 w-4" />
              Markdown
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" className="text-xs">
            Export as a single .md file
          </TooltipContent>
        </Tooltip>
      )}
      {showPause && onPauseToggle && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="secondary"
              size="icon"
              className={cn(
                "h-11 w-11 rounded-full border border-white/[0.1] bg-card/85 shadow-md backdrop-blur-md transition-transform duration-200 hover:scale-[1.03]",
                pauseActive && "border-amber-500/35 bg-amber-500/10",
              )}
              onClick={onPauseToggle}
              aria-label={pauseActive ? "Resume" : "Pause"}
            >
              {pauseActive ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" className="max-w-[200px] text-xs">
            {pauseActive
              ? "Resume simulated phases (API call continues in background)"
              : "Pause simulated phase UI (does not cancel the server request)"}
          </TooltipContent>
        </Tooltip>
      )}
      {onReset && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="secondary"
              size="icon"
              className="h-11 w-11 rounded-full border border-white/[0.1] bg-card/80 shadow-md backdrop-blur-md transition-transform duration-200 hover:scale-[1.03]"
              onClick={onReset}
              aria-label="Reset session"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" className="text-xs">
            Start over
          </TooltipContent>
        </Tooltip>
      )}
    </motion.div>
  );
}
