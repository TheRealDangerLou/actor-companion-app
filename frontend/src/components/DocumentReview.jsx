import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  ArrowLeft, ChevronLeft, ChevronRight, Edit3, Eye, RotateCcw, Check, Loader2,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DocumentReview({ project, onAllConfirmed, onBack }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedTexts, setEditedTexts] = useState({});
  const [autoCleanedTexts, setAutoCleanedTexts] = useState({});
  const [confirmedDocs, setConfirmedDocs] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const resp = await axios.post(`${API}/projects/${project.id}/clean-all`);
        const docs = resp.data.documents || [];
        setDocuments(docs);
        const edited = {};
        const autoCleaned = {};
        const confirmed = {};
        docs.forEach((d) => {
          edited[d.doc_id] = d.cleaned_text;
          autoCleaned[d.doc_id] = d.cleaned_text;
          confirmed[d.doc_id] = d.is_confirmed;
        });
        setEditedTexts(edited);
        setAutoCleanedTexts(autoCleaned);
        setConfirmedDocs(confirmed);
      } catch {
        toast.error("Failed to load documents for review.");
      }
      setLoading(false);
    }
    load();
  }, [project.id]);

  const activeDoc = documents[activeIdx] || null;
  const activeId = activeDoc?.doc_id;
  const currentText = activeId ? (editedTexts[activeId] ?? "") : "";
  const isEdited = activeId && editedTexts[activeId] !== autoCleanedTexts[activeId];
  const isConfirmed = activeId && confirmedDocs[activeId];

  const allConfirmed = documents.length > 0 && documents.every((d) => confirmedDocs[d.doc_id]);

  const handleTextChange = useCallback((val) => {
    if (!activeId) return;
    setEditedTexts((prev) => ({ ...prev, [activeId]: val }));
  }, [activeId]);

  const handleReset = useCallback(() => {
    if (!activeId) return;
    setEditedTexts((prev) => ({ ...prev, [activeId]: autoCleanedTexts[activeId] }));
    setConfirmedDocs((prev) => ({ ...prev, [activeId]: false }));
    toast.info("Reset to auto-cleaned version.");
  }, [activeId, autoCleanedTexts]);

  const handleConfirmOne = useCallback(async () => {
    if (!activeId) return;
    setSaving(true);
    try {
      await axios.post(`${API}/documents/${activeId}/confirm`, {
        cleaned_text: editedTexts[activeId],
      });
      setConfirmedDocs((prev) => ({ ...prev, [activeId]: true }));
      toast.success("Document confirmed.");
      // Auto-advance to next unconfirmed
      if (activeIdx < documents.length - 1) {
        const nextUnconfirmed = documents.findIndex(
          (d, i) => i > activeIdx && !confirmedDocs[d.doc_id]
        );
        if (nextUnconfirmed >= 0) setActiveIdx(nextUnconfirmed);
      }
    } catch {
      toast.error("Failed to confirm.");
    }
    setSaving(false);
  }, [activeId, activeIdx, documents, editedTexts, confirmedDocs]);

  const handleConfirmAll = useCallback(async () => {
    setSaving(true);
    try {
      const payload = {
        documents: documents.map((d) => ({
          doc_id: d.doc_id,
          cleaned_text: editedTexts[d.doc_id] || d.cleaned_text,
        })),
      };
      await axios.post(`${API}/projects/${project.id}/confirm-all`, payload);
      const newConfirmed = {};
      documents.forEach((d) => { newConfirmed[d.doc_id] = true; });
      setConfirmedDocs(newConfirmed);
      toast.success(`All ${documents.length} documents confirmed.`);
    } catch {
      toast.error("Failed to confirm all.");
    }
    setSaving(false);
  }, [documents, editedTexts, project.id]);

  const handleContinue = useCallback(() => {
    onAllConfirmed?.();
  }, [onAllConfirmed]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="review-loading">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!documents.length) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-zinc-400 text-sm">No documents to review.</p>
        <Button variant="outline" onClick={onBack} data-testid="review-back-empty">Go Back</Button>
      </div>
    );
  }

  const confirmedCount = documents.filter((d) => confirmedDocs[d.doc_id]).length;

  return (
    <div className="min-h-screen pb-28" data-testid="document-review">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-900 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="text-zinc-400 hover:text-zinc-200 gap-1 px-2 -ml-2"
              data-testid="review-back-btn"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-semibold text-zinc-100 truncate">
                Review & Confirm
              </h1>
              <p className="text-[11px] text-zinc-500">
                {confirmedCount}/{documents.length} confirmed
              </p>
            </div>
            {!allConfirmed && (
              <Button
                size="sm"
                onClick={handleConfirmAll}
                disabled={saving}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs h-8 gap-1"
                data-testid="confirm-all-btn"
              >
                Confirm All
              </Button>
            )}
          </div>

          {/* Document tabs */}
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              disabled={activeIdx === 0}
              onClick={() => { setActiveIdx((i) => Math.max(0, i - 1)); setEditMode(false); }}
              className="text-zinc-500 px-1.5 h-7"
              data-testid="review-prev-doc"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>

            <div className="flex-1 overflow-x-auto">
              <div className="flex gap-1.5">
                {documents.map((d, i) => (
                  <button
                    key={d.doc_id}
                    onClick={() => { setActiveIdx(i); setEditMode(false); }}
                    data-testid={`review-tab-${i}`}
                    className={`shrink-0 px-2.5 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1 ${
                      i === activeIdx
                        ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                        : confirmedDocs[d.doc_id]
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "text-zinc-500 border border-zinc-800 hover:text-zinc-300"
                    }`}
                  >
                    {confirmedDocs[d.doc_id] && <Check className="w-3 h-3" />}
                    {d.filename?.replace("pasted_text.txt", "Text").substring(0, 12) || `Doc ${i + 1}`}
                  </button>
                ))}
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              disabled={activeIdx === documents.length - 1}
              onClick={() => { setActiveIdx((i) => Math.min(documents.length - 1, i + 1)); setEditMode(false); }}
              className="text-zinc-500 px-1.5 h-7"
              data-testid="review-next-doc"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Document content */}
      {activeDoc && (
        <div className="max-w-lg mx-auto px-4 mt-4">
          {/* Doc info bar */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[10px]">
                {activeDoc.type?.toUpperCase()}
              </Badge>
              {isConfirmed && (
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]" data-testid="confirmed-badge">
                  Confirmed
                </Badge>
              )}
              {isEdited && !isConfirmed && (
                <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]" data-testid="edited-badge">
                  Edited
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditMode((e) => !e)}
                className="text-[11px] gap-1 h-7 border-zinc-700 px-2"
                data-testid="toggle-edit-btn"
              >
                {editMode ? <><Eye className="w-3 h-3" /> Preview</> : <><Edit3 className="w-3 h-3" /> Edit</>}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                className="text-[11px] gap-1 h-7 border-zinc-700 text-zinc-400 px-2"
                data-testid="reset-btn"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </Button>
            </div>
          </div>

          {/* Text content */}
          <motion.div
            key={activeDoc.doc_id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
          >
            {editMode ? (
              <Textarea
                value={currentText}
                onChange={(e) => handleTextChange(e.target.value)}
                className="min-h-[420px] font-mono text-[13px] leading-relaxed bg-zinc-950 border-zinc-800 text-zinc-200 resize-y rounded-xl"
                data-testid="review-textarea"
              />
            ) : (
              <div
                className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 min-h-[420px] overflow-y-auto"
                data-testid="review-preview"
              >
                <pre className="font-mono text-[13px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                  {currentText}
                </pre>
              </div>
            )}
          </motion.div>

          {/* Stats */}
          <div className="flex items-center gap-3 mt-2 text-[11px] text-zinc-600">
            <span>{currentText.split("\n").length} lines</span>
            <span>{currentText.length} chars</span>
          </div>
        </div>
      )}

      {/* Bottom action bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#09090b]/95 backdrop-blur-md border-t border-zinc-900 px-4 py-4">
        <div className="max-w-lg mx-auto flex gap-3">
          {!isConfirmed ? (
            <Button
              onClick={handleConfirmOne}
              disabled={saving}
              className="flex-1 h-12 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm gap-1.5"
              data-testid="confirm-doc-btn"
            >
              <Check className="w-4 h-4" />
              {saving ? "Saving..." : "Confirm This Document"}
            </Button>
          ) : allConfirmed ? (
            <Button
              onClick={handleContinue}
              className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm gap-1.5"
              data-testid="continue-btn"
            >
              Continue — All Confirmed
            </Button>
          ) : (
            <Button
              onClick={() => {
                const nextUnconfirmed = documents.findIndex((d) => !confirmedDocs[d.doc_id]);
                if (nextUnconfirmed >= 0) { setActiveIdx(nextUnconfirmed); setEditMode(false); }
              }}
              className="flex-1 h-12 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold rounded-xl text-sm"
              data-testid="next-unconfirmed-btn"
            >
              Next Unconfirmed ({confirmedCount}/{documents.length})
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
