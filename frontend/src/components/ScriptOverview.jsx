import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ScrollText,
  Mic,
  BookOpen,
  Share2,
  Printer,
  Sparkles,
  Layers,
  Zap,
  AlertTriangle,
  RotateCcw,
  Loader2,
} from "lucide-react";
import BreakdownView from "@/components/BreakdownView";

export default function ScriptOverview({
  scriptData,
  ttsAvailable,
  onNewAnalysis,
  onRetryScene,
  onOpenMemorization,
  onOpenSceneReader,
  onExportPdf,
  onShare,
  onRegenerate,
  onReanalyzeDeep,
  onAdjusted,
  onSelectBreakdown,
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [retrying, setRetrying] = useState(false);

  if (!scriptData || !scriptData.breakdowns?.length) return null;

  const { breakdowns, character_name, mode, prepMode, costSummary } = scriptData;
  const activeBreakdown = breakdowns[activeIndex];
  const isDeep = mode === "deep";
  const isFailed = (b) => b?.id?.toString().startsWith("failed-");

  // Adaptive tool visibility based on prep mode
  const showRunLines = prepMode !== "silent";
  const showMemorize = prepMode !== "silent";
  // Tool order: booked role leads with Memorize
  const memorizeFirst = prepMode === "booked";

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
            {breakdowns.map((b, i) => {
              const failed = isFailed(b);
              return (
                <button
                  key={b.id}
                  data-testid={`script-scene-tab-${i}`}
                  onClick={() => setActiveIndex(i)}
                  className={`shrink-0 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    failed
                      ? i === activeIndex
                        ? "bg-red-500/10 text-red-400 border border-red-500/30"
                        : "text-red-500/50 hover:text-red-400 border border-transparent hover:border-red-500/20"
                      : i === activeIndex
                      ? "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                      : "text-zinc-500 hover:text-zinc-300 border border-transparent hover:border-zinc-800"
                  }`}
                >
                  <span className="font-mono mr-1">#{b.scene_number || i + 1}</span>
                  {failed && <AlertTriangle className="w-3 h-3 inline ml-0.5" />}
                  <span className="hidden sm:inline">
                    {failed ? "Failed" : (b.scene_heading || b.character_name || `Scene ${i + 1}`).slice(0, 25)}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Cost summary */}
          {costSummary && costSummary.total > 0 && (
            <div data-testid="cost-summary-bar" className="flex items-center gap-2 text-[11px] text-zinc-500 pt-1.5">
              <Zap className="w-3 h-3 text-zinc-600" />
              <span>{costSummary.total} scene{costSummary.total !== 1 ? 's' : ''}</span>
              <span className="text-zinc-700">·</span>
              {costSummary.cached > 0 && (
                <>
                  <span className="text-emerald-500/70">
                    {Math.round((costSummary.cached / costSummary.total) * 100)}% from cache
                  </span>
                  <span className="text-zinc-700">·</span>
                </>
              )}
              <span>Est. ${costSummary.estimatedCost.toFixed(2)}</span>
            </div>
          )}
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

      {/* Booked Role: Lines First hero card */}
      {prepMode === "booked" && !isFailed(activeBreakdown) && activeBreakdown.memorization?.cue_recall?.length > 0 && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-4" data-testid="lines-first-card">
          <div className="border border-amber-500/20 bg-amber-500/5 rounded-xl p-4 flex items-center gap-4">
            <div className="shrink-0 w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-amber-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-zinc-200">
                {activeBreakdown.memorization.cue_recall.length} line{activeBreakdown.memorization.cue_recall.length !== 1 ? "s" : ""} in this scene
              </p>
              <p className="text-xs text-zinc-500 mt-0.5">Jump straight to your lines</p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button
                data-testid="lines-first-memorize"
                size="sm"
                onClick={() => onOpenMemorization?.(activeBreakdown)}
                className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-8 gap-1.5"
              >
                <BookOpen className="w-3.5 h-3.5" />
                Memorize
              </Button>
              {ttsAvailable && (
                <Button
                  data-testid="lines-first-run-lines"
                  size="sm"
                  variant="outline"
                  onClick={() => onOpenSceneReader?.(activeBreakdown)}
                  className="border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 text-xs h-8 gap-1.5"
                >
                  <Mic className="w-3.5 h-3.5" />
                  Run Lines
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Per-scene action bar — hidden for failed scenes */}
      {!isFailed(activeBreakdown) && (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-3 pb-1">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1" data-testid="scene-action-bar">
          {/* Memorize — shown first for booked role */}
          {memorizeFirst && showMemorize && onOpenMemorization && activeBreakdown.memorization && (
            <Button
              data-testid="scene-action-memorize"
              variant="outline"
              size="sm"
              onClick={() => onOpenMemorization?.(activeBreakdown)}
              className="shrink-0 border-amber-500/20 text-amber-500 hover:bg-amber-500/10 hover:text-amber-400 gap-1.5 text-xs h-8"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Memorize
            </Button>
          )}

          {/* Run Lines */}
          {showRunLines && ttsAvailable && onOpenSceneReader && activeBreakdown.memorization?.cue_recall?.length > 0 && (
            <Button
              data-testid="scene-action-run-lines"
              variant="outline"
              size="sm"
              onClick={() => onOpenSceneReader?.(activeBreakdown)}
              className="shrink-0 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 gap-1.5 text-xs h-8"
            >
              <Mic className="w-3.5 h-3.5" />
              Run Lines
            </Button>
          )}

          {/* Memorize — shown second for non-booked modes */}
          {!memorizeFirst && showMemorize && onOpenMemorization && activeBreakdown.memorization && (
            <Button
              data-testid="scene-action-memorize"
              variant="outline"
              size="sm"
              onClick={() => onOpenMemorization?.(activeBreakdown)}
              className="shrink-0 border-amber-500/20 text-amber-500 hover:bg-amber-500/10 hover:text-amber-400 gap-1.5 text-xs h-8"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Memorize
            </Button>
          )}

          {/* Go Deeper — only on Quick breakdowns */}
          {activeBreakdown.mode === "quick" && onReanalyzeDeep && (
            <Button
              data-testid="scene-action-go-deeper"
              variant="outline"
              size="sm"
              onClick={() => onReanalyzeDeep?.(activeBreakdown)}
              className="shrink-0 border-amber-500/20 text-amber-500/70 hover:bg-amber-500/10 hover:text-amber-400 gap-1.5 text-xs h-8"
            >
              <Layers className="w-3.5 h-3.5" />
              Go Deeper
            </Button>
          )}

          <div className="flex-1" />

          {/* Share */}
          {onShare && (
            <Button
              data-testid="scene-action-share"
              variant="ghost"
              size="sm"
              onClick={() => onShare?.(activeBreakdown.id)}
              className="shrink-0 text-zinc-500 hover:text-zinc-300 gap-1.5 text-xs h-8"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Share</span>
            </Button>
          )}

          {/* Print/Export */}
          {onExportPdf && (
            <Button
              data-testid="scene-action-export"
              variant="ghost"
              size="sm"
              onClick={() => onExportPdf?.(activeBreakdown.id)}
              className="shrink-0 text-zinc-500 hover:text-zinc-300 gap-1.5 text-xs h-8"
            >
              <Printer className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">PDF</span>
            </Button>
          )}
        </div>
      </div>
      )}

      {/* Active breakdown or failed scene retry card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeBreakdown.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.25 }}
        >
          {isFailed(activeBreakdown) ? (
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8" data-testid="failed-scene-card">
              <div className="border border-red-500/20 bg-red-500/5 rounded-xl p-6 text-center space-y-4">
                <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
                <div>
                  <h3 className="text-base font-semibold text-zinc-200 mb-1">
                    Scene #{activeBreakdown.scene_number} — Analysis Failed
                  </h3>
                  <p className="text-sm text-zinc-400 max-w-md mx-auto">
                    {activeBreakdown.error_msg || "An unexpected error occurred during analysis."}
                  </p>
                </div>

                {activeBreakdown.error_type && (
                  <span className="inline-block px-2.5 py-1 rounded-full text-[11px] font-medium border border-red-500/20 text-red-400 bg-red-500/5">
                    {activeBreakdown.error_type === "network_error" && "Network / Proxy Timeout"}
                    {activeBreakdown.error_type === "service_unavailable" && "LLM Service Unavailable"}
                    {activeBreakdown.error_type === "timeout" && "Analysis Timed Out"}
                    {activeBreakdown.error_type === "budget_exceeded" && "Budget Exceeded"}
                    {activeBreakdown.error_type === "rate_limited" && "Rate Limited"}
                    {activeBreakdown.error_type === "backend_error" && "Backend Error"}
                    {!["network_error", "service_unavailable", "timeout", "budget_exceeded", "rate_limited", "backend_error"].includes(activeBreakdown.error_type) && "Error"}
                  </span>
                )}

                {onRetryScene && (
                  <div>
                    <Button
                      data-testid="retry-scene-button"
                      onClick={async () => {
                        setRetrying(true);
                        await onRetryScene(activeBreakdown);
                        setRetrying(false);
                      }}
                      disabled={retrying}
                      className="bg-amber-500 hover:bg-amber-600 text-black font-bold px-6 h-10 rounded-lg gap-2"
                    >
                      {retrying ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Retrying...
                        </>
                      ) : (
                        <>
                          <RotateCcw className="w-4 h-4" />
                          Retry This Scene
                        </>
                      )}
                    </Button>
                  </div>
                )}

                {activeBreakdown.original_text && (
                  <details className="text-left mt-4 cursor-pointer">
                    <summary className="text-xs text-zinc-500 hover:text-zinc-400 transition-colors">
                      Show scene text ({activeBreakdown.original_text.length} chars)
                    </summary>
                    <pre className="mt-2 text-xs text-zinc-600 whitespace-pre-wrap max-h-40 overflow-y-auto bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                      {activeBreakdown.original_text.slice(0, 2000)}
                      {activeBreakdown.original_text.length > 2000 && "\n..."}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ) : (
            <BreakdownView
              breakdown={activeBreakdown}
              prepMode={prepMode}
              onRegenerate={() => onRegenerate?.(activeBreakdown.id)}
              onReanalyzeDeep={() => onReanalyzeDeep?.(activeBreakdown)}
              onAdjusted={onAdjusted}
              onExportPdf={() => onExportPdf?.(activeBreakdown.id)}
              onNewAnalysis={onNewAnalysis}
              onOpenMemorization={() => onOpenMemorization?.(activeBreakdown)}
              onOpenSceneReader={() => onOpenSceneReader?.(activeBreakdown)}
              onShare={() => onShare?.(activeBreakdown.id)}
              ttsAvailable={ttsAvailable}
              isShareView={false}
              hideHeader={true}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Footer signature */}
      <p className="text-center text-[10px] text-zinc-700/50 pb-4 pt-2">
        Co-produced by DangerLou Media
      </p>
    </div>
  );
}
