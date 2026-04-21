import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, BookOpen, Dumbbell, Eye, EyeOff, ChevronDown, ChevronUp,
  Loader2, User, RotateCcw, ChevronRight, ChevronLeft,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PrepView({ project, onBack, onChangeCharacter, onEditLines }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("read"); // "read" | "rehearse"

  useEffect(() => {
    async function load() {
      try {
        // Prefer user-reviewed lines if they exist
        const reviewed = await axios.get(`${API}/projects/${project.id}/reviewed-lines`);
        if (reviewed.data.reviewed_lines) {
          setData({
            character: reviewed.data.character || project.selected_character,
            total_lines: reviewed.data.total_lines,
            scenes: reviewed.data.reviewed_lines,
          });
          setLoading(false);
          return;
        }
      } catch {}

      // Fall back to fresh extraction
      try {
        const resp = await axios.post(`${API}/projects/${project.id}/extract-lines`);
        setData(resp.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to extract lines.");
      }
      setLoading(false);
    }
    load();
  }, [project.id, project.selected_character]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="prep-loading">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!data || data.total_lines === 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4" data-testid="prep-empty">
        <p className="text-zinc-400 text-sm text-center">
          No lines found for <span className="text-zinc-200 font-medium">{project.selected_character}</span>.
        </p>
        <Button variant="outline" size="sm" onClick={onChangeCharacter} data-testid="prep-change-char-btn">
          Change character
        </Button>
        <Button variant="ghost" size="sm" onClick={onBack} className="text-zinc-500">
          Back
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen" data-testid="prep-view">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost" size="sm" onClick={onBack}
              className="text-zinc-400 hover:text-zinc-200 px-2 -ml-2"
              data-testid="prep-back-btn"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-semibold text-zinc-100 truncate">{project.title}</h1>
              <p className="text-[11px] text-zinc-500">
                {project.selected_character} — {data.total_lines} line{data.total_lines !== 1 ? "s" : ""}
              </p>
            </div>
            <button
              onClick={onChangeCharacter}
              className="text-[11px] text-amber-400 hover:text-amber-300 transition-colors shrink-0"
              data-testid="prep-change-char"
            >
              Change
            </button>
            {onEditLines && (
              <button
                onClick={onEditLines}
                className="text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors shrink-0"
                data-testid="prep-edit-lines"
              >
                Edit Lines
              </button>
            )}
          </div>

          {/* Mode tabs */}
          <div className="flex gap-1 bg-zinc-900/60 rounded-lg p-0.5">
            <button
              onClick={() => setMode("read")}
              data-testid="mode-read-btn"
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === "read"
                  ? "bg-zinc-800 text-zinc-100 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Read
            </button>
            <button
              onClick={() => setMode("rehearse")}
              data-testid="mode-rehearse-btn"
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === "rehearse"
                  ? "bg-amber-500/15 text-amber-400 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <Dumbbell className="w-3.5 h-3.5" />
              Rehearse
            </button>
          </div>
        </div>
      </header>

      <AnimatePresence mode="wait">
        {mode === "read" ? (
          <motion.div key="read" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            <ReadMode data={data} character={project.selected_character} />
          </motion.div>
        ) : (
          <motion.div key="rehearse" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            <RehearseMode data={data} character={project.selected_character} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


/* ============================
   READ MODE
   ============================ */
function ReadMode({ data, character }) {
  const [collapsed, setCollapsed] = useState({});
  const charUpper = character.toUpperCase();

  const toggleScene = (num) => {
    setCollapsed((prev) => ({ ...prev, [num]: !prev[num] }));
  };

  return (
    <div className="max-w-lg mx-auto px-4 pt-4 pb-20" data-testid="read-mode">
      {data.scenes.map((scene) => (
        <div key={scene.scene_number} className="mb-5" data-testid={`scene-${scene.scene_number}`}>
          {/* Scene heading */}
          <button
            onClick={() => toggleScene(scene.scene_number)}
            className="w-full flex items-center gap-2 mb-2 group"
            data-testid={`scene-heading-${scene.scene_number}`}
          >
            {collapsed[scene.scene_number] ? (
              <ChevronRight className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
            )}
            <span className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider truncate">
              {scene.heading}
            </span>
            <Badge className="bg-zinc-900 text-zinc-500 border-zinc-800 text-[9px] shrink-0 ml-auto">
              {scene.line_pairs.length}
            </Badge>
          </button>

          {!collapsed[scene.scene_number] && (
            <div className="space-y-1.5 pl-5">
              {scene.line_pairs.map((pair, i) => (
                <div key={i} data-testid={`line-pair-${scene.scene_number}-${i}`}>
                  {/* Cue */}
                  {pair.cue_speaker && (
                    <div className="py-1.5">
                      <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-wide">
                        {pair.cue_speaker}
                      </span>
                      <p className="text-[13px] text-zinc-500 leading-relaxed">{pair.cue_text}</p>
                    </div>
                  )}
                  {/* Character's line — highlighted */}
                  <div className="bg-amber-500/6 border-l-2 border-amber-500/40 pl-3 py-1.5 rounded-r-md">
                    <span className="text-[10px] font-mono text-amber-400/70 uppercase tracking-wide">
                      {charUpper}
                    </span>
                    <p className="text-[13px] text-zinc-200 leading-relaxed" data-testid={`my-line-${scene.scene_number}-${i}`}>
                      {pair.line_text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}


/* ============================
   REHEARSE MODE
   ============================ */
function RehearseMode({ data, character }) {
  // Flatten all line pairs across scenes
  const allPairs = [];
  data.scenes.forEach((scene) => {
    scene.line_pairs.forEach((pair) => {
      allPairs.push({ ...pair, scene_heading: scene.heading, scene_number: scene.scene_number });
    });
  });

  const [currentIdx, setCurrentIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ revealed: 0, total: allPairs.length });
  const containerRef = useRef(null);

  const current = allPairs[currentIdx] || null;
  const charUpper = character.toUpperCase();
  const progress = allPairs.length > 0 ? ((currentIdx + 1) / allPairs.length) * 100 : 0;

  const handleReveal = useCallback(() => {
    if (!revealed) {
      setRevealed(true);
      setScore((prev) => ({ ...prev, revealed: prev.revealed + 1 }));
    }
  }, [revealed]);

  const handleNext = useCallback(() => {
    if (currentIdx < allPairs.length - 1) {
      setCurrentIdx((i) => i + 1);
      setRevealed(false);
    }
  }, [currentIdx, allPairs.length]);

  const handlePrev = useCallback(() => {
    if (currentIdx > 0) {
      setCurrentIdx((i) => i - 1);
      setRevealed(false);
    }
  }, [currentIdx]);

  const handleRestart = useCallback(() => {
    setCurrentIdx(0);
    setRevealed(false);
    setScore({ revealed: 0, total: allPairs.length });
  }, [allPairs.length]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (!revealed) handleReveal();
        else handleNext();
      }
      if (e.key === "ArrowRight") handleNext();
      if (e.key === "ArrowLeft") handlePrev();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [revealed, handleReveal, handleNext, handlePrev]);

  if (!current) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-16 text-center" data-testid="rehearse-empty">
        <p className="text-zinc-400 text-sm">No lines to rehearse.</p>
      </div>
    );
  }

  // Finished all lines
  if (currentIdx >= allPairs.length) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-16 text-center" data-testid="rehearse-done">
        <p className="text-lg font-semibold text-zinc-100 mb-2">Run complete!</p>
        <p className="text-sm text-zinc-500">{score.revealed} / {score.total} lines</p>
        <Button onClick={handleRestart} className="mt-6 bg-amber-500 hover:bg-amber-600 text-black" data-testid="rehearse-restart-btn">
          <RotateCcw className="w-4 h-4 mr-1.5" /> Run Again
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 pt-4 pb-28" ref={containerRef} data-testid="rehearse-mode">
      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-[11px] text-zinc-600 mb-1">
          <span>{current.scene_heading}</span>
          <span>{currentIdx + 1} / {allPairs.length}</span>
        </div>
        <div className="h-1 bg-zinc-900 rounded-full overflow-hidden">
          <div
            className="h-full bg-amber-500/60 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
            data-testid="rehearse-progress"
          />
        </div>
      </div>

      {/* Cue card */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 mb-4" data-testid="cue-card">
        {current.cue_speaker && (
          <div className="flex items-center gap-2 mb-2">
            <User className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider">
              {current.cue_speaker}
            </span>
          </div>
        )}
        <p className="text-[15px] text-zinc-300 leading-relaxed" data-testid="cue-text">
          {current.cue_text}
        </p>
      </div>

      {/* Your line — tap to reveal */}
      <div
        onClick={handleReveal}
        className={`relative rounded-xl p-5 min-h-[120px] flex flex-col justify-center cursor-pointer transition-all ${
          revealed
            ? "bg-amber-500/8 border border-amber-500/30"
            : "bg-zinc-900/50 border border-zinc-800 border-dashed"
        }`}
        data-testid="line-card"
      >
        <div className="flex items-center gap-2 mb-2">
          {revealed ? (
            <Eye className="w-3.5 h-3.5 text-amber-400" />
          ) : (
            <EyeOff className="w-3.5 h-3.5 text-zinc-600" />
          )}
          <span className={`text-[11px] font-mono uppercase tracking-wider ${
            revealed ? "text-amber-400/70" : "text-zinc-600"
          }`}>
            {charUpper}
          </span>
        </div>

        <AnimatePresence mode="wait">
          {revealed ? (
            <motion.p
              key="revealed"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-[15px] text-zinc-100 leading-relaxed"
              data-testid="revealed-line"
            >
              {current.line_text}
            </motion.p>
          ) : (
            <motion.p
              key="hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-zinc-600 italic"
              data-testid="hidden-line"
            >
              Tap to reveal your line
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#09090b]/95 backdrop-blur-md border-t border-zinc-900 px-4 py-4">
        <div className="max-w-lg mx-auto flex gap-3">
          <Button
            variant="outline"
            onClick={handlePrev}
            disabled={currentIdx === 0}
            className="h-12 px-4 border-zinc-800 text-zinc-400 rounded-xl"
            data-testid="rehearse-prev-btn"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          {!revealed ? (
            <Button
              onClick={handleReveal}
              className="flex-1 h-12 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold rounded-xl text-sm"
              data-testid="rehearse-reveal-btn"
            >
              Reveal Line
            </Button>
          ) : currentIdx < allPairs.length - 1 ? (
            <Button
              onClick={handleNext}
              className="flex-1 h-12 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm gap-1.5"
              data-testid="rehearse-next-btn"
            >
              Next Line <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              onClick={handleRestart}
              className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm gap-1.5"
              data-testid="rehearse-complete-btn"
            >
              <RotateCcw className="w-4 h-4" /> Run Again
            </Button>
          )}

          <Button
            variant="outline"
            onClick={handleNext}
            disabled={currentIdx >= allPairs.length - 1}
            className="h-12 px-4 border-zinc-800 text-zinc-400 rounded-xl"
            data-testid="rehearse-skip-btn"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
