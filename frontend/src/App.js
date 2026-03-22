import { useState, useCallback, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { BrowserRouter, Routes, Route, useParams } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import UploadPage from "@/components/UploadPage";
import BreakdownView from "@/components/BreakdownView";
import MemorizationMode from "@/components/MemorizationMode";
import SceneReader from "@/components/SceneReader";
import ScriptOverview from "@/components/ScriptOverview";
import LoadingScreen from "@/components/LoadingScreen";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function MainApp() {
  const [view, setView] = useState("upload"); // "upload" | "breakdown" | "script"
  const [breakdown, setBreakdown] = useState(null);
  const [scriptData, setScriptData] = useState(null); // {script_id, character_name, mode, breakdowns}
  const [loading, setLoading] = useState(false);
  const [loadingMode, setLoadingMode] = useState("quick");
  const [memorizationOpen, setMemorizationOpen] = useState(false);
  const [sceneReaderOpen, setSceneReaderOpen] = useState(false);
  const [ttsAvailable, setTtsAvailable] = useState(false);
  const [recentBreakdowns, setRecentBreakdowns] = useState([]);
  // Track active breakdown for memorization/scene reader in script mode
  const [activeScriptBreakdown, setActiveScriptBreakdown] = useState(null);
  const [voices, setVoices] = useState([]);

  useEffect(() => {
    axios.get(`${API}/tts/status`).then(r => setTtsAvailable(r.data.available)).catch(() => {});
    axios.get(`${API}/tts/voices`).then(r => {
      if (r.data.available && r.data.voices?.length) {
        setVoices(r.data.voices);
        setTtsAvailable(true);
      }
    }).catch(() => {});
    axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
  }, []);

  const handleAnalyze = useCallback(async (data) => {
    setLoading(true);
    setLoadingMode(data.mode || "quick");
    try {
      let response;
      const isDeep = data.mode === "deep";
      const timeout = isDeep ? 180000 : 120000;
      if (data.type === "text") {
        response = await axios.post(`${API}/analyze/text`, { text: data.text, mode: data.mode || "quick" }, { timeout });
      } else {
        const formData = new FormData();
        formData.append("file", data.file);
        if (data.context) {
          formData.append("context", data.context);
        }
        formData.append("mode", data.mode || "quick");
        response = await axios.post(`${API}/analyze/image`, formData, {
          timeout,
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      const result = response.data;

      // Check if this is a fallback/partial response
      if (result._debug?.fallback) {
        const reason = result._debug?.reason || "Unknown error";
        const stageInfo = (result._debug?.stages || [])
          .filter(s => !s.ok)
          .map(s => `${s.stage}: ${s.error}`)
          .join(" | ");
        toast.error(`Analysis incomplete: ${stageInfo || reason}`, { duration: 10000 });
      } else {
        toast.success("Breakdown ready. Time to work.");
      }

      // Show debug stages in console for troubleshooting
      if (result._debug) {
        console.log("[Actor's Companion] Pipeline debug:", JSON.stringify(result._debug, null, 2));
      }

      setBreakdown(result);
      setView("breakdown");
      // Refresh recent list
      axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
    } catch (error) {
      let msg;
      if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
        msg = "Request timed out. Try a smaller file or paste the text directly.";
      } else if (!error.response) {
        msg = `Network error — check your connection. (${error.message || "no response"})`;
      } else if (error.response.status === 413) {
        msg = "File too large for upload. Try a smaller image or paste the text.";
      } else {
        msg = error.response?.data?.detail || `Server error (${error.response.status})`;
      }
      toast.error(msg, { duration: 8000 });
      console.error("[Actor's Companion] Analysis error:", {
        status: error.response?.status,
        detail: error.response?.data?.detail,
        message: error.message,
      });
    }
    setLoading(false);
  }, []);

  const handleRegenerateTakes = useCallback(async () => {
    if (!breakdown?.id) return;
    try {
      toast.loading("Generating new takes...", { id: "regen" });
      const response = await axios.post(`${API}/regenerate-takes/${breakdown.id}`);
      setBreakdown(response.data);
      toast.success("Fresh takes ready.", { id: "regen" });
    } catch (error) {
      toast.error("Failed to regenerate. Try again.", { id: "regen" });
    }
  }, [breakdown]);

  const handleExportPdf = useCallback(() => {
    if (!breakdown?.id) return;
    window.open(`${API}/export-pdf/${breakdown.id}`, "_blank");
  }, [breakdown]);

  const handleShare = useCallback(() => {
    if (!breakdown?.id) return;
    const shareUrl = `${window.location.origin}/share/${breakdown.id}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      toast.success("Share link copied to clipboard");
    }).catch(() => {
      toast.info(shareUrl);
    });
  }, [breakdown]);

  const handleReanalyzeDeep = useCallback(async () => {
    if (!breakdown?.original_text) {
      toast.error("Original script text not available for re-analysis.");
      return;
    }
    handleAnalyze({ type: "text", text: breakdown.original_text, mode: "deep" });
  }, [breakdown, handleAnalyze]);

  const handleNewAnalysis = useCallback(() => {
    setView("upload");
    setBreakdown(null);
    setScriptData(null);
    setActiveScriptBreakdown(null);
  }, []);

  const [sceneProgress, setSceneProgress] = useState(null); // {current, total, heading}

  const handleFullScriptAnalyze = useCallback(async (data) => {
    // data = { scenes: [...], character_name, mode }
    const scenes = data.scenes;
    const mode = data.mode || "quick";
    const characterName = data.character_name;

    setLoading(true);
    setLoadingMode(mode);
    setSceneProgress({ current: 0, total: scenes.length, heading: "" });

    try {
      // Step 1: Create script record
      const createResp = await axios.post(`${API}/scripts/create`, {
        character_name: characterName,
        mode,
        scene_count: scenes.length,
      }, { timeout: 15000 });
      const { script_id } = createResp.data;

      // Step 2: Analyze each scene individually (avoids proxy timeout)
      const breakdowns = [];
      for (let i = 0; i < scenes.length; i++) {
        const scene = scenes[i];
        setSceneProgress({
          current: i + 1,
          total: scenes.length,
          heading: scene.heading || `Scene ${scene.scene_number}`,
        });

        try {
          const resp = await axios.post(`${API}/analyze/scene`, {
            script_id,
            scene_number: scene.scene_number,
            scene_heading: scene.heading || `Scene ${scene.scene_number}`,
            text: scene.text,
            character_name: characterName,
            mode,
          }, { timeout: 180000 }); // 3min per scene max
          breakdowns.push(resp.data);
        } catch (sceneErr) {
          const errMsg = sceneErr.response?.data?.detail || sceneErr.message;
          console.error(`Scene ${scene.scene_number} failed:`, errMsg);
          // Add placeholder for failed scene
          breakdowns.push({
            id: `failed-${i}`,
            script_id,
            scene_number: scene.scene_number,
            scene_heading: scene.heading,
            original_text: scene.text,
            mode,
            scene_summary: `Analysis failed: ${errMsg}`,
            character_name: characterName,
            character_objective: "", stakes: "",
            beats: [], acting_takes: { grounded: "", bold: "", wildcard: "" },
            memorization: { chunked_lines: [], cue_recall: [] },
            self_tape_tips: { framing: "", eyeline: "", tone_energy: "" },
          });
          toast.error(`Scene ${scene.scene_number} failed — skipping.`, { duration: 4000 });
        }
      }

      const result = { script_id, character_name: characterName, mode, breakdowns };
      setScriptData(result);
      setView("script");
      const successCount = breakdowns.filter(b => !b.id?.startsWith("failed-")).length;
      toast.success(`${successCount} scene${successCount !== 1 ? 's' : ''} analyzed. Time to prep.`);
      axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || "Failed to start analysis";
      toast.error(msg, { duration: 8000 });
    }
    setLoading(false);
    setSceneProgress(null);
  }, []);

  const handleLoadBreakdown = useCallback(async (id) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/breakdowns/${id}`);
      setBreakdown(response.data);
      setView("breakdown");
    } catch {
      toast.error("Could not load this breakdown.");
    }
    setLoading(false);
  }, []);

  return (
    <>
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <LoadingScreen mode={loadingMode} sceneProgress={sceneProgress} />
          </motion.div>
        )}
        {!loading && view === "upload" && (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <UploadPage onAnalyze={handleAnalyze} onFullScriptAnalyze={handleFullScriptAnalyze} recentBreakdowns={recentBreakdowns} onLoadBreakdown={handleLoadBreakdown} />
          </motion.div>
        )}
        {!loading && view === "breakdown" && breakdown && (
          <motion.div key="breakdown" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <BreakdownView
              breakdown={breakdown}
              onRegenerate={handleRegenerateTakes}
              onReanalyzeDeep={handleReanalyzeDeep}
              onExportPdf={handleExportPdf}
              onNewAnalysis={handleNewAnalysis}
              onOpenMemorization={() => setMemorizationOpen(true)}
              onOpenSceneReader={() => setSceneReaderOpen(true)}
              onShare={handleShare}
              ttsAvailable={ttsAvailable}
            />
          </motion.div>
        )}
        {!loading && view === "script" && scriptData && (
          <motion.div key="script" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <ScriptOverview
              scriptData={scriptData}
              ttsAvailable={ttsAvailable}
              onNewAnalysis={handleNewAnalysis}
              onOpenMemorization={(b) => { setActiveScriptBreakdown(b); setMemorizationOpen(true); }}
              onOpenSceneReader={(b) => { setActiveScriptBreakdown(b); setSceneReaderOpen(true); }}
              onExportPdf={(id) => window.open(`${API}/export-pdf/${id}`, "_blank")}
              onShare={(id) => {
                const url = `${window.location.origin}/share/${id}`;
                navigator.clipboard.writeText(url).then(() => toast.success("Share link copied")).catch(() => toast.info(url));
              }}
              onRegenerate={async (id) => {
                try {
                  toast.loading("Generating new takes...", { id: "regen" });
                  const resp = await axios.post(`${API}/regenerate-takes/${id}`);
                  setScriptData(prev => ({
                    ...prev,
                    breakdowns: prev.breakdowns.map(b => b.id === id ? resp.data : b),
                  }));
                  toast.success("Fresh takes ready.", { id: "regen" });
                } catch { toast.error("Failed to regenerate.", { id: "regen" }); }
              }}
              onReanalyzeDeep={async (b) => {
                if (!b?.original_text) return;
                handleAnalyze({ type: "text", text: `[CHARACTER TO ANALYZE: ${scriptData.character_name}]\n[SCENE: ${b.scene_heading || ''}]\n\n${b.original_text}`, mode: "deep" });
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {memorizationOpen && (breakdown || activeScriptBreakdown) && (
          <MemorizationMode
            memorization={(activeScriptBreakdown || breakdown).memorization}
            characterName={(activeScriptBreakdown || breakdown).character_name}
            onClose={() => { setMemorizationOpen(false); setActiveScriptBreakdown(null); }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sceneReaderOpen && (breakdown || activeScriptBreakdown) && (
          <SceneReader
            memorization={(activeScriptBreakdown || breakdown).memorization}
            characterName={(activeScriptBreakdown || breakdown).character_name}
            ttsAvailable={ttsAvailable}
            voices={voices}
            onClose={() => { setSceneReaderOpen(false); setActiveScriptBreakdown(null); }}
          />
        )}
      </AnimatePresence>
    </>
  );
}

function SharePage() {
  const { id } = useParams();
  const [breakdown, setBreakdown] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API}/breakdowns/${id}`)
      .then(r => { setBreakdown(r.data); setLoading(false); })
      .catch(() => { setError("Breakdown not found"); setLoading(false); });
  }, [id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-zinc-500">Loading breakdown...</div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <p className="text-zinc-500">{error}</p>
      <a href="/" className="text-amber-500 hover:text-amber-400 text-sm underline" data-testid="share-go-home">
        Create your own breakdown
      </a>
    </div>
  );

  return (
    <div data-testid="share-view">
      <BreakdownView
        breakdown={breakdown}
        isShareView={true}
        onNewAnalysis={() => window.location.href = "/"}
      />
    </div>
  );
}

function App() {
  return (
    <TooltipProvider>
      <div className="app-root">
        <div className="noise-overlay" />
        <Toaster
          theme="dark"
          position="top-center"
          toastOptions={{
            style: {
              background: "#18181b",
              border: "1px solid #27272a",
              color: "#fafafa",
              fontFamily: "Manrope, sans-serif",
            },
          }}
        />
        <BrowserRouter>
          <Routes>
            <Route path="/share/:id" element={<SharePage />} />
            <Route path="*" element={<MainApp />} />
          </Routes>
        </BrowserRouter>
      </div>
    </TooltipProvider>
  );
}

export default App;
