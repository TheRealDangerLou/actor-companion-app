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
import AdjustmentPanel from "@/components/AdjustmentPanel";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function MainApp() {
  const [view, setView] = useState("upload"); // "upload" | "breakdown" | "script"
  const [breakdown, setBreakdown] = useState(null);
  const [scriptData, setScriptData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMode, setLoadingMode] = useState("quick");
  const [memorizationOpen, setMemorizationOpen] = useState(false);
  const [sceneReaderOpen, setSceneReaderOpen] = useState(false);
  const [ttsAvailable, setTtsAvailable] = useState(false);
  const [recentBreakdowns, setRecentBreakdowns] = useState([]);
  const [recentScripts, setRecentScripts] = useState([]);
  const [activeScriptBreakdown, setActiveScriptBreakdown] = useState(null);
  const [voices, setVoices] = useState([]);
  const [showPostActionAdjust, setShowPostActionAdjust] = useState(false);
  const [postActionBreakdownId, setPostActionBreakdownId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/tts/status`).then(r => setTtsAvailable(r.data.available)).catch(() => {});
    axios.get(`${API}/tts/voices`).then(r => {
      if (r.data.available && r.data.voices?.length) {
        setVoices(r.data.voices);
        setTtsAvailable(true);
      }
    }).catch(() => {});
    axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
    axios.get(`${API}/scripts`).then(r => setRecentScripts(r.data || [])).catch(() => {});
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
      } else if (result.from_cache || result._debug?.cached) {
        toast.success("Breakdown ready.");
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
    // data = { scenes: [...], character_name, mode, prepMode, projectType }
    const scenes = data.scenes;
    const mode = data.mode || "quick";
    const characterName = data.character_name;
    const prepMode = data.prepMode || null;
    const projectType = data.projectType || null;

    setLoading(true);
    setLoadingMode(mode);
    setSceneProgress({ current: 0, total: scenes.length, heading: "" });

    try {
      // Step 1: Create script record
      const createResp = await axios.post(`${API}/scripts/create`, {
        character_name: characterName,
        mode,
        scene_count: scenes.length,
        prep_mode: prepMode,
        project_type: projectType,
      }, { timeout: 15000 });
      const { script_id } = createResp.data;

      // Step 2: Analyze scenes in parallel batches (3 at a time for speed)
      const BATCH_SIZE = 3;
      const breakdowns = new Array(scenes.length).fill(null);
      let stopBatch = false;

      for (let batchStart = 0; batchStart < scenes.length && !stopBatch; batchStart += BATCH_SIZE) {
        const batchEnd = Math.min(batchStart + BATCH_SIZE, scenes.length);
        const batch = scenes.slice(batchStart, batchEnd);

        setSceneProgress({
          current: batchStart + 1,
          total: scenes.length,
          heading: batch.map(s => s.heading || `Scene ${s.scene_number}`).join(", "),
        });

        const batchPromises = batch.map((scene, batchIdx) => {
          const globalIdx = batchStart + batchIdx;
          return axios.post(`${API}/analyze/scene`, {
            script_id,
            scene_number: scene.scene_number,
            scene_heading: scene.heading || `Scene ${scene.scene_number}`,
            text: scene.text,
            character_name: characterName,
            mode,
            prep_mode: prepMode,
            project_type: projectType,
          }, { timeout: 70000 }).then(resp => {
            breakdowns[globalIdx] = resp.data;
            // Update progress as each scene completes
            const doneCount = breakdowns.filter(b => b !== null).length;
            setSceneProgress(prev => ({ ...prev, current: doneCount }));
          }).catch(sceneErr => {
            const status = sceneErr.response?.status;
            const detail = sceneErr.response?.data?.detail;

            let errorType, errorMsg;
            if (status === 402) {
              errorType = "budget_exceeded";
              errorMsg = detail || "Budget exceeded";
            } else if (status === 429) {
              errorType = "rate_limited";
              errorMsg = detail || "Rate limited";
            } else if (status === 503) {
              errorType = "service_unavailable";
              errorMsg = detail || "LLM service temporarily unavailable";
            } else if (status === 504) {
              errorType = "timeout";
              errorMsg = detail || "Scene timed out";
            } else if (!sceneErr.response) {
              errorType = "network_error";
              errorMsg = "Connection lost — proxy timeout. Retry individually.";
            } else {
              errorType = "backend_error";
              errorMsg = detail || sceneErr.message || "Unknown error";
            }
            console.error(`Scene ${scene.scene_number} [${errorType}]:`, errorMsg);

            if (errorType === "budget_exceeded" || errorType === "rate_limited") {
              stopBatch = true;
              toast.error(errorMsg, { duration: 10000 });
            }

            breakdowns[globalIdx] = {
              id: `failed-${globalIdx}`,
              script_id,
              scene_number: scene.scene_number,
              scene_heading: scene.heading,
              original_text: scene.text,
              mode,
              error_type: errorType,
              error_msg: errorMsg,
              scene_summary: `Analysis failed: ${errorMsg}`,
              character_name: characterName,
              character_objective: "", stakes: "",
              beats: [], acting_takes: { grounded: "", bold: "", wildcard: "" },
              memorization: { chunked_lines: [], cue_recall: [] },
              self_tape_tips: { framing: "", eyeline: "", tone_energy: "" },
            };
            toast.error(`Scene ${scene.scene_number}: ${errorMsg}`, { duration: 5000 });
          });
        });

        await Promise.all(batchPromises);

        if (stopBatch) {
          const completed = breakdowns.filter(b => b !== null && !b?.id?.toString().startsWith("failed-")).length;
          if (completed > 0) {
            toast.info(`Showing ${completed} scene${completed > 1 ? 's' : ''} that completed.`);
          }
          break;
        }
      }

      // Filter out null slots (shouldn't happen, but safety)
      const finalBreakdowns = breakdowns.filter(b => b !== null);

      const successBreakdowns = finalBreakdowns.filter(b => !b.id?.toString().startsWith("failed-"));
      const cachedCount = successBreakdowns.filter(b => b.from_cache).length;

      const result = { script_id, character_name: characterName, mode, prepMode, projectType, breakdowns: finalBreakdowns };
      if (finalBreakdowns.length > 0) {
        setScriptData(result);
        setView("script");
        if (successBreakdowns.length > 0) {
          const parts = [`${successBreakdowns.length} scene${successBreakdowns.length !== 1 ? 's' : ''} analyzed`];
          if (cachedCount > 0) parts.push(`${cachedCount} instant`);
          toast.success(parts.join(' · '));
        }
      } else {
        toast.error("No scenes could be analyzed. Check your LLM key balance.");
      }
      axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
      axios.get(`${API}/scripts`).then(r => setRecentScripts(r.data || [])).catch(() => {});
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

  const handleLoadScript = useCallback(async (scriptId) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/scripts/${scriptId}`);
      const script = response.data;
      const breakdowns = script.breakdowns || [];
      if (breakdowns.length === 0) {
        toast.error("This script has no analyzed scenes.");
        setLoading(false);
        return;
      }
      setScriptData({
        script_id: script.id,
        character_name: script.character_name,
        mode: script.mode,
        prepMode: script.prep_mode,
        projectType: script.project_type,
        breakdowns,
      });
      setView("script");
      toast.success(`Loaded "${script.character_name}" — ${breakdowns.length} scene${breakdowns.length !== 1 ? "s" : ""}`);
    } catch {
      toast.error("Could not load this script.");
    }
    setLoading(false);
  }, []);

  const handleAdjusted = useCallback((updatedBreakdown) => {
    // Update single breakdown view
    if (view === "breakdown") {
      setBreakdown(updatedBreakdown);
    }
    // Update script data if in script mode
    if (view === "script" && scriptData) {
      setScriptData(prev => ({
        ...prev,
        breakdowns: prev.breakdowns.map(b => b.id === updatedBreakdown.id ? updatedBreakdown : b),
      }));
    }
    setShowPostActionAdjust(false);
  }, [view, scriptData]);

  const handleRetryScene = useCallback(async (failedBreakdown) => {
    const { script_id, scene_number, scene_heading, original_text, mode: sceneMode } = failedBreakdown;
    const characterName = scriptData?.character_name;
    toast.info(`Retrying scene ${scene_number}...`);
    try {
      const resp = await axios.post(`${API}/analyze/scene`, {
        script_id,
        scene_number,
        scene_heading,
        text: original_text,
        character_name: characterName,
        mode: sceneMode || scriptData?.mode || "quick",
        prep_mode: scriptData?.prepMode,
        project_type: scriptData?.projectType,
      }, { timeout: 70000 });
      setScriptData(prev => ({
        ...prev,
        breakdowns: prev.breakdowns.map(b => b.id === failedBreakdown.id ? resp.data : b),
      }));
      toast.success(`Scene ${scene_number} analyzed successfully.`);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      toast.error(`Scene ${scene_number} retry failed: ${detail}`, { duration: 8000 });
    }
  }, [scriptData]);

  const handleCloseOverlay = useCallback((overlayType) => {
    if (overlayType === "memorization") setMemorizationOpen(false);
    if (overlayType === "sceneReader") setSceneReaderOpen(false);

    // Show post-action adjustment card
    const activeB = activeScriptBreakdown || breakdown;
    if (activeB?.id) {
      setPostActionBreakdownId(activeB.id);
      setShowPostActionAdjust(true);
      // Auto-dismiss after 10s
      setTimeout(() => setShowPostActionAdjust(false), 10000);
    }
    setActiveScriptBreakdown(null);
  }, [activeScriptBreakdown, breakdown]);

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
            <UploadPage onAnalyze={handleAnalyze} onFullScriptAnalyze={handleFullScriptAnalyze} recentBreakdowns={recentBreakdowns} recentScripts={recentScripts} onLoadBreakdown={handleLoadBreakdown} onLoadScript={handleLoadScript} loading={loading} />
          </motion.div>
        )}
        {!loading && view === "breakdown" && breakdown && (
          <motion.div key="breakdown" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <BreakdownView
              breakdown={breakdown}
              onRegenerate={handleRegenerateTakes}
              onReanalyzeDeep={handleReanalyzeDeep}
              onAdjusted={handleAdjusted}
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
              onRetryScene={handleRetryScene}
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
              onAdjusted={handleAdjusted}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {memorizationOpen && (breakdown || activeScriptBreakdown) && (
          <MemorizationMode
            key={`memo-${(activeScriptBreakdown || breakdown)?.id}`}
            memorization={(activeScriptBreakdown || breakdown).memorization}
            characterName={(activeScriptBreakdown || breakdown).character_name}
            onClose={() => handleCloseOverlay("memorization")}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sceneReaderOpen && (breakdown || activeScriptBreakdown) && (
          <SceneReader
            key={`reader-${(activeScriptBreakdown || breakdown)?.id}`}
            memorization={(activeScriptBreakdown || breakdown).memorization}
            characterName={(activeScriptBreakdown || breakdown).character_name}
            ttsAvailable={ttsAvailable}
            voices={voices}
            onClose={() => handleCloseOverlay("sceneReader")}
          />
        )}
      </AnimatePresence>

      {/* Post-action adjustment card */}
      <AnimatePresence>
        {showPostActionAdjust && postActionBreakdownId && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[min(380px,90vw)]"
          >
            <AdjustmentPanel
              breakdownId={postActionBreakdownId}
              onAdjusted={handleAdjusted}
              variant="post-action"
              onDismiss={() => setShowPostActionAdjust(false)}
            />
          </motion.div>
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
