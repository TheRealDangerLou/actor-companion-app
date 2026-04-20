import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { ArrowLeft, Check, Loader2, User, Hash, PenLine } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CharacterSelect({ project, onCharacterSelected, onBack }) {
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState(null);
  const [showManual, setShowManual] = useState(false);
  const [manualName, setManualName] = useState("");

  useEffect(() => {
    async function detect() {
      try {
        const resp = await axios.post(`${API}/projects/${project.id}/detect-characters`);
        const chars = resp.data.characters || [];
        setCharacters(chars);
        // Auto-highlight top suggestion
        if (chars.length > 0) {
          setSelected(chars[0].name);
        }
      } catch (err) {
        const msg = err.response?.data?.detail || "Failed to detect characters.";
        toast.error(msg);
      }
      setLoading(false);
    }
    detect();
  }, [project.id]);

  const handleConfirm = useCallback(async () => {
    const name = showManual ? manualName.trim().toUpperCase() : selected;
    if (!name) {
      toast.error("Please select or enter a character name.");
      return;
    }
    setSaving(true);
    try {
      await axios.put(`${API}/projects/${project.id}`, {
        selected_character: name,
      });
      toast.success(`Playing: ${name}`);
      onCharacterSelected?.(name);
    } catch {
      toast.error("Failed to save character selection.");
    }
    setSaving(false);
  }, [selected, showManual, manualName, project.id, onCharacterSelected]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="character-loading">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-28" data-testid="character-select">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-zinc-400 hover:text-zinc-200 gap-1 px-2 -ml-2"
            data-testid="character-back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-zinc-100 truncate">
              Who are you playing?
            </h1>
            <p className="text-[11px] text-zinc-500">
              {characters.length} character{characters.length !== 1 ? "s" : ""} detected
            </p>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 mt-5">
        {characters.length === 0 && !showManual ? (
          <div className="text-center py-12" data-testid="no-characters">
            <User className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm mb-1">No characters detected</p>
            <p className="text-zinc-600 text-xs mb-4">
              The script may not have standard character cues.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowManual(true)}
              className="border-zinc-700 text-zinc-300"
              data-testid="enter-manually-empty-btn"
            >
              <PenLine className="w-3.5 h-3.5 mr-1.5" />
              Enter Manually
            </Button>
          </div>
        ) : (
          <>
            {/* Character list */}
            <div className="space-y-2" data-testid="character-list">
              {characters.map((char, i) => {
                const isSelected = !showManual && selected === char.name;
                const isTop = i === 0;
                return (
                  <motion.button
                    key={char.name}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    onClick={() => {
                      setSelected(char.name);
                      setShowManual(false);
                    }}
                    data-testid={`character-option-${i}`}
                    className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all text-left ${
                      isSelected
                        ? "bg-amber-500/10 border-amber-500/40 ring-1 ring-amber-500/20"
                        : "bg-zinc-950 border-zinc-800 hover:border-zinc-700"
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      isSelected ? "bg-amber-500/20" : "bg-zinc-900"
                    }`}>
                      {isSelected ? (
                        <Check className="w-4 h-4 text-amber-400" />
                      ) : (
                        <User className="w-4 h-4 text-zinc-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium truncate ${
                        isSelected ? "text-amber-300" : "text-zinc-200"
                      }`}>
                        {char.name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-zinc-500 flex items-center gap-1">
                          <Hash className="w-3 h-3" />
                          {char.line_count} line{char.line_count !== 1 ? "s" : ""}
                        </span>
                        {isTop && (
                          <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px] px-1.5 py-0">
                            Top
                          </Badge>
                        )}
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </div>

            {/* Manual entry toggle */}
            {!showManual ? (
              <button
                onClick={() => { setShowManual(true); setSelected(null); }}
                className="w-full mt-3 flex items-center gap-3 px-4 py-3.5 rounded-xl border border-dashed border-zinc-800 hover:border-zinc-700 text-left transition-colors"
                data-testid="enter-manually-btn"
              >
                <div className="w-9 h-9 rounded-lg bg-zinc-900 flex items-center justify-center shrink-0">
                  <PenLine className="w-4 h-4 text-zinc-500" />
                </div>
                <p className="text-sm text-zinc-400">Enter character name manually</p>
              </button>
            ) : (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-3 p-4 rounded-xl border border-amber-500/30 bg-amber-500/5"
                data-testid="manual-entry"
              >
                <label className="text-xs text-zinc-400 mb-1.5 block">Character name</label>
                <Input
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="e.g. ALEX"
                  className="bg-zinc-950 border-zinc-700 text-zinc-200 h-11 text-sm"
                  autoFocus
                  data-testid="manual-name-input"
                />
                <button
                  onClick={() => { setShowManual(false); if (characters.length > 0) setSelected(characters[0].name); }}
                  className="text-xs text-zinc-500 hover:text-zinc-300 mt-2 transition-colors"
                  data-testid="cancel-manual-btn"
                >
                  Cancel — pick from list
                </button>
              </motion.div>
            )}
          </>
        )}
      </div>

      {/* Bottom action bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#09090b]/95 backdrop-blur-md border-t border-zinc-900 px-4 py-4">
        <div className="max-w-lg mx-auto">
          <Button
            onClick={handleConfirm}
            disabled={saving || (!selected && !(showManual && manualName.trim()))}
            className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm gap-1.5 disabled:opacity-40"
            data-testid="confirm-character-btn"
          >
            <Check className="w-4 h-4" />
            {saving
              ? "Saving..."
              : showManual && manualName.trim()
                ? `Confirm: ${manualName.trim().toUpperCase()}`
                : selected
                  ? `Confirm: ${selected}`
                  : "Select a character"}
          </Button>
        </div>
      </div>
    </div>
  );
}
