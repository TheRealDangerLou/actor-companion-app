import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  X, Eye, EyeOff, ChevronRight, ChevronLeft, BookOpen,
  Maximize2, Minimize2, Zap, Check, RotateCcw
} from "lucide-react";

function useWakeLock() {
  const wakeLockRef = useRef(null);
  const request = useCallback(async () => {
    try {
      if ("wakeLock" in navigator) {
        wakeLockRef.current = await navigator.wakeLock.request("screen");
      }
    } catch (e) { /* non-critical */ }
  }, []);
  const release = useCallback(() => {
    wakeLockRef.current?.release().catch(() => {});
    wakeLockRef.current = null;
  }, []);
  useEffect(() => { request(); return release; }, [request, release]);
}

export default function MemorizationMode({ memorization, characterName, onClose }) {
  const [tab, setTab] = useState("linerun");
  const [currentChunk, setCurrentChunk] = useState(0);
  const [chunkRevealed, setChunkRevealed] = useState(true);
  const [teleprompterMode, setTeleprompterMode] = useState(false);
  const touchStartRef = useRef(null);

  // Line Run state
  const [runIndex, setRunIndex] = useState(0);
  const [lineRevealed, setLineRevealed] = useState(false);
  const [results, setResults] = useState({}); // index -> "nailed" | "peeked"

  // Cue Recall state
  const [revealedCues, setRevealedCues] = useState(new Set());

  useWakeLock();

  if (!memorization) return null;
  const { chunked_lines = [], cue_recall = [] } = memorization;

  const totalCues = cue_recall.length;
  const nailed = Object.values(results).filter(v => v === "nailed").length;
  const peeked = Object.values(results).filter(v => v === "peeked").length;
  const runComplete = Object.keys(results).length === totalCues && totalCues > 0;

  // --- Navigation ---
  const goNext = () => {
    if (currentChunk < chunked_lines.length - 1) {
      setCurrentChunk(c => c + 1);
      setChunkRevealed(true);
    }
  };
  const goPrev = () => {
    if (currentChunk > 0) {
      setCurrentChunk(c => c - 1);
      setChunkRevealed(true);
    }
  };

  const handleTouchStart = (e) => { touchStartRef.current = e.touches[0].clientX; };
  const handleTouchEnd = (e) => {
    if (!touchStartRef.current) return;
    const diff = e.changedTouches[0].clientX - touchStartRef.current;
    if (Math.abs(diff) > 60) { diff > 0 ? goPrev() : goNext(); }
    touchStartRef.current = null;
  };

  // --- Line Run handlers ---
  const revealLine = () => setLineRevealed(true);

  const markAndAdvance = (result) => {
    setResults(prev => ({ ...prev, [runIndex]: result }));
    if (runIndex < totalCues - 1) {
      setRunIndex(i => i + 1);
      setLineRevealed(false);
    }
  };

  const resetRun = () => {
    setRunIndex(0);
    setLineRevealed(false);
    setResults({});
  };

  // --- Cue Recall ---
  const toggleCueReveal = (index) => {
    setRevealedCues(prev => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });
  };

  const tabItems = [
    { value: "linerun", label: "Line Run", icon: Zap },
    { value: "reader", label: "Reader", icon: BookOpen },
    { value: "cue", label: "Cue & Recall", icon: Eye },
  ];

  return (
    <motion.div
      data-testid="memorization-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-50 bg-[#09090b] flex flex-col"
    >
      {/* Header */}
      {!teleprompterMode && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <BookOpen className="w-4 h-4 text-amber-500 shrink-0" />
            <h2 className="font-display text-base font-bold text-white truncate">
              {characterName ? `${characterName}'s Lines` : "Lines"}
            </h2>
          </div>
          <div className="flex items-center gap-1">
            {tab === "reader" && (
              <Button
                data-testid="teleprompter-toggle"
                variant="ghost"
                size="icon"
                onClick={() => setTeleprompterMode(true)}
                className="text-zinc-400 hover:text-amber-500 h-9 w-9"
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            )}
            <Button
              data-testid="memorization-close-button"
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-zinc-400 hover:text-white h-9 w-9"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>
      )}

      {/* Tab bar */}
      {!teleprompterMode && (
        <div className="flex px-4 pt-3 gap-1 shrink-0">
          {tabItems.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              data-testid={`memorization-${value}-tab`}
              onClick={() => setTab(value)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${
                tab === value
                  ? "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                  : "text-zinc-500 hover:text-zinc-400 border border-transparent"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Teleprompter header */}
      {teleprompterMode && (
        <div className="flex items-center justify-between px-4 py-2 shrink-0">
          <span className="text-xs text-zinc-600">{currentChunk + 1}/{chunked_lines.length}</span>
          <Button variant="ghost" size="icon" onClick={() => setTeleprompterMode(false)} className="text-zinc-500 hover:text-white h-8 w-8" data-testid="teleprompter-exit">
            <Minimize2 className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Content */}
      <div
        className="flex-1 overflow-y-auto px-4 py-4 pb-safe"
        onTouchStart={tab === "reader" ? handleTouchStart : undefined}
        onTouchEnd={tab === "reader" ? handleTouchEnd : undefined}
      >
        {/* ===== LINE RUN ===== */}
        {tab === "linerun" && (
          <div className="max-w-xl mx-auto flex flex-col h-full">
            {totalCues === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-sm text-zinc-500 text-center">No cue-recall data available for this breakdown.</p>
              </div>
            ) : runComplete ? (
              /* Run complete summary */
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex-1 flex flex-col items-center justify-center text-center"
              >
                <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-6">
                  <Check className="w-8 h-8 text-amber-500" />
                </div>
                <h3 className="font-display text-xl font-bold text-white mb-2">Run Complete</h3>
                <div className="flex gap-6 mb-8">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-emerald-400">{nailed}</p>
                    <p className="text-xs text-zinc-500">Nailed</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-amber-400">{peeked}</p>
                    <p className="text-xs text-zinc-500">Peeked</p>
                  </div>
                </div>
                <Button
                  data-testid="run-again-button"
                  onClick={resetRun}
                  className="bg-amber-500 hover:bg-amber-600 text-black font-bold gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  Run Again
                </Button>
              </motion.div>
            ) : (
              /* Active drill */
              <div className="flex-1 flex flex-col">
                {/* Progress */}
                <div className="flex items-center gap-2 mb-6">
                  <span className="text-xs text-zinc-600">{runIndex + 1} / {totalCues}</span>
                  <div className="flex-1 h-1 bg-zinc-900 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full transition-all" style={{ width: `${((runIndex + 1) / totalCues) * 100}%` }} />
                  </div>
                  <div className="flex gap-1.5">
                    {nailed > 0 && <span className="text-[10px] text-emerald-400">{nailed}</span>}
                    {peeked > 0 && <span className="text-[10px] text-amber-400">{peeked}</span>}
                  </div>
                </div>

                {/* Cue */}
                <AnimatePresence mode="wait">
                  <motion.div
                    key={runIndex}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{ duration: 0.2 }}
                    className="flex-1 flex flex-col justify-center"
                  >
                    <p className="text-xs uppercase tracking-widest text-zinc-600 mb-2">They say:</p>
                    <p className="text-lg text-zinc-400 font-script leading-relaxed mb-8">
                      {cue_recall[runIndex]?.cue}
                    </p>

                    {/* Your line */}
                    <div className="mb-8">
                      <p className="text-xs uppercase tracking-widest text-amber-500/60 mb-2">You say:</p>
                      {lineRevealed ? (
                        <motion.p
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="text-xl text-zinc-100 font-script leading-relaxed"
                        >
                          {cue_recall[runIndex]?.your_line}
                        </motion.p>
                      ) : (
                        <button
                          data-testid="reveal-line-button"
                          onClick={revealLine}
                          className="w-full py-6 rounded-lg border-2 border-dashed border-zinc-800 text-zinc-600 text-sm hover:border-zinc-700 hover:text-zinc-500 transition-colors active:bg-zinc-900/30"
                        >
                          Tap to reveal your line
                        </button>
                      )}
                    </div>

                    {/* Mark buttons */}
                    {lineRevealed && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex gap-3"
                      >
                        <Button
                          data-testid="mark-nailed"
                          onClick={() => markAndAdvance("nailed")}
                          className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-2"
                        >
                          <Check className="w-4 h-4" />
                          Nailed it
                        </Button>
                        <Button
                          data-testid="mark-peeked"
                          onClick={() => markAndAdvance("peeked")}
                          variant="outline"
                          className="flex-1 h-12 border-zinc-700 text-zinc-400 hover:text-zinc-200 font-bold gap-2"
                        >
                          <Eye className="w-4 h-4" />
                          Peeked
                        </Button>
                      </motion.div>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            )}
          </div>
        )}

        {/* ===== READER ===== */}
        {tab === "reader" && (
          <div className="max-w-2xl mx-auto flex flex-col h-full">
            {!teleprompterMode && (
              <div className="flex items-center justify-between mb-4">
                <Button variant="ghost" disabled={currentChunk === 0} onClick={goPrev} className="text-zinc-400 hover:text-white gap-1 h-11 px-4" data-testid="reader-prev-chunk">
                  <ChevronLeft className="w-5 h-5" />
                </Button>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-zinc-500">{currentChunk + 1} / {chunked_lines.length}</span>
                  <Button variant="ghost" onClick={() => setChunkRevealed(r => !r)} className="text-zinc-400 hover:text-amber-500 h-11 w-11" data-testid="reader-toggle-reveal">
                    {chunkRevealed ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </Button>
                </div>
                <Button variant="ghost" disabled={currentChunk === chunked_lines.length - 1} onClick={goNext} className="text-zinc-400 hover:text-white gap-1 h-11 px-4" data-testid="reader-next-chunk">
                  <ChevronRight className="w-5 h-5" />
                </Button>
              </div>
            )}

            {chunked_lines[currentChunk] && (
              <motion.div
                key={currentChunk}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className={`space-y-4 flex-1 flex flex-col ${teleprompterMode ? "justify-center items-center text-center" : ""}`}
              >
                <Badge variant="outline" className="text-amber-500 border-amber-500/20 self-start">
                  {chunked_lines[currentChunk].chunk_label}
                </Badge>
                <div
                  className={`font-script leading-loose text-zinc-100 whitespace-pre-line transition-all duration-300 ${
                    teleprompterMode ? "text-2xl sm:text-3xl md:text-4xl" : "text-xl"
                  } ${chunkRevealed ? "" : "blur-md select-none"}`}
                  data-testid="reader-chunk-text"
                >
                  {chunked_lines[currentChunk].lines}
                </div>
              </motion.div>
            )}

            {!teleprompterMode && chunked_lines.length > 1 && (
              <p className="text-center text-xs text-zinc-700 mt-4 sm:hidden">Swipe left/right to navigate</p>
            )}

            {/* Teleprompter tap zones */}
            {teleprompterMode && (
              <div className="fixed inset-0 z-10 flex">
                <button className="w-1/3 h-full" onClick={goPrev} data-testid="teleprompter-tap-prev" aria-label="Previous" />
                <button className="w-1/3 h-full" onClick={() => setChunkRevealed(r => !r)} data-testid="teleprompter-tap-toggle" aria-label="Toggle" />
                <button className="w-1/3 h-full" onClick={goNext} data-testid="teleprompter-tap-next" aria-label="Next" />
              </div>
            )}

            {/* Progress dots */}
            <div className="flex gap-1.5 mt-6 justify-center shrink-0">
              {chunked_lines.map((_, i) => (
                <button
                  key={i}
                  onClick={() => { setCurrentChunk(i); setChunkRevealed(true); }}
                  className={`h-1.5 rounded-full transition-colors ${
                    i === currentChunk ? "bg-amber-500 w-10" : i < currentChunk ? "bg-zinc-700 w-6" : "bg-zinc-800 w-6"
                  }`}
                  data-testid={`reader-chunk-indicator-${i}`}
                />
              ))}
            </div>
          </div>
        )}

        {/* ===== CUE & RECALL ===== */}
        {tab === "cue" && (
          <div className="max-w-2xl mx-auto space-y-3">
            <p className="text-sm text-zinc-500 mb-4">
              Read the cue, recall your line, then tap to check.
            </p>
            {cue_recall.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg overflow-hidden"
                data-testid={`cue-recall-item-${i}`}
              >
                <div className="px-4 py-3 border-b border-zinc-800/30">
                  <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-1">Cue</p>
                  <p className="text-sm text-zinc-400 font-script leading-relaxed">{item.cue}</p>
                </div>
                <button
                  onClick={() => toggleCueReveal(i)}
                  className="w-full px-4 py-3 text-left hover:bg-zinc-800/20 transition-colors"
                  data-testid={`cue-reveal-button-${i}`}
                >
                  <p className="text-[10px] uppercase tracking-widest text-amber-500/60 mb-1">Your line</p>
                  <p className={`text-base font-script text-zinc-100 transition-all duration-300 leading-relaxed ${
                    revealedCues.has(i) ? "" : "blur-md select-none"
                  }`}>
                    {item.your_line}
                  </p>
                  {!revealedCues.has(i) && (
                    <p className="text-xs text-zinc-700 mt-1">Tap to reveal</p>
                  )}
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
