import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

const steps = [
  { label: "INPUT", number: 1 },
  { label: "CLARIFY", number: 2 },
  { label: "OUTPUT", number: 3 },
];

interface StepIndicatorProps {
  currentStep: number;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-0 mb-6">
      {steps.map((step, i) => (
        <div key={step.number} className="flex items-center">
          <div className="flex flex-col items-center gap-1.5">
            <motion.div
              animate={{
                boxShadow:
                  currentStep === step.number
                    ? "0 0 12px hsla(160, 100%, 50%, 0.4)"
                    : "none",
              }}
              className={cn(
                "w-8 h-8 rounded-md flex items-center justify-center font-mono text-xs font-bold transition-all duration-300 border",
                currentStep > step.number
                  ? "bg-primary/20 border-primary/40 text-primary"
                  : currentStep === step.number
                  ? "bg-primary/10 border-primary text-primary"
                  : "bg-muted/30 border-border text-muted-foreground"
              )}
            >
              {currentStep > step.number ? "✓" : step.number}
            </motion.div>
            <span
              className={cn(
                "font-mono text-[9px] tracking-[0.2em] uppercase transition-colors",
                currentStep >= step.number
                  ? "text-primary"
                  : "text-muted-foreground/50"
              )}
            >
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={cn(
                "w-12 h-px mx-2 mb-5 transition-colors duration-500",
                currentStep > step.number ? "bg-primary/50" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
