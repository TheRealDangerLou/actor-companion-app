import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import ProjectHome from "@/components/ProjectHome";
import ProjectCreate from "@/components/ProjectCreate";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentReview from "@/components/DocumentReview";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function App() {
  const [view, setView] = useState("home"); // "home" | "create" | "project" | "review"
  const [createMode, setCreateMode] = useState("audition");
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading] = useState(false);

  // --- Navigation handlers ---
  const handleCreateProject = useCallback((mode) => {
    setCreateMode(mode);
    setView("create");
  }, []);

  const handleProjectCreated = useCallback((project) => {
    setActiveProject(project);
    setView("project");
  }, []);

  const handleOpenProject = useCallback(async (projectId) => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/projects/${projectId}`);
      const proj = resp.data;
      setActiveProject(proj);
      // If all docs are confirmed, go to review (future: prep dashboard)
      // If has docs but not confirmed, go to review
      // If no docs, go to upload
      const docs = proj.documents || [];
      if (docs.length === 0) {
        setView("project");
      } else {
        const allConfirmed = docs.every((d) => d.is_confirmed);
        setView(allConfirmed ? "review" : "project");
      }
    } catch {
      toast.error("Could not open project.");
    }
    setLoading(false);
  }, []);

  const handleDocumentsChanged = useCallback((docs, shouldContinue) => {
    setActiveProject((prev) => prev ? { ...prev, documents: docs } : prev);
    if (shouldContinue) {
      setView("review");
    }
  }, []);

  const handleAllConfirmed = useCallback(() => {
    // Feature #5+ will add character detection here
    toast.success("All documents confirmed. Character selection coming next.");
    setView("home");
  }, []);

  const handleBackToHome = useCallback(() => {
    setView("home");
    setActiveProject(null);
  }, []);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#09090b] text-white">
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="min-h-screen flex items-center justify-center"
            >
              <div className="text-zinc-500 text-sm">Loading...</div>
            </motion.div>
          )}

          {!loading && view === "home" && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <ProjectHome onOpenProject={handleOpenProject} onCreateProject={handleCreateProject} />
            </motion.div>
          )}

          {!loading && view === "create" && (
            <motion.div key="create" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <ProjectCreate mode={createMode} onCreated={handleProjectCreated} onBack={handleBackToHome} />
            </motion.div>
          )}

          {!loading && view === "project" && activeProject && (
            <motion.div key="project" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <DocumentUpload
                project={activeProject}
                onDocumentsChanged={handleDocumentsChanged}
                onBack={handleBackToHome}
              />
            </motion.div>
          )}

          {!loading && view === "review" && activeProject && (
            <motion.div key="review" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <DocumentReview
                project={activeProject}
                onAllConfirmed={handleAllConfirmed}
                onBack={() => setView("project")}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <Toaster
          position="top-center"
          toastOptions={{
            style: { background: "#18181b", color: "#fafafa", border: "1px solid #27272a" },
          }}
        />
      </div>
    </TooltipProvider>
  );
}

export default App;
