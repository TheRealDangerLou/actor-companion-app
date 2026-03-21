import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Upload, FileText, Image, Sparkles, ArrowRight, ArrowLeft, Camera,
  ChevronDown, ChevronUp, Layers, Clock, Type, ImageIcon, CameraIcon,
} from "lucide-react";

const HERO_BG = "https://images.unsplash.com/photo-1761229660731-891484da5c35?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2OTV8MHwxfHNlYXJjaHw0fHx0aGVhdGVyJTIwc3RhZ2UlMjBzcG90bGlnaHQlMjBkYXJrfGVufDB8fHx8MTc3Mzg4ODc2Mnww&ixlib=rb-4.1.0&q=85&w=1920";

function getFileCategory(file) {
  if (!file) return null;
  const name = (file.name || "").toLowerCase();
  const type = (file.type || "").toLowerCase();
  if (name.endsWith(".pdf") || type === "application/pdf") return "pdf";
  if (type.startsWith("image/") || /\.(jpe?g|png|webp|heic|heif|gif|bmp|tiff?)$/i.test(name)) return "image";
  if (!type && file.size > 0) return "unknown-accept";
  return null;
}

const stepAnim = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 },
  transition: { duration: 0.2 },
};

export default function UploadPage({ onAnalyze, recentBreakdowns, onLoadBreakdown }) {
  const [step, setStep] = useState(1);
  const [inputType, setInputType] = useState(null); // "text" | "file" | "snap"
  const [scriptText, setScriptText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [mode, setMode] = useState("quick");
  const [showContext, setShowContext] = useState(false);
  const [context, setContext] = useState({ character: "", synopsis: "", castingNotes: "", characterDesc: "" });
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const handleFileChange = useCallback((e) => {
    const file = e?.target?.files?.[0];
    if (!file) return;
    const category = getFileCategory(file);
    if (!category) {
      toast.error("Unsupported file. Upload an image or PDF of your sides.");
      e.target.value = "";
      return;
    }
    setImageFile(file);
    if (category === "image") {
      const reader = new FileReader();
      reader.onload = (ev) => setImagePreview(ev.target.result);
      reader.readAsDataURL(file);
    } else {
      setImagePreview(null);
    }
    e.target.value = "";
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;
    const category = getFileCategory(file);
    if (!category) { toast.error("Unsupported file. Upload an image or PDF."); return; }
    setImageFile(file);
    if (category === "image") {
      const reader = new FileReader();
      reader.onload = (ev) => setImagePreview(ev.target.result);
      reader.readAsDataURL(file);
    } else { setImagePreview(null); }
  }, []);

  const clearFile = useCallback((e) => {
    if (e) e.stopPropagation();
    setImageFile(null);
    setImagePreview(null);
  }, []);

  const buildContextString = () => {
    const parts = [];
    if (context.character.trim()) parts.push(`Character I'm playing: ${context.character.trim()}`);
    if (context.synopsis.trim()) parts.push(`Project synopsis: ${context.synopsis.trim()}`);
    if (context.castingNotes.trim()) parts.push(`Notes from casting: ${context.castingNotes.trim()}`);
    if (context.characterDesc.trim()) parts.push(`Character description: ${context.characterDesc.trim()}`);
    return parts.length > 0 ? parts.join("\n\n") : "";
  };

  const handleSubmit = () => {
    const contextStr = buildContextString();
    if (inputType === "text" && scriptText.trim().length >= 10) {
      const fullText = contextStr
        ? `[CONTEXT FOR ANALYSIS]\n${contextStr}\n\n[AUDITION SIDES]\n${scriptText}`
        : scriptText;
      onAnalyze({ type: "text", text: fullText, mode });
    } else if ((inputType === "file" || inputType === "snap") && imageFile) {
      onAnalyze({ type: "image", file: imageFile, context: contextStr, mode });
    }
  };

  const canSubmit =
    (inputType === "text" && scriptText.trim().length >= 10) ||
    ((inputType === "file" || inputType === "snap") && imageFile);

  const hasContext = Object.values(context).some(v => v.trim());

  const goToStep = (s) => setStep(s);

  const selectInputType = (type) => {
    setInputType(type);
    setStep(2);
  };

  const hasInput = inputType === "text"
    ? scriptText.trim().length >= 10
    : !!imageFile;

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 py-12">
      {/* Hero background */}
      <div className="absolute inset-0 z-0">
        <img src={HERO_BG} alt="" className="w-full h-full object-cover opacity-[0.12]" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#09090b]/60 via-[#09090b]/80 to-[#09090b]" />
      </div>

      <div className="relative z-10 w-full max-w-2xl mx-auto">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-10"
        >
          <h1 data-testid="app-title" className="font-display text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white mb-4">
            Actor's <span className="text-amber-500">Companion</span>
          </h1>
          <p className="text-base md:text-lg text-zinc-400 max-w-md mx-auto leading-relaxed">
            Upload your sides. Get a breakdown you can perform in minutes.
          </p>
        </motion.div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="bg-zinc-950/60 border border-zinc-800 rounded-xl p-6 md:p-8 backdrop-blur-md"
        >
          {/* Step indicator */}
          <div className="flex items-center gap-1.5 mb-5">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-1 rounded-full transition-all duration-300 ${
                  s === step ? "bg-amber-500 flex-[2]" : s < step ? "bg-amber-500/40 flex-1" : "bg-zinc-800 flex-1"
                }`}
              />
            ))}
          </div>

          <AnimatePresence mode="wait">
            {/* ===== STEP 1: Choose input type ===== */}
            {step === 1 && (
              <motion.div key="step1" {...stepAnim}>
                <p className="text-sm text-zinc-500 mb-4">How are you bringing your sides?</p>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    data-testid="input-type-text"
                    onClick={() => selectInputType("text")}
                    className={`flex flex-col items-center gap-2 p-5 rounded-lg border transition-all hover:border-zinc-600 ${
                      inputType === "text" ? "border-amber-500/50 bg-amber-500/5" : "border-zinc-800 bg-zinc-900/30"
                    }`}
                  >
                    <Type className="w-6 h-6 text-amber-500/70" />
                    <span className="text-sm text-zinc-300 font-medium">Paste script</span>
                  </button>
                  <button
                    data-testid="input-type-file"
                    onClick={() => selectInputType("file")}
                    className={`flex flex-col items-center gap-2 p-5 rounded-lg border transition-all hover:border-zinc-600 ${
                      inputType === "file" ? "border-amber-500/50 bg-amber-500/5" : "border-zinc-800 bg-zinc-900/30"
                    }`}
                  >
                    <Upload className="w-6 h-6 text-amber-500/70" />
                    <span className="text-sm text-zinc-300 font-medium">Upload file</span>
                  </button>
                  <button
                    data-testid="input-type-snap"
                    onClick={() => selectInputType("snap")}
                    className="flex flex-col items-center gap-2 p-5 rounded-lg border border-zinc-800 bg-zinc-900/30 transition-all hover:border-zinc-600 sm:hidden col-span-2"
                  >
                    <Camera className="w-6 h-6 text-amber-500/70" />
                    <span className="text-sm text-zinc-300 font-medium">Snap your sides</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* ===== STEP 2: Input + Mode ===== */}
            {step === 2 && (
              <motion.div key="step2" {...stepAnim}>
                {/* Back */}
                <button
                  data-testid="step-back-2"
                  onClick={() => goToStep(1)}
                  className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 mb-4 transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" /> Back
                </button>

                {/* Text input */}
                {inputType === "text" && (
                  <div>
                    <textarea
                      data-testid="script-textarea"
                      value={scriptText}
                      onChange={(e) => setScriptText(e.target.value)}
                      placeholder={"Paste your audition sides here...\n\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"}
                      className="w-full h-48 md:h-56 bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 font-script text-base text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/30 focus:outline-none resize-none transition-colors"
                    />
                    <p className="text-xs text-zinc-600 mt-1.5">Dialogue, stage directions, or full scene pages</p>
                  </div>
                )}

                {/* File upload */}
                {inputType === "file" && (
                  <div
                    data-testid="image-upload-zone"
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    className={`w-full h-48 md:h-56 border-2 border-dashed rounded-lg flex flex-col items-center justify-center transition-all ${
                      dragOver ? "drag-active border-amber-500 bg-amber-500/5"
                      : imagePreview || imageFile ? "border-zinc-700 bg-zinc-900/30"
                      : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700"
                    }`}
                  >
                    {imagePreview ? (
                      <div className="relative w-full h-full p-4">
                        <img src={imagePreview} alt="Preview" className="w-full h-full object-contain rounded" />
                        <button onClick={clearFile} className="absolute top-2 right-2 bg-zinc-900/80 text-zinc-400 hover:text-white rounded-full w-8 h-8 flex items-center justify-center text-sm border border-zinc-700" data-testid="clear-image-button">x</button>
                      </div>
                    ) : imageFile ? (
                      <div className="flex flex-col items-center gap-2 p-4">
                        <FileText className="w-10 h-10 text-amber-500/60" />
                        <p className="text-sm text-zinc-300 font-medium truncate max-w-full px-4">{imageFile.name}</p>
                        <p className="text-xs text-zinc-500">{(imageFile.size / (1024 * 1024)).toFixed(1)}MB</p>
                        <button onClick={clearFile} className="text-xs text-zinc-500 hover:text-white underline mt-1" data-testid="clear-file-button">Remove</button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center cursor-pointer w-full h-full">
                        <Upload className="w-8 h-8 text-zinc-600 mb-3" />
                        <p className="text-sm text-zinc-500">Tap to upload or <span className="text-amber-500">drop file here</span></p>
                        <p className="text-xs text-zinc-600 mt-1">Images, PDFs, or photos up to 20MB</p>
                        <input ref={fileInputRef} type="file" accept="image/*,.pdf,application/pdf" onChange={handleFileChange} className="hidden" data-testid="image-upload-input" />
                      </label>
                    )}
                  </div>
                )}

                {/* Camera snap */}
                {inputType === "snap" && (
                  <div data-testid="camera-capture-zone" className="w-full h-48 md:h-56 border-2 border-dashed border-zinc-800 bg-zinc-900/30 rounded-lg flex flex-col items-center justify-center">
                    {imagePreview ? (
                      <div className="relative w-full h-full p-4">
                        <img src={imagePreview} alt="Captured" className="w-full h-full object-contain rounded" />
                        <button onClick={clearFile} className="absolute top-2 right-2 bg-zinc-900/80 text-zinc-400 hover:text-white rounded-full w-8 h-8 flex items-center justify-center text-sm border border-zinc-700" data-testid="clear-camera-image">x</button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center cursor-pointer w-full h-full">
                        <Camera className="w-10 h-10 text-amber-500/60 mb-3" />
                        <p className="text-sm text-zinc-400 font-semibold">Snap your sides</p>
                        <p className="text-xs text-zinc-600 mt-1">Opens your camera</p>
                        <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" onChange={handleFileChange} className="hidden" data-testid="camera-capture-input" />
                      </label>
                    )}
                  </div>
                )}

                {/* Mode toggle */}
                <div className="mt-5 flex items-center gap-3" data-testid="mode-toggle">
                  <button
                    onClick={() => setMode("quick")}
                    data-testid="mode-quick"
                    className={`flex-1 py-2.5 px-3 rounded-lg border text-sm font-medium transition-all ${
                      mode === "quick"
                        ? "border-amber-500/50 bg-amber-500/10 text-amber-500"
                        : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700 hover:text-zinc-400"
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Quick</span>
                    </div>
                    <p className="text-[10px] mt-0.5 opacity-70">~15s &middot; fast prep</p>
                  </button>
                  <button
                    onClick={() => setMode("deep")}
                    data-testid="mode-deep"
                    className={`flex-1 py-2.5 px-3 rounded-lg border text-sm font-medium transition-all ${
                      mode === "deep"
                        ? "border-amber-500/50 bg-amber-500/10 text-amber-500"
                        : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700 hover:text-zinc-400"
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <Layers className="w-3.5 h-3.5" />
                      <span>Deep</span>
                    </div>
                    <p className="text-[10px] mt-0.5 opacity-70">~30s &middot; full breakdown</p>
                  </button>
                </div>

                {/* Next or Analyze */}
                {hasInput ? (
                  <Button
                    data-testid="step-next-2"
                    onClick={() => goToStep(3)}
                    className="w-full mt-5 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press transition-colors gap-2"
                  >
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                ) : (
                  <p className="text-xs text-zinc-600 text-center mt-5">
                    {inputType === "text" ? "Paste at least a few lines to continue" : "Upload or snap your sides to continue"}
                  </p>
                )}
              </motion.div>
            )}

            {/* ===== STEP 3: Context + Launch ===== */}
            {step === 3 && (
              <motion.div key="step3" {...stepAnim}>
                {/* Back */}
                <button
                  data-testid="step-back-3"
                  onClick={() => goToStep(2)}
                  className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 mb-4 transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" /> Back
                </button>

                {/* Summary */}
                <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg p-4 mb-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {inputType === "text" ? <Type className="w-4 h-4 text-zinc-500" /> : inputType === "snap" ? <Camera className="w-4 h-4 text-zinc-500" /> : <Upload className="w-4 h-4 text-zinc-500" />}
                      <span className="text-sm text-zinc-400">
                        {inputType === "text"
                          ? `${scriptText.trim().split("\n").length} lines`
                          : imageFile?.name || "Photo"}
                      </span>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                      mode === "deep" ? "text-amber-500 border-amber-500/30 bg-amber-500/10" : "text-zinc-400 border-zinc-700 bg-zinc-800/30"
                    }`}>
                      {mode === "deep" ? "Deep" : "Quick"}
                    </span>
                  </div>
                </div>

                {/* Context (optional) */}
                <div>
                  <button
                    onClick={() => setShowContext(!showContext)}
                    className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors w-full"
                    data-testid="toggle-context-button"
                  >
                    <span>{showContext ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</span>
                    <span>Add context</span>
                    <span className="text-xs text-zinc-600">(helps the AI go deeper)</span>
                    {hasContext && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 ml-1" />}
                  </button>

                  <AnimatePresence>
                    {showContext && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="mt-3 space-y-3"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Character</label>
                            <input
                              data-testid="context-character"
                              value={context.character}
                              onChange={(e) => setContext(c => ({ ...c, character: e.target.value }))}
                              placeholder="e.g. Sarah, the younger sister"
                              className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Project</label>
                            <input
                              data-testid="context-synopsis"
                              value={context.synopsis}
                              onChange={(e) => setContext(c => ({ ...c, synopsis: e.target.value }))}
                              placeholder="e.g. Indie drama, estranged siblings"
                              className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none"
                            />
                          </div>
                        </div>
                        <input
                          data-testid="context-casting-notes"
                          value={context.castingNotes}
                          onChange={(e) => setContext(c => ({ ...c, castingNotes: e.target.value }))}
                          placeholder="Casting notes — e.g. 'grounded, not melodramatic'"
                          className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none"
                        />
                        <textarea
                          data-testid="context-character-desc"
                          value={context.characterDesc}
                          onChange={(e) => setContext(c => ({ ...c, characterDesc: e.target.value }))}
                          placeholder="Character description — e.g. 'Late 20s, guarded but sharp.'"
                          rows={2}
                          className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none resize-none"
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Analyze button */}
                <Button
                  data-testid="analyze-button"
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="w-full mt-5 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press disabled:opacity-30 disabled:cursor-not-allowed transition-colors gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  {mode === "deep" ? "Deep Analysis" : "Analyze My Sides"}
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Recent Breakdowns */}
        {step === 1 && recentBreakdowns && recentBreakdowns.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-6"
          >
            <div className="flex items-center gap-2 mb-3 px-1">
              <Clock className="w-3.5 h-3.5 text-zinc-600" />
              <span className="text-xs text-zinc-600 uppercase tracking-wider font-medium">Recent</span>
            </div>
            <div className="space-y-2">
              {recentBreakdowns.slice(0, 5).map((b) => (
                <button
                  key={b.id}
                  data-testid={`recent-breakdown-${b.id}`}
                  onClick={() => onLoadBreakdown(b.id)}
                  className="w-full text-left bg-zinc-950/40 border border-zinc-800/60 rounded-lg px-4 py-3 hover:border-zinc-700 hover:bg-zinc-900/40 transition-all group"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-zinc-300 font-medium truncate group-hover:text-amber-500 transition-colors">
                        {b.character_name || "Untitled Scene"}
                      </p>
                      <p className="text-xs text-zinc-600 truncate mt-0.5">
                        {b.scene_summary ? b.scene_summary.slice(0, 80) + (b.scene_summary.length > 80 ? "..." : "") : "No summary"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {b.mode === "deep" && <span className="text-[9px] text-amber-500/60 border border-amber-500/20 rounded px-1">DEEP</span>}
                      <span className="text-[10px] text-zinc-700">
                        {b.created_at ? new Date(b.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : ""}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-xs text-zinc-600 mt-6"
        >
          Powered by AI. Built for actors who book.
        </motion.p>
      </div>
    </div>
  );
}
