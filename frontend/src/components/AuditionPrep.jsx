import { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import {
  Loader2, RefreshCw, CheckSquare, Shirt, Camera, Eye, Volume2,
  ChevronDown, ChevronRight,
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuditionPrep({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const resp = await axios.post(`${API}/projects/${projectId}/prep-generation`);
        setData(resp.data);
      } catch {}
      setLoading(false);
    }
    load();
  }, [projectId]);

  const handleRegenerate = useCallback(async () => {
    setRegenerating(true);
    try {
      const resp = await axios.post(`${API}/projects/${projectId}/prep-generation`, { force: true });
      setData(resp.data);
      toast.success("Prep refreshed.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Regeneration failed.");
    }
    setRegenerating(false);
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 justify-center" data-testid="prep-gen-loading">
        <Loader2 className="w-4 h-4 animate-spin text-zinc-600" />
        <span className="text-xs text-zinc-600">Generating prep...</span>
      </div>
    );
  }

  if (!data) return null;

  const setup = data.self_tape_setup || {};

  return (
    <div className="border-t border-zinc-900 pt-4 mt-5" data-testid="audition-prep">
      {/* Section header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 mb-3"
        data-testid="prep-toggle"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-zinc-600" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
        )}
        <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Audition Prep</span>
      </button>

      {expanded && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-4"
          data-testid="prep-content"
        >
          {/* Wardrobe */}
          {data.wardrobe && data.wardrobe.length > 0 && (
            <div data-testid="prep-wardrobe">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Shirt className="w-3.5 h-3.5 text-violet-400" />
                <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">Wardrobe</p>
              </div>
              <div className="space-y-1">
                {data.wardrobe.map((item, i) => (
                  <p key={i} className="text-[13px] text-zinc-300 leading-snug" data-testid={`wardrobe-item-${i}`}>
                    {item.startsWith("-") || item.startsWith("•") ? item : `- ${item}`}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Self-Tape Setup */}
          {(setup.framing || setup.backdrop || setup.eyeline || setup.energy_note) && (
            <div data-testid="prep-self-tape">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Camera className="w-3.5 h-3.5 text-cyan-400" />
                <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">Self-Tape Setup</p>
              </div>
              <div className="grid grid-cols-1 gap-1.5">
                {setup.framing && (
                  <div className="flex items-start gap-2" data-testid="setup-framing">
                    <Badge className="bg-zinc-900 text-zinc-500 border-zinc-800 text-[9px] mt-0.5 shrink-0">Frame</Badge>
                    <p className="text-[12px] text-zinc-400 leading-snug">{setup.framing}</p>
                  </div>
                )}
                {setup.backdrop && (
                  <div className="flex items-start gap-2" data-testid="setup-backdrop">
                    <Badge className="bg-zinc-900 text-zinc-500 border-zinc-800 text-[9px] mt-0.5 shrink-0">BG</Badge>
                    <p className="text-[12px] text-zinc-400 leading-snug">{setup.backdrop}</p>
                  </div>
                )}
                {setup.eyeline && (
                  <div className="flex items-start gap-2" data-testid="setup-eyeline">
                    <Eye className="w-3 h-3 text-zinc-600 mt-0.5 shrink-0" />
                    <p className="text-[12px] text-zinc-400 leading-snug">{setup.eyeline}</p>
                  </div>
                )}
                {setup.energy_note && (
                  <div className="flex items-start gap-2" data-testid="setup-energy">
                    <Volume2 className="w-3 h-3 text-zinc-600 mt-0.5 shrink-0" />
                    <p className="text-[12px] text-zinc-400 leading-snug">{setup.energy_note}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action Items */}
          {data.action_items && data.action_items.length > 0 && (
            <div data-testid="prep-actions">
              <div className="flex items-center gap-1.5 mb-1.5">
                <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
                <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">Action Items</p>
              </div>
              <div className="space-y-1.5">
                {data.action_items.map((item, i) => (
                  <div key={i} className="flex items-start gap-2" data-testid={`action-item-${i}`}>
                    <span className="text-[11px] text-zinc-600 font-mono mt-px shrink-0">{i + 1}.</span>
                    <p className="text-[13px] text-zinc-300 leading-snug">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regenerate */}
          <div className="flex justify-center pt-1">
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="text-[11px] text-zinc-600 hover:text-zinc-400 flex items-center gap-1 transition-colors"
              data-testid="prep-regenerate-btn"
            >
              {regenerating ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <RefreshCw className="w-3 h-3" />
              )}
              {regenerating ? "Refreshing..." : "Regenerate prep"}
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
