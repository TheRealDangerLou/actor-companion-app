import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Upload, FileText, Image, Sparkles, ArrowRight } from "lucide-react";

const HERO_BG = "https://images.unsplash.com/photo-1761229660731-891484da5c35?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2OTV8MHwxfHNlYXJjaHw0fHx0aGVhdGVyJTIwc3RhZ2UlMjBzcG90bGlnaHQlMjBkYXJrfGVufDB8fHx8MTc3Mzg4ODc2Mnww&ixlib=rb-4.1.0&q=85&w=1920";

export default function UploadPage({ onAnalyze }) {
  const [tab, setTab] = useState("text");
  const [scriptText, setScriptText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleImageSelect = useCallback((file) => {
    if (!file) return;
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
      return;
    }
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleImageSelect(file);
  }, [handleImageSelect]);

  const handleSubmit = () => {
    if (tab === "text" && scriptText.trim().length >= 10) {
      onAnalyze({ type: "text", text: scriptText });
    } else if (tab === "image" && imageFile) {
      onAnalyze({ type: "image", file: imageFile });
    }
  };

  const canSubmit =
    (tab === "text" && scriptText.trim().length >= 10) ||
    (tab === "image" && imageFile);

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 py-12">
      {/* Hero background */}
      <div className="absolute inset-0 z-0">
        <img
          src={HERO_BG}
          alt=""
          className="w-full h-full object-cover opacity-[0.12]"
        />
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
          <h1
            data-testid="app-title"
            className="font-display text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white mb-4"
          >
            Actor's <span className="text-amber-500">Companion</span>
          </h1>
          <p className="text-base md:text-lg text-zinc-400 max-w-md mx-auto leading-relaxed">
            Upload your sides. Get a breakdown you can perform in minutes.
          </p>
        </motion.div>

        {/* Upload Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="bg-zinc-950/60 border border-zinc-800 rounded-xl p-6 md:p-8 backdrop-blur-md"
        >
          <Tabs value={tab} onValueChange={setTab} className="w-full">
            <TabsList className="w-full bg-zinc-900/80 border border-zinc-800 mb-6">
              <TabsTrigger
                value="text"
                data-testid="upload-text-tab"
                className="flex-1 gap-2 data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-500"
              >
                <FileText className="w-4 h-4" />
                Paste Script
              </TabsTrigger>
              <TabsTrigger
                value="image"
                data-testid="upload-image-tab"
                className="flex-1 gap-2 data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-500"
              >
                <Image className="w-4 h-4" />
                Upload Image
              </TabsTrigger>
            </TabsList>

            <TabsContent value="text">
              <textarea
                data-testid="script-textarea"
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder={"Paste your audition sides here...\n\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?\n\nJOHN\nBecause I need you to hear this."}
                className="w-full h-56 md:h-64 bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 font-script text-base text-zinc-200 placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/30 focus:outline-none resize-none transition-colors"
              />
              <p className="text-xs text-zinc-600 mt-2">
                Paste dialogue, stage directions, or full scene pages
              </p>
            </TabsContent>

            <TabsContent value="image">
              <div
                data-testid="image-upload-zone"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`w-full h-56 md:h-64 border-2 border-dashed rounded-lg flex flex-col items-center justify-center cursor-pointer transition-all ${
                  dragOver
                    ? "drag-active border-amber-500 bg-amber-500/5"
                    : imagePreview
                    ? "border-zinc-700 bg-zinc-900/30"
                    : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700"
                }`}
              >
                {imagePreview ? (
                  <div className="relative w-full h-full p-4">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="w-full h-full object-contain rounded"
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setImageFile(null);
                        setImagePreview(null);
                      }}
                      className="absolute top-2 right-2 bg-zinc-900/80 text-zinc-400 hover:text-white rounded-full w-7 h-7 flex items-center justify-center text-sm border border-zinc-700"
                      data-testid="clear-image-button"
                    >
                      x
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-zinc-600 mb-3" />
                    <p className="text-sm text-zinc-500">
                      Drop your sides here, or{" "}
                      <span className="text-amber-500">browse</span>
                    </p>
                    <p className="text-xs text-zinc-600 mt-1">
                      JPG, PNG, or WebP up to 10MB
                    </p>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => handleImageSelect(e.target.files[0])}
                  className="hidden"
                  data-testid="image-upload-input"
                />
              </div>
            </TabsContent>
          </Tabs>

          {/* Analyze Button */}
          <Button
            data-testid="analyze-button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full mt-6 h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-base rounded-lg btn-press disabled:opacity-30 disabled:cursor-not-allowed transition-colors gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Analyze My Sides
            <ArrowRight className="w-4 h-4" />
          </Button>
        </motion.div>

        {/* Footer hint */}
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
