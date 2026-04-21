import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Check, Loader2, Trash2, Merge, Edit3, Eye,
  ChevronDown, ChevronRight, AlertTriangle,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function LineReview({ project, onLinesReviewed, onBack }) {
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingKey, setEditingKey] = useState(null); // "scene-pair" key
  const [collapsed, setCollapsed] = useState({});
  const [showParens, setShowParens] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Check for existing reviewed lines first
        const reviewed = await axios.get(`${API}/projects/${project.id}/reviewed-lines`);
        if (reviewed.data.reviewed_lines) {
          setScenes(reviewed.data.reviewed_lines);
          setLoading(false);
          return;
        }
      } catch {}

      // Fall back to fresh extraction
      try {
        const resp = await axios.post(`${API}/projects/${project.id}/extract-lines`);
        setScenes(resp.data.scenes || []);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to extract lines.");
      }
      setLoading(false);
    }
    load();
  }, [project.id]);

  const totalLines = scenes.reduce((sum, s) => sum + s.line_pairs.length, 0);

  // Edit a specific field in a line pair
  const updatePair = useCallback((sceneIdx, pairIdx, field, value) => {
    setScenes((prev) => {
      const next = prev.map((s, si) => {
        if (si !== sceneIdx) return s;
        return {
          ...s,
          line_pairs: s.line_pairs.map((p, pi) => {
            if (pi !== pairIdx) return p;
            return { ...p, [field]: value };
          }),
        };
      });
      return next;
    });
  }, []);

  // Delete a line pair
  const deletePair = useCallback((sceneIdx, pairIdx) => {
    setScenes((prev) => {
      const next = prev.map((s, si) => {
        if (si !== sceneIdx) return s;
        return {
          ...s,
          line_pairs: s.line_pairs.filter((_, pi) => pi !== pairIdx),
        };
      });
      // Remove empty scenes
      return next.filter((s) => s.line_pairs.length > 0);
    });
    setEditingKey(null);
    toast.info("Line removed.");
  }, []);

  // Merge current pair with the next one (combine line_text)
  const mergePairDown = useCallback((sceneIdx, pairIdx) => {
    setScenes((prev) => {
      const scene = prev[sceneIdx];
      if (!scene || pairIdx >= scene.line_pairs.length - 1) return prev;
      const current = scene.line_pairs[pairIdx];
      const next = scene.line_pairs[pairIdx + 1];
      const merged = {
        ...current,
        line_text: current.line_text + " " + next.line_text,
      };
      const newPairs = [...scene.line_pairs];
      newPairs.splice(pairIdx, 2, merged);
      return prev.map((s, si) => (si === sceneIdx ? { ...s, line_pairs: newPairs } : s));
    });
    setEditingKey(null);
    toast.info("Lines merged.");
  }, []);

  const toggleScene = (idx) => {
    setCollapsed((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/projects/${project.id}/reviewed-lines`, { scenes });
      toast.success("Lines saved — ready to rehearse.");
      onLinesReviewed?.();
    } catch {
      toast.error("Failed to save lines.");
    }
    setSaving(false);
  }, [scenes, project.id, onLinesReviewed]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="line-review-loading">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (totalLines === 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4" data-testid="line-review-empty">
        <AlertTriangle className="w-8 h-8 text-zinc-600" />
        <p className="text-zinc-400 text-sm text-center">
          No lines found for <span className="text-zinc-200 font-medium">{project.selected_character}</span>.
        </p>
        <Button variant="outline" size="sm" onClick={onBack} data-testid="line-review-back-empty">
          Go Back
        </Button>
      </div>
    );
  }

  const charUpper = (project.selected_character || "").toUpperCase();

  return (
    <div className="min-h-screen pb-28" data-testid="line-review">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-2 mb-1">
            <Button
              variant="ghost" size="sm" onClick={onBack}
              className="text-zinc-400 hover:text-zinc-200 px-2 -ml-2"
              data-testid="line-review-back-btn"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-semibold text-zinc-100 truncate">
                Review My Lines
              </h1>
              <p className="text-[11px] text-zinc-500">
                {charUpper} — {totalLines} line{totalLines !== 1 ? "s" : ""} across {scenes.length} scene{scenes.length !== 1 ? "s" : ""}
              </p>
            </div>
            <button
              onClick={() => setShowParens((v) => !v)}
              className={`text-[10px] px-2 py-1 rounded border transition-colors ${
                showParens
                  ? "border-zinc-700 text-zinc-400"
                  : "border-amber-500/30 text-amber-400 bg-amber-500/5"
              }`}
              data-testid="toggle-parens-btn"
            >
              {showParens ? "(hints on)" : "(hints off)"}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 pt-3">
        {scenes.map((scene, si) => (
          <div key={si} className="mb-4" data-testid={`review-scene-${si}`}>
            {/* Scene heading */}
            <button
              onClick={() => toggleScene(si)}
              className="w-full flex items-center gap-2 mb-2"
              data-testid={`review-scene-toggle-${si}`}
            >
              {collapsed[si] ? (
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

            <AnimatePresence>
              {!collapsed[si] && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <div className="space-y-2 pl-1">
                    {scene.line_pairs.map((pair, pi) => {
                      const key = `${si}-${pi}`;
                      const isEditing = editingKey === key;
                      const canMerge = pi < scene.line_pairs.length - 1;

                      // Filter parentheticals if toggled off
                      const displayCue = showParens
                        ? pair.cue_text
                        : pair.cue_text.replace(/\s*\(.*?\)\s*/g, " ").trim();
                      const displayLine = showParens
                        ? pair.line_text
                        : pair.line_text.replace(/\s*\(.*?\)\s*/g, " ").trim();

                      return (
                        <motion.div
                          key={key}
                          layout
                          className={`rounded-xl border transition-colors ${
                            isEditing
                              ? "border-amber-500/30 bg-amber-500/5"
                              : "border-zinc-800/60 bg-zinc-950/50"
                          }`}
                          data-testid={`line-card-${si}-${pi}`}
                        >
                          {/* Compact view */}
                          {!isEditing && (
                            <div
                              className="px-3 py-2.5 cursor-pointer"
                              onClick={() => setEditingKey(key)}
                            >
                              {/* Cue */}
                              {pair.cue_speaker && (
                                <div className="mb-1">
                                  <span className="text-[9px] font-mono text-zinc-600 uppercase tracking-wider">
                                    {pair.cue_speaker}
                                  </span>
                                  <p className="text-[12px] text-zinc-500 leading-snug line-clamp-2">
                                    {displayCue}
                                  </p>
                                </div>
                              )}
                              {!pair.cue_speaker && pair.cue_text && (
                                <p className="text-[11px] text-zinc-600 italic mb-1">{pair.cue_text}</p>
                              )}
                              {/* Line */}
                              <div className="border-l-2 border-amber-500/40 pl-2.5">
                                <span className="text-[9px] font-mono text-amber-400/60 uppercase tracking-wider">
                                  {charUpper}
                                </span>
                                <p className="text-[13px] text-zinc-200 leading-snug">
                                  {displayLine}
                                </p>
                              </div>
                            </div>
                          )}

                          {/* Edit mode */}
                          {isEditing && (
                            <div className="px-3 py-3 space-y-3" data-testid={`line-edit-${si}-${pi}`}>
                              {/* Cue edit */}
                              <div>
                                <label className="text-[10px] text-zinc-500 mb-1 block">
                                  Cue {pair.cue_speaker ? `(${pair.cue_speaker})` : ""}
                                </label>
                                <Textarea
                                  value={pair.cue_text}
                                  onChange={(e) => updatePair(si, pi, "cue_text", e.target.value)}
                                  className="min-h-[60px] text-[13px] bg-zinc-950 border-zinc-800 text-zinc-300 resize-none rounded-lg"
                                  data-testid={`edit-cue-${si}-${pi}`}
                                />
                              </div>
                              {/* Line edit */}
                              <div>
                                <label className="text-[10px] text-amber-400/60 mb-1 block">{charUpper}</label>
                                <Textarea
                                  value={pair.line_text}
                                  onChange={(e) => updatePair(si, pi, "line_text", e.target.value)}
                                  className="min-h-[60px] text-[13px] bg-zinc-950 border-amber-500/20 text-zinc-100 resize-none rounded-lg"
                                  data-testid={`edit-line-${si}-${pi}`}
                                />
                              </div>
                              {/* Actions */}
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost" size="sm"
                                  onClick={() => setEditingKey(null)}
                                  className="text-[11px] text-zinc-400 gap-1 h-7 px-2"
                                  data-testid={`edit-done-${si}-${pi}`}
                                >
                                  <Eye className="w-3 h-3" /> Done
                                </Button>
                                {canMerge && (
                                  <Button
                                    variant="ghost" size="sm"
                                    onClick={() => mergePairDown(si, pi)}
                                    className="text-[11px] text-zinc-400 gap-1 h-7 px-2"
                                    data-testid={`merge-btn-${si}-${pi}`}
                                  >
                                    <Merge className="w-3 h-3" /> Merge with next
                                  </Button>
                                )}
                                <Button
                                  variant="ghost" size="sm"
                                  onClick={() => deletePair(si, pi)}
                                  className="text-[11px] text-red-400 hover:text-red-300 gap-1 h-7 px-2 ml-auto"
                                  data-testid={`delete-btn-${si}-${pi}`}
                                >
                                  <Trash2 className="w-3 h-3" /> Delete
                                </Button>
                              </div>
                            </div>
                          )}
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>

      {/* Bottom action bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#09090b]/95 backdrop-blur-md border-t border-zinc-900 px-4 py-4">
        <div className="max-w-lg mx-auto">
          <Button
            onClick={handleSave}
            disabled={saving || totalLines === 0}
            className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm gap-1.5"
            data-testid="save-lines-btn"
          >
            <Check className="w-4 h-4" />
            {saving ? "Saving..." : `Lock ${totalLines} Lines & Rehearse`}
          </Button>
        </div>
      </div>
    </div>
  );
}
