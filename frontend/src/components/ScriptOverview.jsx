import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ScrollText,
  Layers,
  Mic,
  BookOpen,
  Share2,
  Download,
  Printer,
} from "lucide-react";
import BreakdownView from "@/components/BreakdownView";

export default function ScriptOverview({
  scriptData,
  ttsAvailable,
  onNewAnalysis,
  onOpenMemorization,
  onOpenSceneReader,
  onExportPdf,
  onShare,
  onRegenerate,
  onReanalyzeDeep,
  onSelectBreakdown,
}) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!scriptData || !scriptData.breakdowns?.length) return null;

  const { breakdowns, character_name, mode } = scriptData;
  const activeBreakdown = breakdowns[activeIndex];
  const isDeep = mode === "deep";

  return (
    <div data-testid="script-overview" className="min-h-screen bg-[#09090b]">
      {/* Script Navigation Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3">
          {/* Top row: back + title */}
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                data-testid="script-back-button"
                variant="ghost"
                size="sm"
                onClick={onNewAnalysis}
                className="text-zinc-400 hover:text-white shrink-0"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">New</span>
              </Button>
              <div className="flex items-center gap-2 min-w-0">
                <ScrollText className="w-4 h-4 text-amber-500 shrink-0" />
                <h1 className="font-display text-lg font-bold text-white truncate">
                  {character_name} — Full Script
                </h1>
              </div>
              {isDeep && (
                <Badge className="bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] shrink-0">
                  DEEP
                </Badge>
              )}
            </div>
          </div>

          {/* Scene tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1 no-scrollbar">
            {breakdowns.map((b, i) => (
              <button
                key={b.id}
                data-testid={`script-scene-tab-${i}`}
                onClick={() => setActiveIndex(i)}
                className={`shrink-0 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  i === activeIndex
                    ? "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                    : "text-zinc-500 hover:text-zinc-300 border border-transparent hover:border-zinc-800"
                }`}
              >
                <span className="font-mono mr-1">#{b.scene_number || i + 1}</span>
                <span className="hidden sm:inline">
                  {(b.scene_heading || b.character_name || `Scene ${i + 1}`).slice(0, 25)}
                </span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Scene navigation arrows + counter */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-4 flex items-center justify-between">
        <Button
          data-testid="script-prev-scene"
          variant="ghost"
          size="sm"
          disabled={activeIndex === 0}
          onClick={() => setActiveIndex(i => Math.max(0, i - 1))}
          className="text-zinc-400 hover:text-white disabled:opacity-20 gap-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Prev
        </Button>
        <span className="text-xs text-zinc-500 tabular-nums">
          Scene {activeIndex + 1} of {breakdowns.length}
        </span>
        <Button
          data-testid="script-next-scene"
          variant="ghost"
          size="sm"
          disabled={activeIndex === breakdowns.length - 1}
          onClick={() => setActiveIndex(i => Math.min(breakdowns.length - 1, i + 1))}
          className="text-zinc-400 hover:text-white disabled:opacity-20 gap-1"
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>

      {/* Scene heading banner */}
      {activeBreakdown.scene_heading && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-2">
          <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider">
            {activeBreakdown.scene_heading}
          </p>
        </div>
      )}

      {/* Active breakdown */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeBreakdown.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.25 }}
        >
          <BreakdownView
            breakdown={activeBreakdown}
            onRegenerate={() => onRegenerate?.(activeBreakdown.id)}
            onReanalyzeDeep={() => onReanalyzeDeep?.(activeBreakdown)}
            onExportPdf={() => onExportPdf?.(activeBreakdown.id)}
            onNewAnalysis={onNewAnalysis}
            onOpenMemorization={() => onOpenMemorization?.(activeBreakdown)}
            onOpenSceneReader={() => onOpenSceneReader?.(activeBreakdown)}
            onShare={() => onShare?.(activeBreakdown.id)}
            ttsAvailable={ttsAvailable}
            isShareView={false}
            hideHeader={true}
          />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
