import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { X, Eye, EyeOff, ChevronRight, ChevronLeft, BookOpen, Maximize2, Minimize2 } from "lucide-react";

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
  return wakeLockRef.current !== null;
}

export default function MemorizationMode({
  memorization,
  characterName,
  onClose,
}) {
  const [mode, setMode] = useState("reader");
  const [currentChunk, setCurrentChunk] = useState(0);
  const [revealedCues, setRevealedCues] = useState(new Set());
  const [chunkRevealed, setChunkRevealed] = useState(true);
  const [teleprompterMode, setTeleprompterMode] = useState(false);
  const contentRef = useRef(null);
  const touchStartRef = useRef(null);

  useWakeLock();

  if (!memorization) return null;
  const { chunked_lines = [], cue_recall = [] } = memorization;

  const goNext = () => {
    if (currentChunk < chunked_lines.length - 1) {
      setCurrentChunk((c) => c + 1);
      setChunkRevealed(true);
    }
  };

  const goPrev = () => {
    if (currentChunk > 0) {
      setCurrentChunk((c) => c - 1);
      setChunkRevealed(true);
    }
  };

  const handleTouchStart = (e) => {
    touchStartRef.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e) => {
    if (!touchStartRef.current) return;
    const diff = e.changedTouches[0].clientX - touchStartRef.current;
    if (Math.abs(diff) > 60) {
      if (diff > 0) goPrev();
      else goNext();
    }
    touchStartRef.current = null;
  };

  const toggleCueReveal = (index) => {
    setRevealedCues((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <motion.div
      data-testid="memorization-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-50 bg-[#09090b] flex flex-col mobile-header-compact"
    >
      {/* Header — compact on mobile */}
      {!teleprompterMode && (
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-zinc-900 shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <BookOpen className="w-4 h-4 sm:w-5 sm:h-5 text-amber-500 shrink-0" />
            <h2 className="font-display text-base sm:text-lg font-bold text-white truncate">
              {characterName ? `${characterName}'s Lines` : "Reader Mode"}
            </h2>
            <div className="awake-indicator shrink-0" title="Screen stays on" />
          </div>
          <div className="flex items-center gap-1">
            <Button
              data-testid="teleprompter-toggle"
              variant="ghost"
              size="icon"
              onClick={() => setTeleprompterMode(true)}
              className="text-zinc-400 hover:text-amber-500 h-9 w-9"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
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

      {/* Mode Selector — hidden in teleprompter mode */}
      {!teleprompterMode && (
        <div className="px-4 sm:px-6 pt-3 sm:pt-4 shrink-0">
          <Tabs value={mode} onValueChange={setMode}>
            <TabsList className="bg-zinc-900/80 border border-zinc-800">
              <TabsTrigger
                value="reader"
                data-testid="memorization-reader-tab"
                className="gap-1.5 data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-500"
              >
                <BookOpen className="w-3.5 h-3.5" />
                Reader
              </TabsTrigger>
              <TabsTrigger
                value="cue"
                data-testid="memorization-cue-tab"
                className="gap-1.5 data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-500"
              >
                <Eye className="w-3.5 h-3.5" />
                Cue Recall
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      )}

      {/* Teleprompter mode header — minimal */}
      {teleprompterMode && (
        <div className="flex items-center justify-between px-4 py-2 shrink-0">
          <span className="text-xs text-zinc-600">
            {currentChunk + 1}/{chunked_lines.length}
          </span>
          <div className="flex items-center gap-2">
            <div className="awake-indicator" />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTeleprompterMode(false)}
              className="text-zinc-500 hover:text-white h-8 w-8"
              data-testid="teleprompter-exit"
            >
              <Minimize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Content */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6 mobile-bottom-safe"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {mode === "reader" && (
          <div className="max-w-2xl mx-auto flex flex-col h-full">
            {/* Navigation — larger touch targets on mobile */}
            {!teleprompterMode && (
              <div className="flex items-center justify-between mb-4 sm:mb-6">
                <Button
                  variant="ghost"
                  disabled={currentChunk === 0}
                  onClick={goPrev}
                  className="text-zinc-400 hover:text-white gap-1 h-11 sm:h-9 px-4 sm:px-3 mobile-touch-target"
                  data-testid="reader-prev-chunk"
                >
                  <ChevronLeft className="w-5 h-5 sm:w-4 sm:h-4" />
                  <span className="hidden sm:inline">Prev</span>
                </Button>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-zinc-500">
                    {currentChunk + 1} / {chunked_lines.length}
                  </span>
                  <Button
                    variant="ghost"
                    onClick={() => setChunkRevealed((r) => !r)}
                    className="text-zinc-400 hover:text-amber-500 h-11 sm:h-9 w-11 sm:w-9"
                    data-testid="reader-toggle-reveal"
                  >
                    {chunkRevealed ? <EyeOff className="w-5 h-5 sm:w-4 sm:h-4" /> : <Eye className="w-5 h-5 sm:w-4 sm:h-4" />}
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  disabled={currentChunk === chunked_lines.length - 1}
                  onClick={goNext}
                  className="text-zinc-400 hover:text-white gap-1 h-11 sm:h-9 px-4 sm:px-3 mobile-touch-target"
                  data-testid="reader-next-chunk"
                >
                  <span className="hidden sm:inline">Next</span>
                  <ChevronRight className="w-5 h-5 sm:w-4 sm:h-4" />
                </Button>
              </div>
            )}

            {/* Current chunk — large text for teleprompter */}
            {chunked_lines[currentChunk] && (
              <motion.div
                key={currentChunk}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className={`space-y-4 flex-1 flex flex-col ${
                  teleprompterMode ? "justify-center items-center text-center" : ""
                }`}
              >
                <Badge
                  variant="outline"
                  className="text-amber-500 border-amber-500/20 self-start"
                >
                  {chunked_lines[currentChunk].chunk_label}
                </Badge>
                <div
                  className={`font-script leading-loose text-zinc-100 whitespace-pre-line transition-all duration-300 ${
                    teleprompterMode
                      ? "text-2xl sm:text-3xl md:text-4xl teleprompter-text"
                      : "text-xl sm:text-lg md:text-xl"
                  } ${chunkRevealed ? "" : "blur-md select-none"}`}
                  data-testid="reader-chunk-text"
                >
                  {chunked_lines[currentChunk].lines}
                </div>
              </motion.div>
            )}

            {/* Swipe hint on mobile */}
            {!teleprompterMode && chunked_lines.length > 1 && (
              <p className="text-center text-xs text-zinc-700 mt-4 sm:hidden">
                Swipe left/right to navigate
              </p>
            )}

            {/* Tap zones in teleprompter mode */}
            {teleprompterMode && (
              <div className="fixed inset-0 z-10 flex">
                <button
                  className="w-1/3 h-full"
                  onClick={goPrev}
                  data-testid="teleprompter-tap-prev"
                  aria-label="Previous chunk"
                />
                <button
                  className="w-1/3 h-full"
                  onClick={() => setChunkRevealed((r) => !r)}
                  data-testid="teleprompter-tap-toggle"
                  aria-label="Toggle reveal"
                />
                <button
                  className="w-1/3 h-full"
                  onClick={goNext}
                  data-testid="teleprompter-tap-next"
                  aria-label="Next chunk"
                />
              </div>
            )}

            {/* Progress indicators */}
            <div className="flex gap-1.5 mt-6 sm:mt-8 justify-center shrink-0">
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

        {mode === "cue" && (
          <div className="max-w-2xl mx-auto space-y-3 sm:space-y-4">
            <p className="text-sm text-zinc-500 mb-4 sm:mb-6">
              Read the cue, try to recall your line, then tap to reveal.
            </p>
            {cue_recall.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg overflow-hidden"
                data-testid={`cue-recall-item-${i}`}
              >
                <div className="px-4 py-3 border-b border-zinc-800/30">
                  <p className="text-xs uppercase tracking-wider text-zinc-600 mb-1">Cue</p>
                  <p className="text-sm sm:text-base text-zinc-400 font-script">{item.cue}</p>
                </div>
                <button
                  onClick={() => toggleCueReveal(i)}
                  className="w-full px-4 py-3 text-left hover:bg-zinc-800/20 transition-colors mobile-touch-target"
                  data-testid={`cue-reveal-button-${i}`}
                >
                  <p className="text-xs uppercase tracking-wider text-amber-500/60 mb-1">Your Line</p>
                  <p className={`text-base sm:text-lg font-script text-zinc-100 transition-all duration-300 ${
                    revealedCues.has(i) ? "" : "blur-md select-none"
                  }`}>
                    {item.your_line}
                  </p>
                  {!revealedCues.has(i) && (
                    <p className="text-xs text-zinc-600 mt-1">Tap to reveal</p>
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
