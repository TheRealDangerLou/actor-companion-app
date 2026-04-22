import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  ArrowLeft, Loader2, RefreshCw,
  Target, Zap, ShieldAlert, FileText, ChevronDown, ChevronRight,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BreakdownView({ project, onBack, onChangeCharacter }) {
  const [sections, setSections] = useState([]);
  const [coachData, setCoachData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [coachLoading, setCoachLoading] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailCollapsed, setDetailCollapsed] = useState({});

  const charUpper = (project.selected_character || "").toUpperCase();

  // Load both coaching AND sections in parallel on mount
  useEffect(() => {
    async function load() {
      const [coachResp, sectionsResp] = await Promise.allSettled([
        axios.post(`${API}/projects/${project.id}/quick-coach`),
        axios.post(`${API}/projects/${project.id}/extract-breakdown`),
      ]);

      if (coachResp.status === "fulfilled") {
        setCoachData(coachResp.value.data);
      }
      if (sectionsResp.status === "fulfilled") {
        setSections(sectionsResp.value.data.sections || []);
      }

      // If coach failed but sections loaded, still show sections
      if (coachResp.status === "rejected" && sectionsResp.status === "rejected") {
        toast.error("Failed to load audition data.");
      }

      setLoading(false);
    }
    load();
  }, [project.id]);

  const handleRegenerate = useCallback(async () => {
    setCoachLoading(true);
    try {
      const resp = await axios.post(`${API}/projects/${project.id}/quick-coach`, { force: true });
      setCoachData(resp.data);
      toast.success("Coaching refreshed.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Regeneration failed.");
    }
    setCoachLoading(false);
  }, [project.id]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3" data-testid="breakdown-loading">
        <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
        <p className="text-xs text-zinc-500">Preparing your audition...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-6" data-testid="breakdown-view">
      {/* Compact header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-2.5">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <Button
            variant="ghost" size="sm" onClick={onBack}
            className="text-zinc-400 hover:text-zinc-200 px-2 -ml-2"
            data-testid="breakdown-back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-zinc-100 truncate">{project.title}</h1>
            <p className="text-[11px] text-zinc-500">{charUpper}</p>
          </div>
          <button
            onClick={onChangeCharacter}
            className="text-[11px] text-amber-400 hover:text-amber-300 transition-colors shrink-0"
            data-testid="breakdown-change-char"
          >
            Change
          </button>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 pt-4">
        {/* === PRIMARY: Coaching (the decision layer) === */}
        {coachData ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-4"
            data-testid="coach-primary"
          >
            {/* Casting Intent — one punchy line */}
            {coachData.casting_intent && (
              <div data-testid="primary-casting-intent">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Target className="w-3.5 h-3.5 text-blue-400" />
                  <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">What they want</p>
                </div>
                <p className="text-[15px] text-zinc-200 leading-relaxed font-medium">
                  {coachData.casting_intent}
                </p>
              </div>
            )}

            {/* Format note — if relevant */}
            {coachData.format_note && (
              <div className="bg-blue-500/5 border border-blue-500/15 rounded-lg px-3 py-2" data-testid="primary-format-note">
                <p className="text-[12px] text-blue-300 font-medium">{coachData.format_note}</p>
              </div>
            )}

            {/* How to Play It — actionable bullets */}
            {coachData.how_to_play_it && (
              <div data-testid="primary-how-to-play">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">Your direction</p>
                </div>
                <div className="space-y-1">
                  {coachData.how_to_play_it.split("\n").filter(l => l.trim()).map((line, i) => (
                    <p key={i} className="text-[13px] text-zinc-300 leading-snug">
                      {line.trim().startsWith("-") ? line.trim() : `- ${line.trim()}`}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* What to Avoid */}
            {coachData.what_to_avoid && (
              <div className="bg-red-500/5 border border-red-500/10 rounded-xl px-3.5 py-2.5" data-testid="primary-avoid">
                <div className="flex items-center gap-1.5 mb-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                  <p className="text-[10px] font-mono text-red-400/70 uppercase tracking-wider">Avoid</p>
                </div>
                <p className="text-[13px] text-zinc-400 leading-relaxed">
                  {coachData.what_to_avoid}
                </p>
              </div>
            )}

            {/* Takes — immediately visible */}
            {coachData.takes && coachData.takes.length > 0 && (
              <div data-testid="primary-takes">
                <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-2">Takes</p>
                <div className="space-y-2">
                  {coachData.takes.map((take, i) => (
                    <div
                      key={i}
                      className="bg-zinc-950 border border-zinc-800/60 rounded-xl px-3.5 py-3"
                      data-testid={`primary-take-${i}`}
                    >
                      <p className="text-[12px] font-semibold text-amber-400 mb-0.5">{take.label}</p>
                      <p className="text-[13px] text-zinc-300 leading-snug">{take.direction}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Regenerate */}
            <div className="flex justify-center pt-1">
              <button
                onClick={handleRegenerate}
                disabled={coachLoading}
                className="text-[11px] text-zinc-600 hover:text-zinc-400 flex items-center gap-1 transition-colors"
                data-testid="coach-regenerate-btn"
              >
                {coachLoading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                {coachLoading ? "Refreshing..." : "Regenerate coaching"}
              </button>
            </div>
          </motion.div>
        ) : (
          /* Coach failed to load — show a retry option */
          <div className="text-center py-8" data-testid="coach-failed">
            <p className="text-zinc-500 text-sm mb-3">Coaching unavailable</p>
            <Button
              variant="outline" size="sm"
              onClick={handleRegenerate}
              disabled={coachLoading}
              className="border-zinc-700 text-zinc-300"
              data-testid="coach-retry-btn"
            >
              {coachLoading ? "Loading..." : "Try again"}
            </Button>
          </div>
        )}

        {/* === SECONDARY: Raw breakdown details (collapsible) === */}
        {sections.length > 0 && (
          <div className="mt-6 border-t border-zinc-900 pt-4" data-testid="breakdown-details">
            <button
              onClick={() => setDetailsOpen((v) => !v)}
              className="w-full flex items-center gap-2 mb-3"
              data-testid="details-toggle"
            >
              {detailsOpen ? (
                <ChevronDown className="w-3.5 h-3.5 text-zinc-600" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
              )}
              <FileText className="w-3.5 h-3.5 text-zinc-600" />
              <span className="text-[11px] text-zinc-500 font-medium">
                Full Breakdown ({sections.length} section{sections.length !== 1 ? "s" : ""})
              </span>
            </button>

            {detailsOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="space-y-2 overflow-hidden"
              >
                {sections.map((section, i) => (
                  <div
                    key={i}
                    className="bg-zinc-950/50 border border-zinc-800/40 rounded-lg overflow-hidden"
                    data-testid={`detail-section-${i}`}
                  >
                    <button
                      onClick={() => setDetailCollapsed((p) => ({ ...p, [i]: !p[i] }))}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left"
                    >
                      {detailCollapsed[i] ? (
                        <ChevronRight className="w-3 h-3 text-zinc-700 shrink-0" />
                      ) : (
                        <ChevronDown className="w-3 h-3 text-zinc-700 shrink-0" />
                      )}
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider truncate">
                        {section.label}
                      </span>
                    </button>
                    {!detailCollapsed[i] && (
                      <div className="px-3 pb-2.5 pt-0">
                        <p className="text-[12px] text-zinc-500 leading-relaxed whitespace-pre-wrap">
                          {section.content}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
