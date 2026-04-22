import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Loader2, Sparkles, X, RefreshCw,
  Target, Zap, ShieldAlert, FileText, ChevronDown, ChevronRight,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BreakdownView({ project, onBack, onChangeCharacter }) {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [coachOpen, setCoachOpen] = useState(false);
  const [coachData, setCoachData] = useState(null);
  const [coachLoading, setCoachLoading] = useState(false);
  const [collapsed, setCollapsed] = useState({});

  const charUpper = (project.selected_character || "").toUpperCase();

  useEffect(() => {
    async function load() {
      try {
        const resp = await axios.post(`${API}/projects/${project.id}/extract-breakdown`);
        setSections(resp.data.sections || []);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load breakdown.");
      }
      setLoading(false);
    }
    load();
  }, [project.id]);

  const toggleSection = (idx) => {
    setCollapsed((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const fetchCoach = useCallback(async (force = false) => {
    setCoachLoading(true);
    try {
      const resp = await axios.post(`${API}/projects/${project.id}/quick-coach`, { force });
      setCoachData(resp.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Coaching failed.");
      if (!force) setCoachOpen(false);
    }
    setCoachLoading(false);
  }, [project.id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="breakdown-loading">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" data-testid="breakdown-view">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost" size="sm" onClick={onBack}
              className="text-zinc-400 hover:text-zinc-200 px-2 -ml-2"
              data-testid="breakdown-back-btn"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-semibold text-zinc-100 truncate">{project.title}</h1>
              <div className="flex items-center gap-2">
                <p className="text-[11px] text-zinc-500">{charUpper}</p>
                <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-[9px]">
                  Breakdown
                </Badge>
              </div>
            </div>
            <button
              onClick={onChangeCharacter}
              className="text-[11px] text-amber-400 hover:text-amber-300 transition-colors shrink-0"
              data-testid="breakdown-change-char"
            >
              Change
            </button>
          </div>
        </div>
      </header>

      {/* Sections */}
      <div className="max-w-lg mx-auto px-4 pt-4 pb-20" data-testid="breakdown-sections">
        {sections.length === 0 ? (
          <div className="text-center py-12" data-testid="breakdown-empty-sections">
            <FileText className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">No structured sections found.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sections.map((section, i) => (
              <div
                key={i}
                className="bg-zinc-950 border border-zinc-800/60 rounded-xl overflow-hidden"
                data-testid={`breakdown-section-${i}`}
              >
                <button
                  onClick={() => toggleSection(i)}
                  className="w-full flex items-center gap-2 px-4 py-3 text-left"
                  data-testid={`breakdown-section-toggle-${i}`}
                >
                  {collapsed[i] ? (
                    <ChevronRight className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                  )}
                  <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wide flex-1 truncate">
                    {section.label}
                  </span>
                </button>
                {!collapsed[i] && (
                  <div className="px-4 pb-3 pt-0">
                    <p className="text-[13px] text-zinc-400 leading-relaxed whitespace-pre-wrap">
                      {section.content}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Coach FAB */}
      {!coachOpen && (
        <button
          onClick={async () => {
            setCoachOpen(true);
            if (!coachData) await fetchCoach();
          }}
          className="fixed bottom-20 right-4 z-50 w-11 h-11 rounded-full bg-amber-500 hover:bg-amber-600 text-black flex items-center justify-center shadow-lg shadow-amber-500/20 transition-transform hover:scale-105"
          data-testid="breakdown-coach-fab"
        >
          <Sparkles className="w-5 h-5" />
        </button>
      )}

      {/* Quick Coach Panel */}
      <AnimatePresence>
        {coachOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCoachOpen(false)}
              className="fixed inset-0 z-50 bg-black/60"
              data-testid="breakdown-coach-backdrop"
            />
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 300 }}
              className="fixed bottom-0 left-0 right-0 z-50 max-h-[85vh] overflow-y-auto bg-[#0c0c0f] border-t border-zinc-800 rounded-t-2xl"
              data-testid="breakdown-coach-panel"
            >
              <div className="max-w-lg mx-auto px-4 pt-4 pb-8">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <h2 className="text-sm font-semibold text-zinc-100">Quick Coach</h2>
                    <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-[9px]">
                      Behavioral
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    {coachData && !coachLoading && (
                      <button
                        onClick={async () => {
                          await fetchCoach(true);
                          toast.success("Coaching regenerated.");
                        }}
                        className="text-[11px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors"
                        data-testid="breakdown-coach-regenerate"
                      >
                        <RefreshCw className="w-3 h-3" /> Regenerate
                      </button>
                    )}
                    <button
                      onClick={() => setCoachOpen(false)}
                      className="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
                      data-testid="breakdown-coach-close"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {coachLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3" data-testid="breakdown-coach-loading">
                    <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                    <p className="text-xs text-zinc-500">Analyzing your breakdown...</p>
                  </div>
                ) : coachData ? (
                  <div className="space-y-4" data-testid="breakdown-coach-content">
                    <CoachBlock icon={<Target className="w-3.5 h-3.5 text-blue-400" />} label="Casting Intent" text={coachData.casting_intent} testId="bd-coach-intent" />
                    <CoachBlock icon={<Zap className="w-3.5 h-3.5 text-amber-400" />} label="How to Play It" text={coachData.how_to_play_it} testId="bd-coach-play" />
                    <CoachBlock icon={<ShieldAlert className="w-3.5 h-3.5 text-red-400" />} label="What to Avoid" text={coachData.what_to_avoid} testId="bd-coach-avoid" />
                    {coachData.takes && coachData.takes.length > 0 && (
                      <div data-testid="bd-coach-takes">
                        <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-2">Takes</p>
                        <div className="space-y-2">
                          {coachData.takes.map((take, i) => (
                            <div key={i} className="bg-zinc-950 border border-zinc-800/60 rounded-lg px-3 py-2.5" data-testid={`bd-coach-take-${i}`}>
                              <p className="text-[11px] font-semibold text-amber-400/80 mb-0.5">{take.label}</p>
                              <p className="text-[13px] text-zinc-300 leading-snug">{take.direction}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

function CoachBlock({ icon, label, text, testId }) {
  if (!text) return null;
  return (
    <div data-testid={testId}>
      <div className="flex items-center gap-1.5 mb-1">
        {icon}
        <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-[13px] text-zinc-300 leading-relaxed">{text}</p>
    </div>
  );
}
