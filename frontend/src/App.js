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
import LoadingScreen from "@/components/LoadingScreen";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function MainApp() {
  const [view, setView] = useState("upload");
  const [breakdown, setBreakdown] = useState(null);
  const [loading, setLoading] = useState(false);
  const [memorizationOpen, setMemorizationOpen] = useState(false);
  const [sceneReaderOpen, setSceneReaderOpen] = useState(false);
  const [ttsAvailable, setTtsAvailable] = useState(false);
  const [recentBreakdowns, setRecentBreakdowns] = useState([]);

  useEffect(() => {
    axios.get(`${API}/tts/status`).then(r => setTtsAvailable(r.data.available)).catch(() => {});
    axios.get(`${API}/breakdowns`).then(r => setRecentBreakdowns(r.data || [])).catch(() => {});
  }, []);

  const handleAnalyze = useCallback(async (data) => {
    setLoading(true);
    try {
      let response;
      const timeout = 120000;
      if (data.type === "text") {
        response = await axios.post(`${API}/analyze/text`, { text: data.text }, { timeout });
      } else {
        const formData = new FormData();
        formData.append("file", data.file);
        if (data.context) {
          formData.append("context", data.context);
        }
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

  const handleNewAnalysis = useCallback(() => {
    setView("upload");
    setBreakdown(null);
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
            <LoadingScreen />
          </motion.div>
        )}
        {!loading && view === "upload" && (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <UploadPage onAnalyze={handleAnalyze} recentBreakdowns={recentBreakdowns} onLoadBreakdown={handleLoadBreakdown} />
          </motion.div>
        )}
        {!loading && view === "breakdown" && breakdown && (
          <motion.div key="breakdown" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <BreakdownView
              breakdown={breakdown}
              onRegenerate={handleRegenerateTakes}
              onExportPdf={handleExportPdf}
              onNewAnalysis={handleNewAnalysis}
              onOpenMemorization={() => setMemorizationOpen(true)}
              onOpenSceneReader={() => setSceneReaderOpen(true)}
              onShare={handleShare}
              ttsAvailable={ttsAvailable}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {memorizationOpen && breakdown && (
          <MemorizationMode
            memorization={breakdown.memorization}
            characterName={breakdown.character_name}
            onClose={() => setMemorizationOpen(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sceneReaderOpen && breakdown && (
          <SceneReader
            memorization={breakdown.memorization}
            characterName={breakdown.character_name}
            ttsAvailable={ttsAvailable}
            onClose={() => setSceneReaderOpen(false)}
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
