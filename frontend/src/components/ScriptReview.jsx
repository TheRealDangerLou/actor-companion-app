import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Check, ChevronLeft, ChevronRight, Edit3, Eye, Save, RotateCcw } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ScriptReview({ scriptId, onConfirm, onBack }) {
  const [scenes, setScenes] = useState([]);
  const [characterName, setCharacterName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedTexts, setEditedTexts] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const resp = await axios.post(`${API}/clean-script`, { script_id: scriptId });
        const data = resp.data;
        setScenes(data.scenes || []);
        setCharacterName(data.character_name || "");
        const initial = {};
        (data.scenes || []).forEach((s) => {
          initial[s.breakdown_id] = s.cleaned_text;
        });
        setEditedTexts(initial);
      } catch (err) {
        toast.error("Failed to load script for review.");
      }
      setLoading(false);
    }
    load();
  }, [scriptId]);

  const activeScene = scenes[activeIdx] || null;
  const activeBid = activeScene?.breakdown_id;
  const currentText = activeBid ? (editedTexts[activeBid] ?? "") : "";

  const handleTextChange = useCallback(
    (val) => {
      if (!activeBid) return;
      setEditedTexts((prev) => ({ ...prev, [activeBid]: val }));
    },
    [activeBid]
  );

  const handleReset = useCallback(() => {
    if (!activeScene) return;
    setEditedTexts((prev) => ({
      ...prev,
      [activeScene.breakdown_id]: activeScene.cleaned_text,
    }));
    toast.info("Reset to auto-cleaned version.");
  }, [activeScene]);

  const handleConfirmAll = useCallback(async () => {
    setSaving(true);
    try {
      const payload = {
        script_id: scriptId,
        scenes: scenes.map((s) => ({
          breakdown_id: s.breakdown_id,
          cleaned_text: editedTexts[s.breakdown_id] || s.cleaned_text,
        })),
      };
      await axios.post(`${API}/save-cleaned-script`, payload);
      toast.success(`Saved cleaned text for ${scenes.length} scenes.`);
      onConfirm?.();
    } catch (err) {
      toast.error("Failed to save. Try again.");
    }
    setSaving(false);
  }, [scriptId, scenes, editedTexts, onConfirm]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="script-review-loading">
        <div className="text-zinc-500 text-sm">Cleaning script...</div>
      </div>
    );
  }

  if (!scenes.length) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-zinc-500">No scenes found for this script.</p>
        <Button variant="outline" onClick={onBack} data-testid="review-back-btn">
          Go Back
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-24" data-testid="script-review">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="text-zinc-400 hover:text-zinc-200 gap-1 px-2"
              data-testid="review-back-btn"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </Button>
            <div>
              <h1 className="text-base font-semibold text-zinc-100">
                Review Script — {characterName}
              </h1>
              <p className="text-xs text-zinc-500">
                Review and edit the cleaned text. This becomes the source of truth for all features.
              </p>
            </div>
          </div>
          <Button
            onClick={handleConfirmAll}
            disabled={saving}
            className="bg-amber-500 hover:bg-amber-600 text-black font-semibold gap-1.5"
            data-testid="confirm-all-btn"
          >
            <Check className="w-4 h-4" />
            {saving ? "Saving..." : `Confirm All ${scenes.length} Scenes`}
          </Button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 mt-4">
        {/* Scene navigator */}
        <div className="flex items-center gap-2 mb-4">
          <Button
            variant="ghost"
            size="sm"
            disabled={activeIdx === 0}
            onClick={() => setActiveIdx((i) => Math.max(0, i - 1))}
            className="text-zinc-400 px-2"
            data-testid="review-prev-scene"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          <div className="flex-1 overflow-x-auto">
            <div className="flex gap-1.5 min-w-0">
              {scenes.map((s, i) => (
                <button
                  key={s.breakdown_id}
                  onClick={() => setActiveIdx(i)}
                  data-testid={`review-scene-tab-${i}`}
                  className={`shrink-0 px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                    i === activeIdx
                      ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                      : "text-zinc-500 hover:text-zinc-300 border border-transparent hover:border-zinc-800"
                  }`}
                >
                  #{s.scene_number}
                </button>
              ))}
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            disabled={activeIdx === scenes.length - 1}
            onClick={() => setActiveIdx((i) => Math.min(scenes.length - 1, i + 1))}
            className="text-zinc-400 px-2"
            data-testid="review-next-scene"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        {/* Scene content */}
        {activeScene && (
          <motion.div
            key={activeScene.breakdown_id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-sm font-semibold text-zinc-200">
                  Scene {activeIdx + 1} of {scenes.length}
                </h2>
                <p className="text-xs text-zinc-500">{activeScene.scene_heading}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditMode((e) => !e)}
                  className="text-xs gap-1.5 h-7 border-zinc-700"
                  data-testid="toggle-edit-btn"
                >
                  {editMode ? (
                    <>
                      <Eye className="w-3.5 h-3.5" /> Preview
                    </>
                  ) : (
                    <>
                      <Edit3 className="w-3.5 h-3.5" /> Edit
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  className="text-xs gap-1.5 h-7 border-zinc-700 text-zinc-400"
                  data-testid="reset-scene-btn"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Reset
                </Button>
              </div>
            </div>

            {editMode ? (
              <Textarea
                value={currentText}
                onChange={(e) => handleTextChange(e.target.value)}
                className="min-h-[500px] font-mono text-sm leading-relaxed bg-zinc-950 border-zinc-800 text-zinc-200 resize-y"
                data-testid="scene-edit-textarea"
              />
            ) : (
              <div
                className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 min-h-[500px] overflow-y-auto"
                data-testid="scene-preview"
              >
                <pre className="font-mono text-sm leading-relaxed text-zinc-300 whitespace-pre-wrap">
                  {currentText}
                </pre>
              </div>
            )}

            {/* Quick stats */}
            <div className="flex items-center gap-3 mt-3 text-xs text-zinc-500">
              <span>{currentText.split("\n").length} lines</span>
              <span>{currentText.length} chars</span>
              {editedTexts[activeBid] !== activeScene.cleaned_text && (
                <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px]">
                  Edited
                </Badge>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
