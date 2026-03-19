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

  useEffect(() => {
    axios.get(`${API}/tts/status`).then(r => setTtsAvailable(r.data.available)).catch(() => {});
  }, []);

  const handleAnalyze = useCallback(async (data) => {
    setLoading(true);
    try {
      let response;
      if (data.type === "text") {
        response = await axios.post(`${API}/analyze/text`, { text: data.text });
      } else {
        const formData = new FormData();
        formData.append("file", data.file);
        response = await axios.post(`${API}/analyze/image`, formData);
      }
      setBreakdown(response.data);
      setView("breakdown");
      toast.success("Breakdown ready. Time to work.");
    } catch (error) {
      const msg = error.response?.data?.detail || "Analysis failed. Try again.";
      toast.error(msg);
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
            <UploadPage onAnalyze={handleAnalyze} />
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
