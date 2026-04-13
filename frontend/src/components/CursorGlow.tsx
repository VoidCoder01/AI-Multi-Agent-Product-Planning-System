import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** Subtle radial highlight following the pointer — premium, low-opacity. */
export function CursorGlow({ className }: { className?: string }) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setPos({ x: e.clientX, y: e.clientY });
      setVisible(true);
    };
    const onLeave = () => setVisible(false);
    window.addEventListener("mousemove", onMove);
    document.body.addEventListener("mouseleave", onLeave);
    return () => {
      window.removeEventListener("mousemove", onMove);
      document.body.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-0 z-[5] overflow-hidden transition-opacity duration-500",
        visible ? "opacity-100" : "opacity-0",
        className,
      )}
      aria-hidden
    >
      <div
        className="absolute h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle_at_center,hsla(160,84%,45%,0.07)_0%,transparent_68%)] blur-2xl"
        style={{ left: pos.x, top: pos.y }}
      />
    </div>
  );
}
