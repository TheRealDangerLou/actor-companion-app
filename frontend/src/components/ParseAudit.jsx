import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, AlertTriangle, Check, ArrowLeft } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ParseAudit() {
  const [text, setText] = useState("");
  const [characterName, setCharacterName] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runAudit = async () => {
    if (!text.trim() || !characterName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/debug/parse-audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, character_name: characterName }),
      });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: e.message });
    }
    setLoading(false);
  };

  const lineColor = (type) => {
    switch (type) {
      case "speaker": return "text-amber-400";
      case "captured": return "text-emerald-400";
      case "uncaptured": return "text-red-400 bg-red-500/10";
      case "heading": return "text-blue-400";
      case "parenthetical": return "text-zinc-500 italic";
      case "blank": return "text-zinc-800";
      default: return "text-zinc-400";
    }
  };

  const typeBadge = (ann) => {
    switch (ann.type) {
      case "speaker":
        return <Badge variant="outline" className={`text-[9px] px-1 py-0 ${ann.is_target_character ? "border-amber-500/40 text-amber-500" : "border-zinc-700 text-zinc-500"}`}>
          {ann.is_target_character ? "YOUR CHARACTER" : "SPEAKER"}
        </Badge>;
      case "captured":
        return <Badge variant="outline" className="text-[9px] px-1 py-0 border-emerald-500/40 text-emerald-500">CAPTURED</Badge>;
      case "uncaptured":
        return <Badge variant="outline" className="text-[9px] px-1 py-0 border-red-500/40 text-red-500">MISSED</Badge>;
      case "heading":
        return <Badge variant="outline" className="text-[9px] px-1 py-0 border-blue-500/40 text-blue-500">HEADING</Badge>;
      case "parenthetical":
        return <Badge variant="outline" className="text-[9px] px-1 py-0 border-zinc-600 text-zinc-500">PAREN</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 p-4 sm:p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <a href="/" className="text-zinc-500 hover:text-zinc-300 transition-colors" data-testid="audit-back">
            <ArrowLeft className="w-4 h-4" />
          </a>
          <h1 className="font-display text-lg font-bold text-zinc-300">Parse Audit</h1>
          <Badge variant="outline" className="text-[9px] border-zinc-700 text-zinc-600">DEBUG</Badge>
        </div>

        {/* Input */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Scene Text</label>
            <textarea
              data-testid="audit-text-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste scene text here..."
              className="w-full h-48 bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-sm font-mono text-zinc-300 placeholder-zinc-700 resize-none focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Character Name</label>
              <input
                data-testid="audit-character-input"
                value={characterName}
                onChange={(e) => setCharacterName(e.target.value)}
                placeholder="e.g. FELIX"
                className="w-full bg-zinc-900/50 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300 placeholder-zinc-700 focus:outline-none focus:border-zinc-600"
              />
            </div>
            <Button
              data-testid="audit-run-button"
              onClick={runAudit}
              disabled={loading || !text.trim() || !characterName.trim()}
              className="bg-amber-500 hover:bg-amber-600 text-black font-bold gap-2 h-10"
            >
              <Search className="w-4 h-4" />
              {loading ? "Auditing..." : "Run Audit"}
            </Button>
          </div>
        </div>

        {/* Results */}
        {result && !result.error && (
          <div className="space-y-4">
            {/* Summary bar */}
            <div className="flex items-center gap-4 p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg" data-testid="audit-summary">
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-500" />
                <span className="text-sm text-zinc-300">{result.extracted_line_count} lines captured</span>
              </div>
              {result.uncaptured_count > 0 && (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-sm text-red-400">{result.uncaptured_count} lines uncaptured</span>
                </div>
              )}
              {result.uncaptured_count === 0 && (
                <span className="text-sm text-emerald-400">All text accounted for</span>
              )}
            </div>

            {/* Extracted lines */}
            <div className="p-3 bg-zinc-900/30 border border-zinc-800 rounded-lg">
              <h3 className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Extracted Lines ({result.extracted_line_count})</h3>
              <div className="space-y-1">
                {result.extracted_lines.map((line, i) => (
                  <p key={i} className="text-sm text-emerald-400 font-mono" data-testid={`extracted-line-${i}`}>
                    {i + 1}. {line}
                  </p>
                ))}
                {result.extracted_lines.length === 0 && (
                  <p className="text-sm text-zinc-600">No lines extracted.</p>
                )}
              </div>
            </div>

            {/* Uncaptured lines (mismatches) */}
            {result.uncaptured_count > 0 && (
              <div className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                <h3 className="text-xs text-red-400 uppercase tracking-widest mb-2">
                  Uncaptured Lines ({result.uncaptured_count})
                </h3>
                <div className="space-y-1">
                  {result.uncaptured_lines.map((u, i) => (
                    <p key={i} className="text-sm text-red-400 font-mono" data-testid={`uncaptured-line-${i}`}>
                      L{u.line_num}: {u.text}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Full annotated view */}
            <div className="p-3 bg-zinc-900/30 border border-zinc-800 rounded-lg">
              <h3 className="text-xs text-zinc-500 uppercase tracking-widest mb-3">Annotated Script</h3>
              <div className="font-mono text-xs space-y-0 leading-relaxed">
                {result.annotations.map((ann, i) => (
                  <div key={i} className={`flex items-start gap-2 px-2 py-0.5 rounded ${ann.type === "uncaptured" ? "bg-red-500/10" : ""}`}>
                    <span className="text-zinc-700 w-8 text-right shrink-0 select-none">{ann.line_num}</span>
                    <span className={`flex-1 ${lineColor(ann.type)} ${ann.type === "blank" ? "h-3" : ""}`}>
                      {ann.raw || "\u00A0"}
                    </span>
                    <span className="shrink-0 ml-2">{typeBadge(ann)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {result?.error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm text-red-400">Error: {result.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
