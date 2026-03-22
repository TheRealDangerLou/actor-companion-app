import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Loader2, SlidersHorizontal, X, Check } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ADJUSTMENTS = [
  { id: "tighten_pacing", label: "Tighten pacing", icon: "~" },
  { id: "emotional_depth", label: "Add depth", icon: "+" },
  { id: "more_natural", label: "More natural", icon: "=" },
  { id: "raise_stakes", label: "Raise stakes", icon: "^" },
  { id: "play_opposite", label: "Play the opposite", icon: "<>" },
];

export default function AdjustmentPanel({
  breakdownId,
  onAdjusted,
  variant = "inline", // "inline" | "post-action"
  onDismiss,
}) {
  const [selected, setSelected] = useState(new Set());
  const [isAdjusting, setIsAdjusting] = useState(false);
  const [appliedStack, setAppliedStack] = useState([]);

  const toggle = useCallback((id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleApply = useCallback(async () => {
    if (selected.size === 0 || !breakdownId) return;

    const adjustments = [...appliedStack, ...Array.from(selected)];
    setIsAdjusting(true);

    try {
      const response = await axios.post(
        `${API}/adjust-takes/${breakdownId}`,
        { adjustments },
        { timeout: 60000 }
      );
      setAppliedStack(adjustments);
      setSelected(new Set());
      onAdjusted?.(response.data);
      toast.success("Takes adjusted — check the new direction.");
    } catch (err) {
      const msg = err.response?.data?.detail || "Adjustment failed. Try again.";
      toast.error(msg);
    }
    setIsAdjusting(false);
  }, [selected, appliedStack, breakdownId, onAdjusted]);

  const isPostAction = variant === "post-action";

  return (
    <motion.div
      data-testid="adjustment-panel"
      initial={{ opacity: 0, y: isPostAction ? -12 : 0 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: isPostAction ? -12 : 0 }}
      transition={{ duration: 0.25 }}
      className={
        isPostAction
          ? "bg-zinc-900/95 border border-zinc-800 rounded-xl p-4 shadow-xl backdrop-blur-sm"
          : "mt-4 pt-3 border-t border-zinc-800/50"
      }
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-xs font-medium text-zinc-400">
            {isPostAction ? "Want to adjust?" : "Adjust takes"}
          </span>
          {appliedStack.length > 0 && (
            <span className="text-[10px] text-amber-500/60 ml-1">
              {appliedStack.length} applied
            </span>
          )}
        </div>
        {isPostAction && onDismiss && (
          <button
            data-testid="adjustment-dismiss"
            onClick={onDismiss}
            className="text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Adjustment chips */}
      <div className="flex flex-wrap gap-1.5 mb-3" data-testid="adjustment-chips">
        {ADJUSTMENTS.map((adj) => {
          const isActive = selected.has(adj.id);
          const wasApplied = appliedStack.includes(adj.id);

          return (
            <button
              key={adj.id}
              data-testid={`adjustment-${adj.id}`}
              onClick={() => !wasApplied && toggle(adj.id)}
              disabled={wasApplied || isAdjusting}
              className={`text-xs px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 ${
                wasApplied
                  ? "border-zinc-800 bg-zinc-900/30 text-zinc-600 cursor-default"
                  : isActive
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-500"
                  : "border-zinc-800 bg-zinc-900/30 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300"
              } disabled:opacity-40`}
            >
              {wasApplied && <Check className="w-2.5 h-2.5" />}
              {adj.label}
            </button>
          );
        })}
      </div>

      {/* Apply button */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Button
              data-testid="adjustment-apply"
              onClick={handleApply}
              disabled={isAdjusting}
              size="sm"
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold text-xs h-8 btn-press disabled:opacity-50 gap-1.5"
            >
              {isAdjusting ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Adjusting...
                </>
              ) : (
                <>
                  Apply {selected.size} adjustment{selected.size > 1 ? "s" : ""}
                </>
              )}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
