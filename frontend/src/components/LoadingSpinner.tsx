import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

export function LoadingSpinner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center gap-4 py-12"
    >
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
      <p className="text-muted-foreground text-sm font-medium">
        Running agents… this may take a minute.
      </p>
    </motion.div>
  );
}
