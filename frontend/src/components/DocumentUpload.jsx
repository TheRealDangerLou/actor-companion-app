import { useState, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Upload, Camera, FileText, Image as ImageIcon, X, Loader2, Type, Trash2,
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DOC_TYPES = [
  { value: "sides", label: "Sides" },
  { value: "instructions", label: "Instructions" },
  { value: "wardrobe", label: "Wardrobe" },
  { value: "notes", label: "Notes" },
  { value: "reference", label: "Reference" },
  { value: "unknown", label: "Unknown" },
];

const TYPE_COLORS = {
  sides: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  instructions: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  wardrobe: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  notes: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  reference: "bg-green-500/10 text-green-400 border-green-500/20",
  unknown: "bg-zinc-700/30 text-zinc-500 border-zinc-700/30",
};

export default function DocumentUpload({ project, onDocumentsChanged, onBack }) {
  const [documents, setDocuments] = useState(project?.documents || []);
  const [uploading, setUploading] = useState(false);
  const [showPasteInput, setShowPasteInput] = useState(false);
  const [pastedText, setPastedText] = useState("");
  const [pasteType, setPasteType] = useState("unknown");
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const projectId = project?.id;
  const canUpload = documents.length < 5;

  const handleFileUpload = useCallback(async (files) => {
    if (!files || files.length === 0) return;
    const remaining = 5 - documents.length;
    const toUpload = Array.from(files).slice(0, remaining);

    setUploading(true);
    let newDocs = [];

    for (const file of toUpload) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("doc_type", "unknown");

        const resp = await axios.post(`${API}/projects/${projectId}/documents`, formData, {
          timeout: 120000,
        });
        newDocs.push(resp.data);
        toast.success(`Uploaded: ${file.name}`);
      } catch (err) {
        const msg = err.response?.data?.detail || "Upload failed";
        toast.error(`${file.name}: ${msg}`);
      }
    }

    if (newDocs.length > 0) {
      const updated = [...documents, ...newDocs];
      setDocuments(updated);
      onDocumentsChanged?.(updated);
    }
    setUploading(false);
  }, [documents, projectId, onDocumentsChanged]);

  const handlePaste = useCallback(async () => {
    const text = pastedText.trim();
    if (!text) {
      toast.error("Enter some text first.");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("pasted_text", text);
      formData.append("doc_type", pasteType);

      const resp = await axios.post(`${API}/projects/${projectId}/documents`, formData, {
        timeout: 30000,
      });
      const updated = [...documents, resp.data];
      setDocuments(updated);
      onDocumentsChanged?.(updated);
      setPastedText("");
      setPasteType("unknown");
      setShowPasteInput(false);
      toast.success("Text saved as document.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save text.");
    }
    setUploading(false);
  }, [pastedText, pasteType, documents, projectId, onDocumentsChanged]);

  const handleDeleteDoc = useCallback(async (docId) => {
    try {
      await axios.delete(`${API}/documents/${docId}`);
      const updated = documents.filter((d) => d.id !== docId);
      setDocuments(updated);
      onDocumentsChanged?.(updated);
      toast.success("Document removed.");
    } catch {
      toast.error("Failed to delete document.");
    }
  }, [documents, onDocumentsChanged]);

  const handleTypeChange = useCallback(async (docId, newType) => {
    try {
      await axios.put(`${API}/documents/${docId}/type`, { type: newType });
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? { ...d, type: newType } : d))
      );
    } catch {
      toast.error("Failed to update type.");
    }
  }, []);

  return (
    <div className="min-h-screen px-4 pb-24 pt-6 max-w-lg mx-auto" data-testid="document-upload">
      {/* Header */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="text-zinc-400 hover:text-zinc-200 gap-1 px-2 mb-4 -ml-2"
        data-testid="upload-back-btn"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </Button>

      <div className="mb-6">
        <h1 className="text-lg font-bold text-zinc-100">{project?.title || "Upload Documents"}</h1>
        <p className="text-xs text-zinc-500 mt-0.5">
          Upload your sides, instructions, and other materials. ({documents.length}/5 documents)
        </p>
      </div>

      {/* Upload actions */}
      {canUpload && (
        <div className="space-y-3 mb-6">
          {/* File + Camera row */}
          <div className="flex gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex-1 h-24 rounded-xl border-2 border-dashed border-zinc-700 hover:border-amber-500/40 bg-zinc-900/40 flex flex-col items-center justify-center gap-2 transition-colors disabled:opacity-50"
              data-testid="file-upload-btn"
            >
              <Upload className="w-5 h-5 text-zinc-400" />
              <span className="text-xs text-zinc-400">Browse Files</span>
            </button>
            <button
              onClick={() => cameraInputRef.current?.click()}
              disabled={uploading}
              className="flex-1 h-24 rounded-xl border-2 border-dashed border-zinc-700 hover:border-amber-500/40 bg-zinc-900/40 flex flex-col items-center justify-center gap-2 transition-colors disabled:opacity-50"
              data-testid="camera-upload-btn"
            >
              <Camera className="w-5 h-5 text-zinc-400" />
              <span className="text-xs text-zinc-400">Take Photo</span>
            </button>
          </div>

          {/* Paste text toggle */}
          <button
            onClick={() => setShowPasteInput(!showPasteInput)}
            disabled={uploading}
            className="w-full h-12 rounded-xl border border-zinc-800 bg-zinc-900/40 flex items-center justify-center gap-2 text-xs text-zinc-400 hover:border-zinc-700 transition-colors disabled:opacity-50"
            data-testid="paste-text-btn"
          >
            <Type className="w-4 h-4" />
            Paste Text
          </button>

          {/* Hidden file inputs */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.heic,.heif,.webp,.txt"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
            data-testid="file-input"
          />
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
            data-testid="camera-input"
          />
        </div>
      )}

      {/* Paste text area */}
      <AnimatePresence>
        {showPasteInput && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mb-6"
          >
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
              <Textarea
                placeholder="Paste your script text here..."
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                className="min-h-[160px] bg-zinc-950 border-zinc-800 text-zinc-200 text-sm resize-y"
                data-testid="paste-textarea"
              />
              <div className="flex items-center gap-2">
                <select
                  value={pasteType}
                  onChange={(e) => setPasteType(e.target.value)}
                  className="h-9 rounded-lg bg-zinc-800 border-zinc-700 text-zinc-300 text-xs px-2"
                  data-testid="paste-type-select"
                >
                  {DOC_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <div className="flex-1" />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => { setShowPasteInput(false); setPastedText(""); }}
                  className="text-zinc-500 text-xs h-8"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handlePaste}
                  disabled={uploading || !pastedText.trim()}
                  className="bg-amber-500 hover:bg-amber-600 text-black text-xs h-8 font-semibold"
                  data-testid="paste-submit-btn"
                >
                  {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Add Text"}
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Uploading indicator */}
      {uploading && (
        <div className="flex items-center gap-2 mb-4 text-sm text-zinc-400" data-testid="upload-spinner">
          <Loader2 className="w-4 h-4 animate-spin" />
          Processing file...
        </div>
      )}

      {/* Document list */}
      {documents.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mb-2">
            Documents
          </p>
          <AnimatePresence>
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -50 }}
                className="bg-zinc-900/60 border border-zinc-800/60 rounded-xl p-3"
                data-testid={`doc-card-${doc.id}`}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0 mt-0.5">
                    {doc.extraction_method === "paste" ? (
                      <Type className="w-4 h-4 text-zinc-400" />
                    ) : doc.filename?.toLowerCase().endsWith(".pdf") ? (
                      <FileText className="w-4 h-4 text-red-400" />
                    ) : (
                      <ImageIcon className="w-4 h-4 text-blue-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-zinc-200 truncate font-medium">
                      {doc.filename || "Pasted text"}
                    </p>
                    <p className="text-[11px] text-zinc-600 mt-0.5">
                      {doc.char_count?.toLocaleString() || "?"} chars
                      {doc.extraction_method ? ` · ${doc.extraction_method}` : ""}
                      {doc.suggested_type && doc.suggested_type !== "unknown" && doc.type === doc.suggested_type
                        ? " · auto-detected"
                        : ""}
                    </p>
                    {/* Type selector */}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {DOC_TYPES.map((t) => (
                        <button
                          key={t.value}
                          onClick={() => handleTypeChange(doc.id, t.value)}
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide border transition-colors ${
                            doc.type === t.value
                              ? TYPE_COLORS[t.value]
                              : "border-transparent text-zinc-600 hover:text-zinc-400"
                          }`}
                          data-testid={`doc-type-${doc.id}-${t.value}`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteDoc(doc.id)}
                    className="p-1.5 text-zinc-600 hover:text-red-400 transition-colors rounded shrink-0"
                    data-testid={`delete-doc-${doc.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Empty state */}
      {documents.length === 0 && !uploading && (
        <div className="text-center py-12" data-testid="no-docs-state">
          <p className="text-zinc-500 text-sm">No documents yet.</p>
          <p className="text-zinc-600 text-xs mt-1">Upload your sides, instructions, or reference materials.</p>
        </div>
      )}

      {/* Continue button */}
      {documents.length > 0 && (
        <div className="fixed bottom-6 left-4 right-4 max-w-lg mx-auto">
          <Button
            onClick={() => onDocumentsChanged?.(documents, true)}
            className="w-full h-14 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm shadow-lg shadow-amber-500/10"
            data-testid="continue-btn"
          >
            Continue with {documents.length} Document{documents.length !== 1 ? "s" : ""}
          </Button>
        </div>
      )}
    </div>
  );
}
