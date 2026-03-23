import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Upload, FileText, Image, Sparkles, ArrowRight, ArrowLeft, Camera,
  ChevronDown, ChevronUp, Layers, Clock, Type, ImageIcon, CameraIcon,
  ScrollText, User, Search, Check, CheckSquare, Square, Loader2,
  AlertTriangle,
} from "lucide-react";
import axios from "axios";

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

export default function UploadPage({ onAnalyze, onFullScriptAnalyze, recentBreakdowns, recentScripts, onLoadBreakdown, onLoadScript }) {
  const [step, setStep] = useState(1);
  const [inputType, setInputType] = useState(null); // "text" | "file" | "snap" | "fullscript"
  const [scriptText, setScriptText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [mode, setMode] = useState("quick");
  const [showContext, setShowContext] = useState(false);
  const [context, setContext] = useState({ character: "", synopsis: "", castingNotes: "", characterDesc: "" });
  const [clarifications, setClarifications] = useState(new Set());

  const CLARIFICATION_OPTIONS = [
    { id: "cold_read", label: "Cold read", hint: "First time seeing this material" },
    { id: "comedic", label: "Comedic", hint: "Scene is comedic in tone" },
    { id: "dramatic", label: "Dramatic", hint: "Scene is dramatic/serious" },
    { id: "antagonist", label: "I'm the antagonist", hint: "Playing the villain/obstacle" },
    { id: "callback", label: "Callback", hint: "Second or later audition" },
    { id: "self_tape", label: "Self-tape", hint: "Recording at home, not in the room" },
    { id: "chemistry_read", label: "Chemistry read", hint: "Reading with another actor" },
    { id: "under_5", label: "Under-5", hint: "Small role, few lines" },
  ];

  const toggleClarification = useCallback((id) => {
    setClarifications(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  // Full Script mode state
  const [fullScriptText, setFullScriptText] = useState("");
  const [fullScriptFile, setFullScriptFile] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [characterName, setCharacterName] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [parsedScenes, setParsedScenes] = useState(null);
  const [selectedScenes, setSelectedScenes] = useState(new Set());
  const [prepMode, setPrepMode] = useState(null); // "audition" | "booked" | "silent" | "study"
  const [projectType, setProjectType] = useState(null); // "commercial" | "tvfilm" | "theatre" | "voiceover"
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fullScriptFileRef = useRef(null);

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

  // --- Full Script Helpers ---
  const handleFullScriptFile = useCallback(async (e) => {
    const file = e?.target?.files?.[0];
    if (!file) return;
    e.target.value = "";

    const name = file.name.toLowerCase();
    const isText = name.endsWith('.txt');
    const isPdf = name.endsWith('.pdf');
    const isImage = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp'].some(ext => name.endsWith(ext));

    if (!isText && !isPdf && !isImage) {
      toast.error("Upload a PDF, image, or text file.");
      return;
    }

    setFullScriptFile(file);

    // .txt files: read directly
    if (isText) {
      const text = await file.text();
      setFullScriptText(text);
      toast.success(`Loaded ${file.name} — ${text.split('\\n').length} lines`);
      return;
    }

    // PDF/image: extract text via backend
    setIsExtracting(true);
    toast.loading("Extracting text from file...", { id: "extract" });
    try {
      const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
      const formData = new FormData();
      formData.append("file", file);
      const response = await axios.post(`${API}/extract-text`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      const { text, chars } = response.data;
      setFullScriptText(text);
      toast.success(`Extracted ${chars.toLocaleString()} characters from ${file.name}`, { id: "extract" });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Extraction failed";
      toast.error(msg, { id: "extract", duration: 6000 });
      setFullScriptFile(null);
    }
    setIsExtracting(false);
  }, []);

  const handleParseScenes = useCallback(async () => {
    let textToparse = fullScriptText.trim();

    if (textToparse.length < 50) {
      toast.error("Not enough text for scene detection. Paste more script or upload a file.");
      return;
    }
    if (!characterName.trim()) {
      toast.error("Enter your character name to find your scenes.");
      return;
    }

    setIsParsing(true);
    try {
      const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
      const response = await axios.post(`${API}/parse-scenes`, {
        text: textToparse,
        character_name: characterName.trim(),
      }, { timeout: 60000 });

      const data = response.data;
      setParsedScenes(data);

      // Auto-select all scenes that contain the character
      const charSceneNums = new Set(
        data.scenes.filter(s => s.has_character).map(s => s.scene_number)
      );
      setSelectedScenes(charSceneNums);

      if (data.character_scenes_count === 0) {
        toast.info(`No scenes found for "${characterName}". Try a different name or check spelling.`);
      } else {
        toast.success(`Found ${data.character_scenes_count} scene${data.character_scenes_count > 1 ? 's' : ''} with ${characterName}.`);
      }

      setStep(4); // Move to scene selection
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to parse scenes";
      toast.error(msg);
    }
    setIsParsing(false);
  }, [fullScriptText, fullScriptFile, characterName]);

  const toggleScene = useCallback((sceneNum) => {
    setSelectedScenes(prev => {
      const next = new Set(prev);
      if (next.has(sceneNum)) next.delete(sceneNum);
      else next.add(sceneNum);
      return next;
    });
  }, []);

  const toggleAllCharScenes = useCallback(() => {
    if (!parsedScenes) return;
    const charSceneNums = parsedScenes.scenes.filter(s => s.has_character).map(s => s.scene_number);
    const allSelected = charSceneNums.every(n => selectedScenes.has(n));
    if (allSelected) {
      setSelectedScenes(new Set());
    } else {
      setSelectedScenes(new Set(charSceneNums));
    }
  }, [parsedScenes, selectedScenes]);

  const handleFullScriptSubmit = useCallback(() => {
    if (!parsedScenes || selectedScenes.size === 0 || isSubmitting) return;
    setIsSubmitting(true);
    const scenesToAnalyze = parsedScenes.scenes.filter(s => selectedScenes.has(s.scene_number));
    if (onFullScriptAnalyze) {
      onFullScriptAnalyze({
        scenes: scenesToAnalyze,
        character_name: characterName.trim(),
        mode,
        prepMode,
        projectType,
      });
    }
    // Reset after a short delay to allow navigation away
    setTimeout(() => setIsSubmitting(false), 2000);
  }, [parsedScenes, selectedScenes, characterName, mode, prepMode, projectType, onFullScriptAnalyze, isSubmitting]);

  const buildContextString = () => {
    const parts = [];
    if (context.character.trim()) parts.push(`Character I'm playing: ${context.character.trim()}`);
    if (context.synopsis.trim()) parts.push(`Project synopsis: ${context.synopsis.trim()}`);
    if (context.castingNotes.trim()) parts.push(`Notes from casting: ${context.castingNotes.trim()}`);
    if (context.characterDesc.trim()) parts.push(`Character description: ${context.characterDesc.trim()}`);
    if (clarifications.size > 0) {
      const labels = CLARIFICATION_OPTIONS
        .filter(o => clarifications.has(o.id))
        .map(o => `${o.label}: ${o.hint}`);
      parts.push(`Actor notes: ${labels.join('; ')}`);
    }
    return parts.length > 0 ? parts.join("\n\n") : "";
  };

  const handleSubmit = () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    const contextStr = buildContextString();
    if (inputType === "text" && scriptText.trim().length >= 10) {
      const fullText = contextStr
        ? `[CONTEXT FOR ANALYSIS]\n${contextStr}\n\n[AUDITION SIDES]\n${scriptText}`
        : scriptText;
      onAnalyze({ type: "text", text: fullText, mode });
    } else if ((inputType === "file" || inputType === "snap") && imageFile) {
      onAnalyze({ type: "image", file: imageFile, context: contextStr, mode });
    }
    // Reset after a short delay to allow navigation away
    setTimeout(() => setIsSubmitting(false), 2000);
  };

  const canSubmit =
    (inputType === "text" && scriptText.trim().length >= 10) ||
    ((inputType === "file" || inputType === "snap") && imageFile);

  const hasContext = Object.values(context).some(v => v.trim()) || clarifications.size > 0;

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
            {(inputType === "fullscript" ? [1, 2, 3, 4] : [1, 2, 3]).map((s) => (
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
                    <span className="text-sm text-zinc-300 font-medium">Paste sides</span>
                  </button>
                  <button
                    data-testid="input-type-file"
                    onClick={() => selectInputType("file")}
                    className={`flex flex-col items-center gap-2 p-5 rounded-lg border transition-all hover:border-zinc-600 ${
                      inputType === "file" ? "border-amber-500/50 bg-amber-500/5" : "border-zinc-800 bg-zinc-900/30"
                    }`}
                  >
                    <Upload className="w-6 h-6 text-amber-500/70" />
                    <span className="text-sm text-zinc-300 font-medium">Upload sides</span>
                  </button>
                  <button
                    data-testid="input-type-fullscript"
                    onClick={() => selectInputType("fullscript")}
                    className={`flex flex-col items-center gap-2 p-5 rounded-lg border transition-all hover:border-zinc-600 col-span-2 ${
                      inputType === "fullscript" ? "border-amber-500/50 bg-amber-500/5" : "border-zinc-800 bg-zinc-900/30"
                    }`}
                  >
                    <ScrollText className="w-6 h-6 text-amber-500/70" />
                    <span className="text-sm text-zinc-300 font-medium">Full Script</span>
                    <span className="text-[10px] text-zinc-500">Find & break down all your scenes</span>
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

                {/* Full Script input */}
                {inputType === "fullscript" && (
                  <div className="space-y-3">
                    {/* File upload area */}
                    <div
                      data-testid="fullscript-upload-zone"
                      onClick={() => !isExtracting && fullScriptFileRef.current?.click()}
                      className={`w-full border-2 border-dashed rounded-lg flex items-center justify-center cursor-pointer transition-all ${
                        isExtracting ? "border-amber-500/30 bg-amber-500/5 cursor-wait" :
                        fullScriptFile ? "border-emerald-500/30 bg-emerald-500/5 p-3" : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 p-5"
                      }`}
                    >
                      {isExtracting ? (
                        <div className="flex items-center gap-2 py-2">
                          <Loader2 className="w-4 h-4 animate-spin text-amber-500" />
                          <span className="text-sm text-amber-500">Extracting text from {fullScriptFile?.name}...</span>
                        </div>
                      ) : fullScriptFile && fullScriptText ? (
                        <div className="flex items-center justify-between w-full gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="w-4 h-4 text-emerald-500 shrink-0" />
                            <span className="text-sm text-emerald-400 truncate">{fullScriptFile.name}</span>
                            <span className="text-xs text-zinc-500 shrink-0">{fullScriptText.split('\n').length} lines</span>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); setFullScriptFile(null); setFullScriptText(""); }}
                            className="text-zinc-500 hover:text-white text-xs shrink-0"
                            data-testid="fullscript-clear-file"
                          >
                            Clear
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center gap-1.5">
                          <Upload className="w-6 h-6 text-amber-500/60" />
                          <p className="text-sm text-zinc-400">Upload PDF or image</p>
                          <p className="text-[10px] text-zinc-600">PDF, JPG, PNG, HEIC</p>
                        </div>
                      )}
                      <input
                        ref={fullScriptFileRef}
                        type="file"
                        accept=".pdf,.txt,.jpg,.jpeg,.png,.heic,.heif,.webp"
                        onChange={handleFullScriptFile}
                        className="hidden"
                        data-testid="fullscript-file-input"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="h-px flex-1 bg-zinc-800" />
                      <span className="text-[10px] text-zinc-600 uppercase tracking-wider">or paste</span>
                      <div className="h-px flex-1 bg-zinc-800" />
                    </div>

                    {/* Textarea */}
                    <textarea
                      data-testid="fullscript-textarea"
                      value={fullScriptText}
                      onChange={(e) => setFullScriptText(e.target.value)}
                      placeholder={"Paste the full script here...\n\nINT. KITCHEN - DAY\n\nSARAH sits at the table.\n\nJOHN\nWe need to talk.\n\n..."}
                      className="w-full h-44 md:h-52 bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 font-script text-base text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/30 focus:outline-none resize-none transition-colors"
                    />
                  </div>
                )}

                {/* Mode toggle — only for non-fullscript modes */}
                {inputType !== "fullscript" && (
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
                )}

                {/* Next or Analyze */}
                {inputType === "fullscript" ? (
                  fullScriptText.trim().length >= 50 && !isExtracting ? (
                    <Button
                      data-testid="step-next-2-fullscript"
                      onClick={() => goToStep(3)}
                      className="w-full mt-5 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press transition-colors gap-2"
                    >
                      Continue
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  ) : !isExtracting ? (
                    <p className="text-xs text-zinc-600 text-center mt-5">Upload a file or paste the script to continue</p>
                  ) : null
                ) : hasInput ? (
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

            {/* ===== STEP 3: Context + Launch (Sides) OR Character Name (Full Script) ===== */}
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

                {inputType === "fullscript" ? (
                  /* --- Full Script: Character Name + Find Scenes --- */
                  <div>
                    <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-lg p-4 mb-5">
                      <div className="flex items-center gap-2">
                        <ScrollText className="w-4 h-4 text-zinc-500" />
                        <span className="text-sm text-zinc-400">
                          {fullScriptText.trim().split("\n").length} lines pasted
                        </span>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-zinc-400 mb-2 block font-medium">
                          Who are you playing?
                        </label>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
                          <input
                            data-testid="character-name-input"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="e.g. Sarah, Felix, Dr. Chen"
                            className="w-full bg-zinc-900/50 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-base text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/30 focus:outline-none transition-colors"
                            onKeyDown={(e) => { if (e.key === 'Enter' && characterName.trim()) handleParseScenes(); }}
                          />
                        </div>
                        <p className="text-xs text-zinc-600 mt-1.5">
                          We'll find every scene this character appears in
                        </p>
                      </div>

                      {/* Prep Mode */}
                      <div>
                        <label className="text-sm text-zinc-400 mb-2 block font-medium">
                          What's this for?
                        </label>
                        <div className="grid grid-cols-2 gap-2" data-testid="prep-mode-selector">
                          {[
                            { id: "audition", label: "Audition", desc: "Breakdown + takes + self-tape" },
                            { id: "booked", label: "Booked role", desc: "Memorize + rehearse + run lines" },
                            { id: "silent", label: "Silent / on-camera", desc: "Breakdown + performance notes" },
                            { id: "study", label: "Script study", desc: "Full analysis, all tools" },
                          ].map(opt => (
                            <button
                              key={opt.id}
                              data-testid={`prep-mode-${opt.id}`}
                              onClick={() => setPrepMode(prev => prev === opt.id ? null : opt.id)}
                              className={`text-left p-2.5 rounded-lg border transition-all ${
                                prepMode === opt.id
                                  ? "border-amber-500/40 bg-amber-500/5"
                                  : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700"
                              }`}
                            >
                              <p className={`text-xs font-medium ${prepMode === opt.id ? "text-amber-500" : "text-zinc-300"}`}>
                                {opt.label}
                              </p>
                              <p className="text-[10px] text-zinc-600 mt-0.5">{opt.desc}</p>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Project Type */}
                      <div>
                        <label className="text-xs text-zinc-500 mb-1.5 block">Project type</label>
                        <div className="flex flex-wrap gap-1.5" data-testid="project-type-selector">
                          {[
                            { id: "commercial", label: "Commercial" },
                            { id: "tvfilm", label: "TV / Film" },
                            { id: "theatre", label: "Theatre" },
                            { id: "voiceover", label: "Voiceover" },
                            { id: "vertical", label: "Vertical / Soap" },
                          ].map(opt => (
                            <button
                              key={opt.id}
                              data-testid={`project-type-${opt.id}`}
                              onClick={() => setProjectType(prev => prev === opt.id ? null : opt.id)}
                              className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                                projectType === opt.id
                                  ? "border-amber-500/40 bg-amber-500/10 text-amber-500"
                                  : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700 hover:text-zinc-400"
                              }`}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Mode toggle for full script */}
                      <div className="flex items-center gap-3" data-testid="fullscript-mode-toggle">
                        <button
                          onClick={() => setMode("quick")}
                          data-testid="fs-mode-quick"
                          className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                            mode === "quick"
                              ? "border-amber-500/50 bg-amber-500/10 text-amber-500"
                              : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700"
                          }`}
                        >
                          <div className="flex items-center justify-center gap-2">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Quick</span>
                          </div>
                          <p className="text-[10px] mt-0.5 opacity-70">~15s per scene</p>
                        </button>
                        <button
                          onClick={() => setMode("deep")}
                          data-testid="fs-mode-deep"
                          className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                            mode === "deep"
                              ? "border-amber-500/50 bg-amber-500/10 text-amber-500"
                              : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700"
                          }`}
                        >
                          <div className="flex items-center justify-center gap-2">
                            <Layers className="w-3.5 h-3.5" />
                            <span>Deep</span>
                          </div>
                          <p className="text-[10px] mt-0.5 opacity-70">~30s per scene</p>
                        </button>
                      </div>
                      {mode === "deep" && (
                        <div className="flex items-start gap-2 px-1" data-testid="deep-mode-fullscript-warning">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                          <p className="text-xs text-amber-500/80">
                            Deep mode takes longer per scene. For full scripts, Quick is recommended — you can always deep-dive individual scenes later.
                          </p>
                        </div>
                      )}

                      <Button
                        data-testid="find-scenes-button"
                        onClick={handleParseScenes}
                        disabled={!characterName.trim() || isParsing}
                        className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press disabled:opacity-30 disabled:cursor-not-allowed transition-colors gap-2"
                      >
                        {isParsing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Finding scenes...
                          </>
                        ) : (
                          <>
                            <Search className="w-4 h-4" />
                            Find My Scenes
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ) : (
                  /* --- Sides: Context + Launch --- */
                  <div>
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

                    {/* Clarification toggles */}
                    <div className="mt-4">
                      <p className="text-xs text-zinc-600 mb-2">Quick flags (optional)</p>
                      <div className="flex flex-wrap gap-1.5" data-testid="clarification-toggles">
                        {CLARIFICATION_OPTIONS.map(opt => {
                          const isActive = clarifications.has(opt.id);
                          return (
                            <button
                              key={opt.id}
                              data-testid={`clarification-${opt.id}`}
                              onClick={() => toggleClarification(opt.id)}
                              className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                                isActive
                                  ? "border-amber-500/40 bg-amber-500/10 text-amber-500"
                                  : "border-zinc-800 bg-zinc-900/30 text-zinc-500 hover:border-zinc-700 hover:text-zinc-400"
                              }`}
                            >
                              {opt.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Analyze button */}
                    <Button
                      data-testid="analyze-button"
                      onClick={handleSubmit}
                      disabled={!canSubmit || isSubmitting}
                      className="w-full mt-5 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press disabled:opacity-30 disabled:cursor-not-allowed transition-colors gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          {mode === "deep" ? "Deep Analysis" : "Analyze My Sides"}
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </motion.div>
            )}

            {/* ===== STEP 4: Scene Selection (Full Script only) ===== */}
            {step === 4 && inputType === "fullscript" && parsedScenes && (
              <motion.div key="step4" {...stepAnim}>
                <button
                  data-testid="step-back-4"
                  onClick={() => goToStep(3)}
                  className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 mb-4 transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" /> Back
                </button>

                {/* Summary header */}
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-200">
                      {parsedScenes.character_scenes_count} scene{parsedScenes.character_scenes_count !== 1 ? 's' : ''} found for {parsedScenes.character_name}
                    </h3>
                    <p className="text-xs text-zinc-500 mt-0.5">
                      {parsedScenes.total_scenes} total scenes in script
                    </p>
                  </div>
                  <button
                    data-testid="toggle-all-scenes"
                    onClick={toggleAllCharScenes}
                    className="text-xs text-amber-500 hover:text-amber-400 transition-colors"
                  >
                    {parsedScenes.scenes.filter(s => s.has_character).every(s => selectedScenes.has(s.scene_number))
                      ? "Deselect All" : "Select All"}
                  </button>
                </div>

                {/* Scene list */}
                <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1 -mr-1 custom-scrollbar">
                  {parsedScenes.scenes.map((scene) => {
                    const isSelected = selectedScenes.has(scene.scene_number);
                    const isMyScene = scene.has_character;

                    return (
                      <button
                        key={scene.scene_number}
                        data-testid={`scene-item-${scene.scene_number}`}
                        onClick={() => toggleScene(scene.scene_number)}
                        className={`w-full text-left rounded-lg border p-3 transition-all ${
                          isSelected
                            ? "border-amber-500/40 bg-amber-500/5"
                            : isMyScene
                            ? "border-zinc-700 bg-zinc-900/30 hover:border-zinc-600"
                            : "border-zinc-800/40 bg-zinc-950/20 opacity-50"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 shrink-0">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-amber-500" />
                            ) : (
                              <Square className="w-4 h-4 text-zinc-600" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-mono text-zinc-500">#{scene.scene_number}</span>
                              <span className="text-sm text-zinc-200 font-medium truncate">{scene.heading}</span>
                              {isMyScene && (
                                <span className="text-[9px] text-amber-500 border border-amber-500/20 rounded px-1 shrink-0">
                                  YOUR SCENE
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-zinc-500 line-clamp-2">{scene.preview}</p>
                            {scene.characters.length > 0 && (
                              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                                {scene.characters.slice(0, 6).map(c => (
                                  <span
                                    key={c}
                                    className={`text-[10px] px-1.5 py-0.5 rounded border ${
                                      c.toUpperCase().includes(characterName.toUpperCase())
                                        ? "text-amber-500 border-amber-500/20 bg-amber-500/5"
                                        : "text-zinc-500 border-zinc-800 bg-zinc-900/30"
                                    }`}
                                  >
                                    {c}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Analyze selected */}
                <Button
                  data-testid="analyze-batch-button"
                  onClick={handleFullScriptSubmit}
                  disabled={selectedScenes.size === 0 || isSubmitting}
                  className="w-full mt-4 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press disabled:opacity-30 disabled:cursor-not-allowed transition-colors gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Starting analysis...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      {selectedScenes.size === 0
                        ? "Select scenes to analyze"
                        : selectedScenes.size === 1
                        ? `Analyze 1 Scene (${mode === 'deep' ? 'Deep' : 'Quick'})`
                        : `Break Down ${selectedScenes.size} Scenes (${mode === 'deep' ? 'Deep' : 'Quick'})`}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Recent Scripts (full script projects) */}
        {step === 1 && recentScripts && recentScripts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-6"
          >
            <div className="flex items-center gap-2 mb-3 px-1">
              <Layers className="w-3.5 h-3.5 text-amber-500/60" />
              <span className="text-xs text-amber-500/60 uppercase tracking-wider font-medium">My Scripts</span>
            </div>
            <div className="space-y-2">
              {recentScripts.slice(0, 5).map((s) => (
                <button
                  key={s.id}
                  data-testid={`recent-script-${s.id}`}
                  onClick={() => onLoadScript(s.id)}
                  className="w-full text-left bg-zinc-950/40 border border-zinc-800/60 rounded-lg px-4 py-3 hover:border-amber-500/30 hover:bg-zinc-900/40 transition-all group"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-zinc-300 font-medium truncate group-hover:text-amber-500 transition-colors">
                        {s.character_name || "Untitled"}
                      </p>
                      <p className="text-xs text-zinc-600 mt-0.5">
                        {s.breakdown_count || 0} scene{(s.breakdown_count || 0) !== 1 ? "s" : ""}
                        {s.mode === "deep" ? " · Deep" : " · Quick"}
                        {s.project_type === "vertical" ? " · Vertical" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {s.prep_mode === "booked" && <span className="text-[9px] text-emerald-500/60 border border-emerald-500/20 rounded px-1">BOOKED</span>}
                      <span className="text-[10px] text-zinc-700">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : ""}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}

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
        <p className="text-center text-[10px] text-zinc-700/50 mt-1.5">
          Co-produced by DangerLou Media
        </p>
      </div>
    </div>
  );
}
