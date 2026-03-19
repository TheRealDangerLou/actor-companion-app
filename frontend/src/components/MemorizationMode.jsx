import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { X, Eye, EyeOff, ChevronRight, ChevronLeft, BookOpen } from "lucide-react";

export default function MemorizationMode({
  memorization,
  characterName,
  onClose,
}) {
  const [mode, setMode] = useState("reader");
  const [currentChunk, setCurrentChunk] = useState(0);
  const [revealedCues, setRevealedCues] = useState(new Set());
  const [chunkRevealed, setChunkRevealed] = useState(true);

  if (!memorization) return null;

  const { chunked_lines = [], cue_recall = [] } = memorization;

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
      className="fixed inset-0 z-50 bg-[#09090b]/98 backdrop-blur-sm flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-zinc-900">
        <div className="flex items-center gap-3">
          <BookOpen className="w-5 h-5 text-amber-500" />
          <h2 className="font-display text-lg font-bold text-white">
            {characterName ? `${characterName}'s Lines` : "Reader Mode"}
          </h2>
        </div>
        <Button
          data-testid="memorization-close-button"
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="text-zinc-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Mode Selector */}
      <div className="px-4 sm:px-6 pt-4">
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

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {mode === "reader" && (
          <div className="max-w-2xl mx-auto">
            {/* Chunk navigation */}
            <div className="flex items-center justify-between mb-6">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentChunk === 0}
                onClick={() => {
                  setCurrentChunk((c) => c - 1);
                  setChunkRevealed(true);
                }}
                className="text-zinc-400 hover:text-white gap-1"
                data-testid="reader-prev-chunk"
              >
                <ChevronLeft className="w-4 h-4" />
                Prev
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm text-zinc-500">
                  {currentChunk + 1} / {chunked_lines.length}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setChunkRevealed((r) => !r)}
                  className="text-zinc-400 hover:text-amber-500"
                  data-testid="reader-toggle-reveal"
                >
                  {chunkRevealed ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={currentChunk === chunked_lines.length - 1}
                onClick={() => {
                  setCurrentChunk((c) => c + 1);
                  setChunkRevealed(true);
                }}
                className="text-zinc-400 hover:text-white gap-1"
                data-testid="reader-next-chunk"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            {/* Current chunk */}
            {chunked_lines[currentChunk] && (
              <motion.div
                key={currentChunk}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-4"
              >
                <Badge
                  variant="outline"
                  className="text-amber-500 border-amber-500/20"
                >
                  {chunked_lines[currentChunk].chunk_label}
                </Badge>
                <div
                  className={`font-script text-lg md:text-xl leading-loose text-zinc-100 whitespace-pre-line transition-all duration-300 ${
                    chunkRevealed ? "" : "blur-md select-none"
                  }`}
                  data-testid="reader-chunk-text"
                >
                  {chunked_lines[currentChunk].lines}
                </div>
              </motion.div>
            )}

            {/* All chunks timeline */}
            <div className="flex gap-1.5 mt-8 justify-center">
              {chunked_lines.map((_, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setCurrentChunk(i);
                    setChunkRevealed(true);
                  }}
                  className={`w-8 h-1.5 rounded-full transition-colors ${
                    i === currentChunk
                      ? "bg-amber-500"
                      : i < currentChunk
                      ? "bg-zinc-700"
                      : "bg-zinc-800"
                  }`}
                  data-testid={`reader-chunk-indicator-${i}`}
                />
              ))}
            </div>
          </div>
        )}

        {mode === "cue" && (
          <div className="max-w-2xl mx-auto space-y-4">
            <p className="text-sm text-zinc-500 mb-6">
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
                {/* Cue line */}
                <div className="px-4 py-3 border-b border-zinc-800/30">
                  <p className="text-xs uppercase tracking-wider text-zinc-600 mb-1">
                    Cue
                  </p>
                  <p className="text-sm text-zinc-400 font-script">
                    {item.cue}
                  </p>
                </div>
                {/* Your line */}
                <button
                  onClick={() => toggleCueReveal(i)}
                  className="w-full px-4 py-3 text-left hover:bg-zinc-800/20 transition-colors"
                  data-testid={`cue-reveal-button-${i}`}
                >
                  <p className="text-xs uppercase tracking-wider text-amber-500/60 mb-1">
                    Your Line
                  </p>
                  <p
                    className={`text-base font-script text-zinc-100 transition-all duration-300 ${
                      revealedCues.has(i) ? "" : "blur-md select-none"
                    }`}
                  >
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
